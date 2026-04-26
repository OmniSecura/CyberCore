from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...database.models.User import User
from ...schemas.user import CreateUser, LoginRequest, UserResponse
from ...security.JWT import (
    blacklist_from_request_cookies,
    clear_auth_cookies,
    get_current_user,
    require_superadmin,
    set_auth_cookies,
    _decode_token,
    _get_jti_and_exp,
    create_access_token,
    create_refresh_token,
    _set_cookie,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    _REFRESH_COOKIE,
)
from ...services.user_service import UserService

from ...security.token_blacklist import blacklist_token

auth_router = APIRouter(prefix="/users", tags=["Auth"])


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
        Returns only a success message — no user data, no tokens.
        The user must log in after registering.
        """
        try:
            service.create_user(user_data)
            return {"message": "Account created successfully"}
        except ValueError:
            # Generic message — do not confirm whether the email exists
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed",
            )

    # ── Login ─────────────────────────────────────────────────────────────────

    @auth_router.post("/login", status_code=status.HTTP_200_OK)
    def login(
        self,
        credentials: LoginRequest,
        service: UserService = Depends(_get_service),
    ):
        """
        Authenticate with email + password.

        On success both tokens are written into httpOnly cookies — the client
        never sees the token values. Response body contains only a status message.
        """
        try:
            user = service.authenticate(credentials)
        except ValueError:
            # Always the same message — never reveal whether email or password was wrong
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
    def refresh(
        self,
        request: Request,
        db: Session = Depends(get_db),
    ):
        """
        Issue a new access token using the refresh token cookie.

        Normally handled automatically by AutoRefreshMiddleware —
        this endpoint exists as a manual fallback.
        Returns only a status message. New tokens go into cookies.
        """

        refresh_token = request.cookies.get(_REFRESH_COOKIE)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

        try:
            payload = _decode_token(refresh_token, expected_type="refresh")
        except HTTPException:
            raise

        user_id = payload["sub"]
        old_jti = payload["jti"]
        old_exp = payload["exp"]

        user = (
            db.query(User)
            .filter(
                User.id == user_id,
                User.is_active == True,
                User.deleted_at.is_(None),
            )
            .first()
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        # Blacklist the old refresh token (token rotation)
        blacklist_token(old_jti, old_exp)

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Token refreshed"},
        )
        set_auth_cookies(response, user_id)
        return response

    # ── Logout ────────────────────────────────────────────────────────────────

    @auth_router.post("/logout", status_code=status.HTTP_200_OK)
    def logout(self, request: Request):
        """
        Invalidate both tokens and clear the cookies.
        Response body contains only a status message.
        """
        blacklist_from_request_cookies(request)

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Logged out"},
        )
        clear_auth_cookies(response)
        return response

    # ── Me ────────────────────────────────────────────────────────────────────

    @auth_router.get("/me", status_code=status.HTTP_200_OK, response_model=UserResponse)
    def get_me(self, current_user: User = Depends(get_current_user)):
        """
        Return the current user's profile.
        UserResponse exposes only safe fields — no password hash, no MFA secret.
        """
        return current_user

    # ── Delete own account ────────────────────────────────────────────────────

    @auth_router.delete("/me", status_code=status.HTTP_200_OK)
    def delete_my_account(
        self,
        request: Request,
        password: str,
        service: UserService = Depends(_get_service),
        current_user: User = Depends(get_current_user),
    ):
        """
        Soft-delete the authenticated user's own account.
        User ID comes from the cookie token — never from the URL.
        Invalidates both tokens immediately on deletion.
        """
        try:
            service.soft_delete_user(current_user.id, password=password)
        except LookupError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

        blacklist_from_request_cookies(request)

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Account deleted"},
        )
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
        """
        Soft-delete any user by ID. Superadmin only.
        Returns only a status message — no user data.
        """
        try:
            service.admin_soft_delete_user(user_id)
            return {"message": "Account deleted"}
        except LookupError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")