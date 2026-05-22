from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...database.models.User import User
from ...schemas.user import CreateUser, LoginRequest, PublicUser, UserLookupRequest, UserResponse
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
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services.user_service import UserService
from ...services.email_service import EmailService
from ...cyberlog_client import log

auth_router = APIRouter(prefix="/users", tags=["Auth"])

_email_svc = EmailService()


def _get_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@cbv(auth_router)
class AuthRouter:

    # ── Register ──────────────────────────────────────────────────────────────

    @auth_router.post("/register", status_code=status.HTTP_201_CREATED)
    @limiter.limit(settings.POST_USERS_REGISTER)
    def register(
        self,
        request: Request,
        user_data: CreateUser,
        service: UserService = Depends(_get_service),
    ):
        try:
            user, verify_token = service.create_user(user_data)
        except ValueError:
            log.warning("Registration failed — email already taken", email=user_data.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed",
            )

        ulog = log.bind(user_id=str(user.id), email=user.email)
        ulog.info("User registered")

        try:
            _email_svc.send_welcome(user.email, user.full_name)
            _email_svc.send_verify_email(user.email, user.full_name, verify_token)
        except Exception:
            ulog.warning("Welcome email delivery failed")

        return {"message": "Account created successfully. Check your email to verify your address."}

    # ── Login ─────────────────────────────────────────────────────────────────

    @auth_router.post("/login", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_USERS_LOGIN)
    def login(
        self,
        request: Request,
        credentials: LoginRequest,
        service: UserService = Depends(_get_service),
    ):
        try:
            user = service.authenticate(credentials)
        except ValueError as e:
            if "not verified" in str(e):
                log.warning("Login blocked — email not verified", email=credentials.email)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please verify your email before logging in",
                )
            log.warning("Login failed — invalid credentials", email=credentials.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        log.info("User logged in", user_id=str(user.id), email=user.email)

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Login successful"},
        )
        set_auth_cookies(response, user.id)
        return response

    # ── Refresh ───────────────────────────────────────────────────────────────

    @auth_router.post("/refresh", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_USERS_REFRESH)
    def refresh(self, request: Request, db: Session = Depends(get_db)):
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
    @limiter.limit(settings.POST_USERS_LOGOUT)
    def logout(self, request: Request):
        """Invalidate both tokens and clear the cookies."""
        blacklist_from_request_cookies(request)
        log.info("User logged out")
        response = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Logged out"})
        clear_auth_cookies(response)
        return response

    # ── Me ────────────────────────────────────────────────────────────────────

    @auth_router.get("/me", status_code=status.HTTP_200_OK, response_model=UserResponse)
    @limiter.limit(settings.GET_USERS_ME)
    def get_me(self, request: Request, current_user: User = Depends(get_current_user)):
        """Return the current user's profile (safe fields only)."""
        return current_user

    # ── Bulk lookup ───────────────────────────────────────────────────────────

    @auth_router.post("/lookup", status_code=status.HTTP_200_OK, response_model=list[PublicUser])
    @limiter.limit(settings.POST_USERS_LOOKUP)
    def lookup_users(
        self,
        request: Request,
        body: UserLookupRequest,
        db: Session = Depends(get_db),
        _current: User = Depends(get_current_user),
    ):
        if not body.ids:
            return []
        ids = list({str(i) for i in body.ids})[:200]
        users = (
            db.query(User)
            .filter(User.id.in_(ids), User.deleted_at.is_(None))
            .all()
        )
        return users

    # ── Resend verification ───────────────────────────────────────────────────

    @auth_router.post("/me/resend-verification", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_USERS_ME_RESEND_VERIFICATION)
    def resend_verification(
        self,
        request: Request,
        service: UserService = Depends(_get_service),
        current_user: User = Depends(get_current_user),
    ):
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
    @limiter.limit(settings.DELETE_USERS_ME)
    def delete_my_account(
        self,
        request: Request,
        body: DeleteAccountRequest,
        service: UserService = Depends(_get_service),
        current_user: User = Depends(get_current_user),
    ):
        try:
            service.soft_delete_user(current_user.id, body.password)
        except LookupError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        except ValueError:
            log.warning("Account deletion failed — wrong password", user_id=str(current_user.id))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        log.info("Account deleted", user_id=str(current_user.id), email=current_user.email)
        blacklist_from_request_cookies(request)
        response = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Account deleted"})
        clear_auth_cookies(response)
        return response

    # ── Admin: delete any user ────────────────────────────────────────────────

    @auth_router.delete("/admin/{user_id}", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.DELETE_USERS_ADMIN)
    def admin_delete_user(
        self,
        request: Request,
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
