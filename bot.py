"""
Telegram-бот на aiogram для мини-игры «CS Case Bot».

Задачи бота:
- Приветствовать игрока по /start и регистрировать его в базе.
- Давать кнопку запуска WebApp (мини-приложения).
- Показывать краткую статистику по /stats.

WebApp открывается по HTTPS-URL (WEBAPP_URL), который отдаёт FastAPI-сервер (server.py).
Локально для HTTPS удобно использовать туннель (ngrok/cloudflared) — см. README.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker, init_db
from app.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cs-case-bot")


def _webapp_keyboards():
    """Инлайн- и reply-клавиатуры с кнопкой запуска WebApp."""
    url = settings.webapp_url
    inline = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Открыть игру", web_app=WebAppInfo(url=url))]
        ]
    )
    reply = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎮 Играть", web_app=WebAppInfo(url=url))]],
        resize_keyboard=True,
    )
    return inline, reply


async def get_or_create_user(tg_user) -> User:
    """Регистрирует игрока в базе, если его ещё нет."""
    async with async_session_maker() as session:
        existing = await session.scalar(
            select(User).where(User.tg_id == tg_user.id)
        )
        if existing:
            return existing
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Player",
        )
        session.add(user)
        await session.commit()
        return user


def register_handlers(dp: Dispatcher) -> None:
    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        await get_or_create_user(message.from_user)
        inline, reply = _webapp_keyboards()
        text = (
            f"<b>CS Case Bot</b>\n\n"
            f"Привет, {message.from_user.first_name}! 🟢\n\n"
            "Кликай, открывай кейсы, прокачивай уровень и собирай скины в стилистике CS.\n\n"
            "Нажми кнопку ниже, чтобы открыть игру 👇"
        )
        await message.answer(text, reply_markup=inline)
        await message.answer("Кнопка «Играть» закреплена внизу.", reply_markup=reply)

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message):
        async with async_session_maker() as session:
            user = await session.scalar(
                select(User).where(User.tg_id == message.from_user.id)
            )
        if not user:
            await message.answer("Сначала запусти игру командой /start")
            return
        await message.answer(
            f"<b>Твоя статистика</b>\n\n"
            f"💰 Баланс: {user.balance:.2f}\n"
            f"⭐ Уровень: {user.level}\n"
            f"👆 Кликов: {user.total_clicks}\n"
            f"📦 Кейсов открыто: {user.cases_opened}"
        )

    @dp.message(F.web_app_data)
    async def on_webapp_data(message: Message):
        # Резерв: обработка данных, если WebApp пришлёт что-то через sendData.
        await message.answer("Данные из игры получены ✅")


async def main() -> None:
    if not settings.bot_token or settings.bot_token == "CHANGE_ME":
        raise SystemExit(
            "Не задан BOT_TOKEN. Укажи токен бота в .env перед запуском (см. README)."
        )

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_handlers(dp)

    logger.info("Бот запущен. WebApp URL: %s", settings.webapp_url)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
