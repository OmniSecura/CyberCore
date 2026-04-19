from sqlalchemy.orm import Session
from ..database.models.User import User
from ..schemas import CreateUser
from ..security.security import PasswordSecurity
from fastapi import HTTPException

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

    def get_by_id(self, id: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.id == id, User.deleted_at.is_(None))
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

    def create_user(self, user_data: CreateUser) -> HTTPException | User:
        if self.get_by_email(user_data.email):
            raise ValueError(f"Email already registered: {user_data.email}")

        hashed_password=PasswordSecurity().hash_password(user_data.password)

        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=hashed_password,
        )

        self.db.add(user)
        self.db.commit()
        return user
