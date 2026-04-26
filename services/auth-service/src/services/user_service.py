from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from ..database.models.User import User
from ..schemas.user import CreateUser, LoginRequest
from ..security.security import PasswordSecurity

_pwd = PasswordSecurity()

# Lockout policy
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES     = 15


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

    def del_user(self, user: User, password: str):
        if not user:
            raise LookupError(f"User not found")
        if not _pwd.verify_password(user.password_hash, password):
            raise LookupError(f"Invalid credentials")

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active  = False
        self.db.flush()
        return f"Account has been deactivated"


    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_user(self, user_data: CreateUser) -> str:
        """
        Register a new user.

        Raises:
            ValueError: If the email is already registered.
        """
        if self.get_by_email(user_data.email):
            raise ValueError(f"Email already registered: {user_data.email}")

        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=_pwd.hash_password(user_data.password),
        )

        self.db.add(user)
        self.db.flush()   # generates id — commit handled by get_db()
        return "Welcome to Cybercore"

    def authenticate(self, credentials: LoginRequest) -> User:
        """
        Verify email + password and return the user on success.

        Implements brute-force protection:
            - Tracks failed attempts per user
            - Locks account for LOCKOUT_MINUTES after MAX_FAILED_ATTEMPTS failures
            - Resets counter on successful login

        Raises:
            ValueError: With a generic message on any authentication failure.
                        The message is intentionally vague — never reveal
                        whether the email exists or the password was wrong.
        """
        _GENERIC_ERROR = "Invalid email or password"

        user = self.get_by_email(credentials.email)
        if not user:
            raise ValueError(_GENERIC_ERROR)

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise ValueError("Account is temporarily locked — try again later")

        # Inactive or deleted accounts get the same generic error
        if not user.is_active:
            raise ValueError(_GENERIC_ERROR)

        # Verify password — argon2 verify(hash, plaintext)
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

        # Successful login — reset lockout state and record metadata
        user.failed_login_attempts = 0
        user.locked_until          = None
        user.last_login_at         = datetime.now(timezone.utc)
        self.db.flush()

        return user

    def soft_delete_user(self, user_id: str, password: str) -> str:
        """
        Soft-delete a user by setting deleted_at and deactivating the account.

        Raises:
            LookupError: If the user does not exist or is already deleted.
        """
        user = self.get_by_id(user_id)
        return self.del_user(user, password)

    def soft_delete_by_email(self, email: str, password: str) -> str:
        """
        Soft-delete a user by email — used for user-facing account deletion.

        Raises:
            LookupError: If the user does not exist.
        """
        user = self.get_by_email(email)
        return self.del_user(user, password)

    def admin_soft_delete_user(self, user_id: str) -> str:
        """
        Soft-delete a user by setting deleted_at and deactivating the account.

        Raises:
            LookupError: If the user does not exist or is already deleted.
        """
        user = self.get_by_id(user_id)
        if not user:
            raise LookupError(f"User not found: {user_id}")

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active  = False
        self.db.flush()
        return f"User {user_id} has been deactivated"