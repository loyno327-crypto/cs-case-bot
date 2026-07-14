"""Наполнение БД демо-данными: скины, кейсы и шансы выпадения.

Запуск: python -m app.seed
Повторный запуск безопасен — данные пересоздаются только если таблицы пусты.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.database import async_session_maker, init_db
from app.models import Case, CaseItem, Item

# Каталог скинов. rarity влияет на цвет рамки в UI.
ITEMS: list[dict] = [
    {"key": "karambit", "name": "★ Karambit", "subtitle": "Gamma Doppler", "rarity": "ancient",
     "price": 32560.50, "image": "/static/img/skins/karambit_gamma.png"},
    {"key": "awp", "name": "AWP", "subtitle": "Dragon Lore", "rarity": "legendary",
     "price": 21560.00, "image": "/static/img/skins/awp_dragon.png"},
    {"key": "m4a4", "name": "M4A4", "subtitle": "Howl", "rarity": "mythical",
     "price": 18450.50, "image": "/static/img/skins/m4a4_howl.png"},
    {"key": "butterfly", "name": "★ Butterfly Knife", "subtitle": "Doppler", "rarity": "ancient",
     "price": 15700.00, "image": "/static/img/skins/butterfly_doppler.png"},
    {"key": "ak", "name": "AK-47", "subtitle": "Wild Lotus", "rarity": "legendary",
     "price": 12850.30, "image": "/static/img/skins/ak_wildlotus.png"},
    {"key": "deagle", "name": "Desert Eagle", "subtitle": "Emerald", "rarity": "rare",
     "price": 3200.00, "image": "/static/img/skins/deagle_emerald.png"},
    {"key": "usp", "name": "USP-S", "subtitle": "Neon", "rarity": "uncommon",
     "price": 950.00, "image": "/static/img/skins/usp_neon.png"},
    {"key": "glock", "name": "Glock-18", "subtitle": "Grey Camo", "rarity": "common",
     "price": 150.00, "image": "/static/img/skins/glock_grey.png"},
]

# Кейсы: (name, price, image, is_free, [(item_key, weight), ...])
CASES: list[dict] = [
    {
        "name": "Зелёный кейс",
        "price": 2500.0,
        "image": "/static/img/cases/green_case.png",
        "is_free": False,
        "drops": [
            ("glock", 40), ("usp", 28), ("deagle", 18),
            ("ak", 8), ("m4a4", 4), ("awp", 1.6),
            ("butterfly", 0.3), ("karambit", 0.1),
        ],
    },
    {
        "name": "Бесплатный кейс",
        "price": 0.0,
        "image": "/static/img/cases/free_case.png",
        "is_free": True,
        "drops": [
            ("glock", 55), ("usp", 30), ("deagle", 12),
            ("ak", 2.5), ("awp", 0.5),
        ],
    },
    {
        "name": "Ножевой кейс",
        "price": 12000.0,
        "image": "/static/img/cases/green_case.png",
        "is_free": False,
        "drops": [
            ("deagle", 35), ("ak", 30), ("m4a4", 18),
            ("awp", 10), ("butterfly", 4), ("karambit", 3),
        ],
    },
]


async def seed() -> None:
    await init_db()
    async with async_session_maker() as session:
        count = await session.scalar(select(func.count(Item.id)))
        if count and count > 0:
            print("Данные уже есть, пропускаю сид.")
            return

        # Скины
        key_to_item: dict[str, Item] = {}
        for data in ITEMS:
            item = Item(
                name=data["name"], subtitle=data["subtitle"], rarity=data["rarity"],
                price=data["price"], image=data["image"],
            )
            session.add(item)
            key_to_item[data["key"]] = item
        await session.flush()

        # Кейсы
        for c in CASES:
            case = Case(name=c["name"], price=c["price"], image=c["image"], is_free=c["is_free"])
            session.add(case)
            await session.flush()
            for item_key, weight in c["drops"]:
                session.add(CaseItem(case_id=case.id, item_id=key_to_item[item_key].id, weight=weight))

        await session.commit()
        print(f"Готово: {len(ITEMS)} скинов, {len(CASES)} кейсов.")


if __name__ == "__main__":
    asyncio.run(seed())
