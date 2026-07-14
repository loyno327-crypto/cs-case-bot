"""
Единая точка запуска: одновременно поднимает FastAPI (WebApp + API) и бота aiogram.

Использование:
    python run.py            # сервер + бот
    python run.py server     # только сервер (WebApp + API)
    python run.py bot        # только бот
    python run.py seed       # наполнить базу демо-данными

Для локального теста WebApp в браузере достаточно `python run.py server`
и открыть http://localhost:8000 (работает демо-игрок, DEBUG=True).
"""
import asyncio
import sys

import uvicorn

from app.config import settings


async def _bootstrap() -> None:
    """Создаёт таблицы и наполняет БД демо-данными (безопасно при каждом старте)."""
    from app.seed import seed
    await seed()


async def _run_server() -> None:
    config = uvicorn.Config(
        "server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def _run_bot() -> None:
    import bot
    await bot.main()


async def _run_all() -> None:
    await _bootstrap()
    await asyncio.gather(_run_server(), _run_bot())


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "seed":
        from app.seed import seed
        asyncio.run(seed())
        return

    if mode == "server":
        asyncio.run(_bootstrap())
        uvicorn.run("server:app", host=settings.host, port=settings.port)
        return

    if mode == "bot":
        asyncio.run(_run_bot())
        return

    # mode == "all"
    asyncio.run(_run_all())


if __name__ == "__main__":
    main()
