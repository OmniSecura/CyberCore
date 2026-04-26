from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

from ...database.db_connection import get_db
from ...schemas.email import (
    VerifyEmailRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
)
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
    def verify_email(
        self,
        body: VerifyEmailRequest,
        service: UserService = Depends(_get_service),
    ):
        """
        Consume an email-verification token sent to the user's inbox.

        The frontend extracts the token from the URL query param and POSTs it here.
        Returns 400 on invalid / expired token — always the same generic message.
        """
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
    def request_password_reset(
        self,
        body: RequestPasswordResetRequest,
        service: UserService = Depends(_get_service),
    ):
        """
        Trigger a password-reset email.

        Always returns 200 — never confirm whether the email is registered.
        Token is valid for 1 hour.
        """
        result = service.request_password_reset(body.email)

        if result:
            user, token = result
            try:
                _email_svc.send_reset_password(user.email, user.full_name, token)
            except Exception:
                pass  # log in production

        # Identical response regardless of whether email exists
        return {"message": "If that email is registered, a reset link has been sent"}

    # ── Confirm password reset ────────────────────────────────────────────────

    @email_router.post("/reset-password/confirm", status_code=status.HTTP_200_OK)
    def confirm_password_reset(
        self,
        body: ResetPasswordRequest,
        service: UserService = Depends(_get_service),
    ):
        """
        Consume a password-reset token and set the new password.

        Returns 400 on invalid / expired token.
        Returns 422 if the new password fails validation rules.
        """
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