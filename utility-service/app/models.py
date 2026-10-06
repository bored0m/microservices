from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now():
    return datetime.now(timezone.utc)


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    address: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    # Ссылка на пользователя из Auth Service — без FK, это чужая БД.
    author_id: Mapped[int] = mapped_column(index=True)
    author_username: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
