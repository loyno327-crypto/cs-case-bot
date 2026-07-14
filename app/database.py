"""Настройка асинхронного подключения к БД через SQLAlchemy."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
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
    """Создаёт таблицы, если их ещё нет, и досоздаёт недостающие колонки."""
    # Импорт нужен, чтобы модели зарегистрировались в метаданных Base.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate)


# Лёгкие миграции для SQLite: добавляем недостающие колонки без потери данных.
# Каждая запись: (таблица, колонка, SQL-тип с DEFAULT при необходимости).
_MIGRATIONS = [
    ("users", "last_free_case_at", "DATETIME"),
]


def _migrate(conn) -> None:
    from sqlalchemy import text

    for table, column, ddl in _MIGRATIONS:
        cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        if column not in cols:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
