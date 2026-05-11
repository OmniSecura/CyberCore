from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from .Base import Base


class User(Base):
    """Read-only reference to the shared users table (owned by auth-service)."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
