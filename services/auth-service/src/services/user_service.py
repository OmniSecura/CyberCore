from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..database.models.User import User
from ..schemas.user import CreateUser
from ..security.security import PasswordSecurity


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

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_user(self, user_data: CreateUser) -> User:
        if self.get_by_email(user_data.email):
            raise ValueError(f"Email already registered: {user_data.email}")

        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=PasswordSecurity().hash_password(user_data.password),
        )

        self.db.add(user)
        self.db.flush()  # commit handled by get_db()
        return user

    def soft_delete_user(self, user_id: str) -> str:
        user = self.get_by_id(user_id)
        if not user:
            raise LookupError(f"User not found: {user_id}")

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        self.db.flush()
        return f"User {user_id} has been deactivated"