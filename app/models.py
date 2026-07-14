"""ORM-модели игры."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="Player")
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Прогресс
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    balance: Mapped[float] = mapped_column(Float, default=0.0)

    # Уровни улучшений (влияют на доход)
    click_level: Mapped[int] = mapped_column(Integer, default=1)
    income_level: Mapped[int] = mapped_column(Integer, default=0)
    autoclick_level: Mapped[int] = mapped_column(Integer, default=0)

    # Тайминги
    last_daily_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_free_case_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_income_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    boost_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Статистика
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)
    cases_opened: Mapped[int] = mapped_column(Integer, default=0)

    inventory: Mapped[list["InventoryItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Item(Base):
    """Скин/предмет CS."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    subtitle: Mapped[str] = mapped_column(String(128), default="")
    # common | uncommon | rare | mythical | legendary | ancient
    rarity: Mapped[str] = mapped_column(String(32), default="common")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    image: Mapped[str] = mapped_column(String(256), default="")

    case_links: Mapped[list["CaseItem"]] = relationship(back_populates="item")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    price: Mapped[float] = mapped_column(Float, default=0.0)
    image: Mapped[str] = mapped_column(String(256), default="")
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list["CaseItem"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class CaseItem(Base):
    """Связь кейс-предмет с весом выпадения."""

    __tablename__ = "case_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    case: Mapped["Case"] = relationship(back_populates="items")
    item: Mapped["Item"] = relationship(back_populates="case_links")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="inventory", lazy="select")
    item: Mapped["Item"] = relationship()
