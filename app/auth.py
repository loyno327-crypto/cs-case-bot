"""Проверка подписи Telegram WebApp initData.

Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from app.config import settings


class TelegramUser:
    def __init__(self, data: dict):
        self.id: int = int(data["id"])
        self.first_name: str = data.get("first_name", "Player")
        self.username: str | None = data.get("username")
        self.photo_url: str | None = data.get("photo_url")


def _check_signature(init_data: str, bot_token: str) -> dict | None:
    """Проверяет HMAC-подпись initData. Возвращает распарсенные поля или None."""
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        return None
    return pairs


def parse_init_data(init_data: str | None) -> TelegramUser | None:
    """Валидирует initData и извлекает пользователя.

    В debug-режиме допускается работа без валидной подписи (для браузера),
    тогда возвращается демо-пользователь.
    """
    if init_data:
        pairs = _check_signature(init_data, settings.bot_token) if settings.bot_token else None
        if pairs is None and not settings.debug:
            return None
        if pairs is None:
            # debug: пытаемся достать user без проверки подписи
            pairs = dict(parse_qsl(init_data))
        user_raw = pairs.get("user")
        if user_raw:
            try:
                return TelegramUser(json.loads(user_raw))
            except (ValueError, KeyError):
                pass

    if settings.debug:
        # Демо-игрок для локальной разработки в обычном браузере.
        return TelegramUser({
            "id": 999000999,
            "first_name": "GreenLegend",
            "username": "green_legend",
        })
    return None
