from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...database.models.User import User
from ...schemas.user import CreateUser, LoginRequest, UserResponse
from ...schemas.email import DeleteAccountRequest
from ...security.JWT import (
    blacklist_from_request_cookies,
    clear_auth_cookies,
    get_current_user,
    require_superadmin,
    set_auth_cookies,
    _decode_token,
    _REFRESH_COOKIE,
    set_auth_cookies,
)
from ...security.token_blacklist import blacklist_token
from ...services.user_service import UserService
from ...services.email_service import EmailService

auth_router = APIRouter(prefix="/users", tags=["Auth"])

_email_svc = EmailService()


def _get_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@cbv(auth_router)
class AuthRouter:

    # ── Register ──────────────────────────────────────────────────────────────

    @auth_router.post("/register", status_code=status.HTTP_201_CREATED)
    def register(
        self,
        user_data: CreateUser,
        service: UserService = Depends(_get_service),
    ):
        """
        Create a new account.
        Sends a welcome email and an email-verification link.
        Returns only a success message — no user data, no tokens.
        The user must log in separately after registering.
        """
        try:
            user, verify_token = service.create_user(user_data)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed",
            )

        # Best-effort — do not fail registration if email delivery fails
        try:
            _email_svc.send_welcome(user.email, user.full_name)
            _email_svc.send_verify_email(user.email, user.full_name, verify_token)
        except Exception:
            pass  # log in production

        return {"message": "Account created successfully. Check your email to verify your address."}

    # ── Login ─────────────────────────────────────────────────────────────────

    @auth_router.post("/login", status_code=status.HTTP_200_OK)
    def login(
        self,
        credentials: LoginRequest,
        service: UserService = Depends(_get_service),
    ):
        """
        Authenticate with email + password.
        Tokens are written into httpOnly cookies — client never sees the values.
        """
        try:
            user = service.authenticate(credentials)
        except ValueError as e:
            if "not verified" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please verify your email before logging in",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Login successful"},
        )
        set_auth_cookies(response, user.id)
        return response

    # ── Refresh ───────────────────────────────────────────────────────────────

    @auth_router.post("/refresh", status_code=status.HTTP_200_OK)
    def refresh(self, request: Request, db: Session = Depends(get_db)):
        """
        Issue a new access token using the refresh-token cookie.
        Normally handled automatically by AutoRefreshMiddleware.
        """

        refresh_token = request.cookies.get(_REFRESH_COOKIE)
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        try:
            payload = _decode_token(refresh_token, expected_type="refresh")
        except HTTPException:
            raise

        user_id = payload["sub"]
        old_jti = payload["jti"]
        old_exp = payload["exp"]

        user = (
            db.query(User)
            .filter(User.id == user_id, User.is_active == True, User.deleted_at.is_(None))
            .first()
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        blacklist_token(old_jti, old_exp)

        response = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Token refreshed"})
        set_auth_cookies(response, user_id)
        return response

    # ── Logout ────────────────────────────────────────────────────────────────

    @auth_router.post("/logout", status_code=status.HTTP_200_OK)
    def logout(self, request: Request):
        """Invalidate both tokens and clear the cookies."""
        blacklist_from_request_cookies(request)
        response = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Logged out"})
        clear_auth_cookies(response)
        return response

    # ── Me ────────────────────────────────────────────────────────────────────

    @auth_router.get("/me", status_code=status.HTTP_200_OK, response_model=UserResponse)
    def get_me(self, current_user: User = Depends(get_current_user)):
        """Return the current user's profile (safe fields only)."""
        return current_user

    # ── Resend verification ───────────────────────────────────────────────────

    @auth_router.post("/me/resend-verification", status_code=status.HTTP_200_OK)
    def resend_verification(
        self,
        service: UserService = Depends(_get_service),
        current_user: User = Depends(get_current_user),
    ):
        """
        Re-send the email-verification link.
        Returns 400 if the email is already verified.
        """
        try:
            token = service.resend_verification(current_user)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        try:
            _email_svc.send_verify_email(current_user.email, current_user.full_name, token)
        except Exception:
            pass

        return {"message": "Verification email sent"}

    # ── Delete own account ────────────────────────────────────────────────────

    @auth_router.delete("/me", status_code=status.HTTP_200_OK)
    def delete_my_account(
        self,
        request: Request,
        body: DeleteAccountRequest,
        service: UserService = Depends(_get_service),
        current_user: User = Depends(get_current_user),
    ):
        """
        Soft-delete the authenticated user's own account.
        Requires the current password in the request body.
        Invalidates both tokens immediately.
        """
        try:
            service.soft_delete_user(current_user.id, body.password)
        except LookupError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        blacklist_from_request_cookies(request)
        response = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Account deleted"})
        clear_auth_cookies(response)
        return response

    # ── Admin: delete any user ────────────────────────────────────────────────

    @auth_router.delete("/admin/{user_id}", status_code=status.HTTP_200_OK)
    def admin_delete_user(
        self,
        user_id: str,
        service: UserService = Depends(_get_service),
        _: User = Depends(require_superadmin),
    ):
        """Soft-delete any user by ID. Superadmin only."""
        try:
            service.admin_soft_delete_user(user_id)
            return {"message": "Account deleted"}
        except LookupError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")