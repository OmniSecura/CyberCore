from sqlalchemy.orm import Session
from sqlalchemy.testing.pickleable import User


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
            .filter(User.deleted_at_is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ── Mutations ─────────────────────────────────────────────────────────────

    