import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from ..database.models.User import User
from ..database.models.UserToken import UserToken
from ..schemas.user import CreateUser, LoginRequest
from ..schemas.email import ResetPasswordRequest
from ..security.security import PasswordSecurity
from ..security.template_matching import validate_password

_pwd = PasswordSecurity()

# Lockout policy
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES     = 15

# Token TTLs
_VERIFY_EMAIL_TTL_HOURS  = 24
_RESET_PASSWORD_TTL_HOURS = 1


def _hash_token(plaintext: str) -> str:
    """SHA-256 hash of a token. Only the hash is stored in the DB."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _generate_token() -> str:
    """Cryptographically secure URL-safe token (48 bytes → 64 chars)."""
    return secrets.token_urlsafe(48)


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_by_email(self, email: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.email == email, User.deleted_at.is_(None))
            .first()
        )

    def get_by_id(self, user_id: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.id == user_id, User.deleted_at.is_(None))
            .first()
        )

    def list_users(self, skip: int = 0, limit: int = 50) -> list[type[User]]:
        return (
            self.db.query(User)
            .filter(User.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ── Internal: token helpers ───────────────────────────────────────────────

    def _create_token(self, user_id: str, token_type: str, ttl_hours: int) -> str:
        """
        Generate a token, invalidate any existing unused token of the same type
        for this user, persist the hash, and return the plaintext.
        """
        # Invalidate previous unused tokens of the same type
        self.db.query(UserToken).filter(
            UserToken.user_id   == user_id,
            UserToken.token_type == token_type,
            UserToken.used_at.is_(None),
        ).delete(synchronize_session=False)

        plaintext  = _generate_token()
        token_hash = _hash_token(plaintext)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        record = UserToken(
            user_id    = user_id,
            token_hash = token_hash,
            token_type = token_type,
            expires_at = expires_at,
        )
        self.db.add(record)
        self.db.flush()

        return plaintext

    def _consume_token(self, plaintext: str, token_type: str) -> UserToken:
        """
        Look up a token by its hash, verify it is the right type,
        not expired, and not already used. Mark it as used.

        Raises:
            LookupError: If the token is invalid, expired, or already used.
        """
        token_hash = _hash_token(plaintext)
        now        = datetime.now(timezone.utc)

        record = (
            self.db.query(UserToken)
            .filter(
                UserToken.token_hash  == token_hash,
                UserToken.token_type  == token_type,
                UserToken.used_at.is_(None),
                UserToken.expires_at  > now,
            )
            .first()
        )

        if not record:
            raise LookupError("Invalid or expired token")

        record.used_at = now
        self.db.flush()
        return record

    # ── Registration ──────────────────────────────────────────────────────────

    def create_user(self, user_data: CreateUser) -> tuple[User, str]:
        """
        Register a new user and generate an email-verification token.

        Returns:
            (user, plaintext_token) — caller sends the welcome + verify emails.

        Raises:
            ValueError: If the email is already registered.
        """
        if self.get_by_email(user_data.email):
            raise ValueError(f"Email already registered: {user_data.email}")

        user = User(
            email         = user_data.email,
            full_name     = user_data.full_name,
            password_hash = _pwd.hash_password(user_data.password),
        )
        self.db.add(user)
        self.db.flush()  # populates user.id

        verify_token = self._create_token(
            user.id, "email_verification", _VERIFY_EMAIL_TTL_HOURS
        )
        return user, verify_token

    # ── Email verification ────────────────────────────────────────────────────

    def verify_email(self, token: str) -> None:
        """
        Mark a user's email as verified.

        Raises:
            LookupError: If the token is invalid, expired, or already used.
        """
        record = self._consume_token(token, "email_verification")

        user = self.get_by_id(record.user_id)
        if not user:
            raise LookupError("User not found")

        user.email_verified = True
        self.db.flush()

    def resend_verification(self, user: User) -> str:
        """
        Generate a new email-verification token (invalidates previous one).

        Raises:
            ValueError: If the email is already verified.

        Returns:
            plaintext token — caller sends the email.
        """
        if user.email_verified:
            raise ValueError("Email is already verified")

        return self._create_token(user.id, "email_verification", _VERIFY_EMAIL_TTL_HOURS)

    # ── Password reset ────────────────────────────────────────────────────────

    def request_password_reset(self, email: str) -> tuple[User, str] | None:
        """
        Generate a password-reset token for the given email.

        Returns (user, plaintext_token) if the email exists and the account
        is active, or None if not — caller always returns 200 to avoid
        leaking whether the email is registered.
        """
        user = self.get_by_email(email)
        if not user or not user.is_active:
            return None

        token = self._create_token(user.id, "password_reset", _RESET_PASSWORD_TTL_HOURS)
        return user, token

    def reset_password(self, data: ResetPasswordRequest) -> None:
        """
        Validate reset token and update password.

        Raises:
            LookupError: If the token is invalid or expired.
            ValueError:  If the new password fails validation.
        """
        record = self._consume_token(data.token, "password_reset")

        user = self.get_by_id(record.user_id)
        if not user:
            raise LookupError("User not found")

        # Re-run password validation (same rules as registration)
        result = validate_password(data.new_password, full_name=user.full_name, email=user.email)
        if not result.valid:
            # Restore token as unused so the user can try again
            record.used_at = None
            self.db.flush()
            raise ValueError(result.errors)

        user.password_hash = _pwd.hash_password(data.new_password)
        self.db.flush()

    # ── Authentication ────────────────────────────────────────────────────────

    def authenticate(self, credentials: LoginRequest) -> str | User:
        """
        Verify email + password and return the user on success.

        Implements brute-force protection:
            - Tracks failed attempts per user
            - Locks account for LOCKOUT_MINUTES after MAX_FAILED_ATTEMPTS failures
            - Resets counter on successful login

        Raises:
            ValueError: With a generic message on any authentication failure.
        """
        _GENERIC_ERROR = "Invalid email or password"

        user = self.get_by_email(credentials.email)
        if not user:
            raise ValueError(_GENERIC_ERROR)

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise ValueError("Account is temporarily locked — try again later")

        if not user.is_active:
            raise ValueError(_GENERIC_ERROR)

        if not user.email_verified:
            raise ValueError("Email not verified")

        if not _pwd.verify_password(user.password_hash, credentials.password):
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
                self.db.flush()
                raise ValueError(
                    f"Too many failed attempts — account locked for {LOCKOUT_MINUTES} minutes"
                )

            self.db.flush()
            raise ValueError(_GENERIC_ERROR)

        user.failed_login_attempts = 0
        user.locked_until          = None
        user.last_login_at         = datetime.now(timezone.utc)
        self.db.flush()

        return user

    # ── Deletion ──────────────────────────────────────────────────────────────

    def _do_soft_delete(self, user: User, password: str) -> None:
        """
        Shared deletion logic — verify password then soft-delete.

        Raises:
            ValueError:  If the password is wrong.
            LookupError: If the user is None (caller checked).
        """
        if not user:
            raise LookupError("User not found")
        if not _pwd.verify_password(user.password_hash, password):
            raise ValueError("Invalid credentials")

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active  = False
        self.db.flush()

    def soft_delete_user(self, user_id: str, password: str) -> None:
        user = self.get_by_id(user_id)
        self._do_soft_delete(user, password)

    def soft_delete_by_email(self, email: str, password: str) -> None:
        user = self.get_by_email(email)
        self._do_soft_delete(user, password)

    def admin_soft_delete_user(self, user_id: str) -> None:
        """Soft-delete without password check. Superadmin only."""
        user = self.get_by_id(user_id)
        if not user:
            raise LookupError(f"User not found: {user_id}")

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active  = False
        self.db.flush()