"""Конфигурация приложения. Значения берутся из переменных окружения (.env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Токен бота из @BotFather
    bot_token: str = ""
    # Публичный HTTPS-адрес, на котором доступен WebApp (например, ngrok / домен)
    # Именно эту ссылку Telegram откроет как Mini App.
    webapp_url: str = "http://localhost:8000"
    # Строка подключения к БД
    database_url: str = "sqlite+aiosqlite:///./game.db"
    # Хост/порт для FastAPI
    host: str = "0.0.0.0"
    port: int = 8000
    # Режим отладки: если True, проверка подписи Telegram initData не блокирует
    # запросы (удобно для локальной разработки в браузере).
    debug: bool = True


settings = Settings()
