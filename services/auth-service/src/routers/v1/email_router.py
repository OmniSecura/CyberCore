from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...schemas.email import (
    VerifyEmailRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
)
from ...security.limiter.rate_limit import limiter
from ...security.limiter import settings
from ...services.user_service import UserService
from ...services.email_service import EmailService

email_router = APIRouter(prefix="/email", tags=["Email"])

_email_svc = EmailService()


def _get_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@cbv(email_router)
class EmailRouter:

    # ── Verify email ──────────────────────────────────────────────────────────

    @email_router.post("/verify", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_EMAIL_VERIFY)
    def verify_email(
        self,
        request: Request,
        body: VerifyEmailRequest,
        service: UserService = Depends(_get_service),
    ):
        try:
            service.verify_email(body.token)
        except LookupError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification link",
            )
        return {"message": "Email verified successfully"}

    # ── Request password reset ────────────────────────────────────────────────

    @email_router.post("/reset-password/request", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_EMAIL_RESET_PASSWORD_REQUEST)
    def request_password_reset(
        self,
        request: Request,
        body: RequestPasswordResetRequest,
        service: UserService = Depends(_get_service),
    ):
        result = service.request_password_reset(body.email)

        if result:
            user, token = result
            try:
                _email_svc.send_reset_password(user.email, user.full_name, token)
            except Exception:
                pass

        return {"message": "If that email is registered, a reset link has been sent"}

    # ── Confirm password reset ────────────────────────────────────────────────

    @email_router.post("/reset-password/confirm", status_code=status.HTTP_200_OK)
    @limiter.limit(settings.POST_EMAIL_RESET_PASSWORD_CONFIRM)
    def confirm_password_reset(
        self,
        request: Request,
        body: ResetPasswordRequest,
        service: UserService = Depends(_get_service),
    ):
        try:
            service.reset_password(body)
        except LookupError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset link",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"password": e.args[0]},
            )

        return {"message": "Password updated successfully. Please log in again."}
