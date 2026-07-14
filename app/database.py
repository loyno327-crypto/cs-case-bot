"""Настройка асинхронного подключения к БД через SQLAlchemy."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость: выдаёт сессию БД на время запроса."""
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """Создаёт таблицы, если их ещё нет."""
    # Импорт нужен, чтобы модели зарегистрировались в метаданных Base.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            columns = await conn.execute(text("PRAGMA table_info(users)"))
            existing = {row[1] for row in columns}
            if "last_free_case_at" not in existing:
                await conn.execute(text("ALTER TABLE users ADD COLUMN last_free_case_at DATETIME"))
