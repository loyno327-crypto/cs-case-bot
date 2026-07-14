"""Игровые операции над состоянием пользователя (бизнес-логика поверх БД)."""
from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import game
from app.auth import TelegramUser
from app.models import Case, CaseItem, InventoryItem, Item, User


# --- Пользователь --------------------------------------------------------

async def get_or_create_user(session: AsyncSession, tg: TelegramUser) -> User:
    user = await session.scalar(select(User).where(User.tg_id == tg.id))
    if user is None:
        user = User(
            tg_id=tg.id,
            username=tg.username,
            first_name=tg.first_name,
            photo_url=tg.photo_url,
            balance=0.0,
        )
        session.add(user)
        await session.flush()
    else:
        # держим профиль актуальным
        user.username = tg.username or user.username
        user.first_name = tg.first_name or user.first_name
        if tg.photo_url:
            user.photo_url = tg.photo_url
    return user


def serialize_user(user: User) -> dict:
    lp = game.level_progress(user)
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "photo_url": user.photo_url,
        "balance": round(user.balance, 2),
        "level": user.level,
        "xp": user.xp,
        "xp_into_level": lp["xp_into_level"],
        "xp_for_next": lp["xp_for_next"],
        "xp_total_next": lp["xp_total_next"],
        "level_progress": round(lp["progress"], 4),
        "click_income": round(game.click_income(user), 2),
        "per_second_income": round(game.per_second_income(user), 2),
        "boost_active": game.is_boost_active(user),
        "boost_seconds_left": game.boost_seconds_left(user),
        "income_multiplier": game.income_multiplier(user),
        "total_clicks": user.total_clicks,
        "cases_opened": user.cases_opened,
        "daily_available": daily_available(user),
        "daily_seconds_left": daily_seconds_left(user),
        "free_case_available": free_case_available(user, 0),
        "free_case_seconds_left": free_case_seconds_left(user),
        "upgrades": game.upgrades_state(user),
    }


# --- Ежедневный бонус ----------------------------------------------------

def daily_available(user: User) -> bool:
    last = game._aware(user.last_daily_at)
    return last is None or (game.now() - last) >= game.DAILY_COOLDOWN


def daily_seconds_left(user: User) -> int:
    last = game._aware(user.last_daily_at)
    if last is None:
        return 0
    left = game.DAILY_COOLDOWN - (game.now() - last)
    return max(int(left.total_seconds()), 0)


def claim_daily(user: User) -> dict:
    if not daily_available(user):
        return {"ok": False, "reason": "cooldown", "seconds_left": daily_seconds_left(user)}
    user.balance += game.DAILY_BONUS
    user.last_daily_at = game.now()
    game.apply_xp(user, 25)
    return {"ok": True, "reward": game.DAILY_BONUS}


# --- Клик ----------------------------------------------------------------

def do_click(user: User, taps: int = 1) -> dict:
    taps = max(1, min(taps, 50))  # анти-чит: не больше 50 тапов за запрос
    income = game.click_income(user) * taps * game.income_multiplier(user)
    user.balance += income
    user.total_clicks += taps
    levels = game.apply_xp(user, game.XP_PER_CLICK * taps)
    return {"earned": round(income, 2), "levels_gained": levels}


# --- Буст ----------------------------------------------------------------

def activate_boost(user: User) -> dict:
    if game.is_boost_active(user):
        return {"ok": False, "reason": "already_active", "seconds_left": game.boost_seconds_left(user)}
    if user.balance < game.BOOST_COST:
        return {"ok": False, "reason": "not_enough"}
    user.balance -= game.BOOST_COST
    user.boost_until = game.now() + game.BOOST_DURATION
    return {"ok": True, "seconds_left": game.boost_seconds_left(user)}


# --- Улучшения -----------------------------------------------------------

def buy_upgrade(user: User, kind: str) -> dict:
    if kind not in game.UPGRADE_CONFIG:
        return {"ok": False, "reason": "unknown"}
    lvl = game.get_upgrade_level(user, kind)
    cost = game.upgrade_cost(kind, lvl)
    if user.balance < cost:
        return {"ok": False, "reason": "not_enough", "cost": cost}
    user.balance -= cost
    if kind == "click":
        user.click_level += 1
    elif kind == "income":
        user.income_level += 1
    elif kind == "autoclick":
        user.autoclick_level += 1
    game.apply_xp(user, 10)
    return {"ok": True, "cost": cost}


# --- Кейсы ---------------------------------------------------------------

async def list_cases(session: AsyncSession) -> list[dict]:
    cases = (await session.scalars(
        select(Case).options(selectinload(Case.items).selectinload(CaseItem.item))
    )).all()
    out = []
    for c in cases:
        drops = sorted(c.items, key=lambda ci: ci.item.price, reverse=True)
        out.append({
            "id": c.id,
            "name": c.name,
            "price": round(c.price, 2),
            "image": c.image,
            "is_free": c.is_free,
            "items": [_item_json(ci.item) for ci in drops],
        })
    return out


def _item_json(item: Item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "subtitle": item.subtitle,
        "rarity": item.rarity,
        "price": round(item.price, 2),
        "image": item.image,
    }


async def open_case(session: AsyncSession, user: User, case_id: int) -> dict:
    case = await session.scalar(
        select(Case).where(Case.id == case_id).options(
            selectinload(Case.items).selectinload(CaseItem.item)
        )
    )
    if case is None or not case.items:
        return {"ok": False, "reason": "not_found"}

    if case.is_free:
        if not free_case_available(user, case.id):
            return {"ok": False, "reason": "cooldown", "seconds_left": free_case_seconds_left(user)}
        user.last_free_case_at = game.now()
    else:
        if user.balance < case.price:
            return {"ok": False, "reason": "not_enough", "price": round(case.price, 2)}
        user.balance -= case.price

    weights = [ci.weight for ci in case.items]
    won: CaseItem = random.choices(case.items, weights=weights, k=1)[0]
    item = won.item

    session.add(InventoryItem(user_id=user.id, item_id=item.id))
    user.cases_opened += 1
    game.apply_xp(user, game.XP_PER_CASE)

    return {"ok": True, "item": _item_json(item)}


# --- Инвентарь -----------------------------------------------------------

async def get_inventory(session: AsyncSession, user: User) -> list[dict]:
    rows = (await session.scalars(
        select(InventoryItem).where(InventoryItem.user_id == user.id)
        .options(selectinload(InventoryItem.item))
        .order_by(InventoryItem.acquired_at.desc())
    )).all()
    return [{"inv_id": r.id, **_item_json(r.item)} for r in rows]


async def sell_item(session: AsyncSession, user: User, inv_id: int) -> dict:
    row = await session.scalar(
        select(InventoryItem).where(
            InventoryItem.id == inv_id, InventoryItem.user_id == user.id
        ).options(selectinload(InventoryItem.item))
    )
    if row is None:
        return {"ok": False, "reason": "not_found"}
    price = row.item.price
    user.balance += price
    await session.delete(row)
    return {"ok": True, "amount": round(price, 2)}


# --- Апгрейд предметов (шанс улучшить предмет в более дорогой) ------------

async def upgrade_item(session: AsyncSession, user: User, inv_id: int, target_item_id: int) -> dict:
    src = await session.scalar(
        select(InventoryItem).where(
            InventoryItem.id == inv_id, InventoryItem.user_id == user.id
        ).options(selectinload(InventoryItem.item))
    )
    target = await session.scalar(select(Item).where(Item.id == target_item_id))
    if src is None or target is None:
        return {"ok": False, "reason": "not_found"}
    if target.price <= src.item.price:
        return {"ok": False, "reason": "bad_target"}

    # Шанс = отношение цен с домом 5%
    chance = min(0.95, (src.item.price / target.price) * 0.95)
    roll = random.random()
    success = roll < chance

    await session.delete(src)  # исходный предмет всегда сгорает
    if success:
        session.add(InventoryItem(user_id=user.id, item_id=target.id))
        game.apply_xp(user, 30)
    return {
        "ok": True,
        "success": success,
        "chance": round(chance, 4),
        "target": _item_json(target),
    }


# --- Контракты (trade-up: 3+ предмета -> 1 новый) ------------------------

async def contract(session: AsyncSession, user: User, inv_ids: list[int]) -> dict:
    if len(inv_ids) < 3:
        return {"ok": False, "reason": "need_three"}
    rows = (await session.scalars(
        select(InventoryItem).where(
            InventoryItem.id.in_(inv_ids), InventoryItem.user_id == user.id
        ).options(selectinload(InventoryItem.item))
    )).all()
    if len(rows) != len(set(inv_ids)):
        return {"ok": False, "reason": "not_found"}

    total = sum(r.item.price for r in rows)
    target_value = total * 0.85  # дом 15%

    # Ищем предмет, ближайший по цене к target_value
    all_items = (await session.scalars(select(Item))).all()
    candidates = sorted(all_items, key=lambda i: abs(i.price - target_value))
    # немного случайности среди 3 ближайших
    result_item = random.choice(candidates[:3])

    for r in rows:
        await session.delete(r)
    session.add(InventoryItem(user_id=user.id, item_id=result_item.id))
    game.apply_xp(user, 40)
    return {"ok": True, "result": _item_json(result_item), "invested": round(total, 2)}


# --- Сражения (1 на 1 против бота на выбранном кейсе) --------------------

async def get_top_players(session: AsyncSession, sort: str = "level") -> list[dict]:
    """ТОП-10 игроков по уровню или балансу."""
    order = User.level.desc() if sort == "level" else User.balance.desc()
    rows = (await session.scalars(select(User).order_by(order).limit(10))).all()
    result = []
    for i, u in enumerate(rows, 1):
        result.append({
            "rank": i,
            "first_name": u.first_name or "Player",
            "username": u.username,
            "level": u.level,
            "balance": round(u.balance, 2),
            "photo_url": u.photo_url,
        })
    return result


async def get_recent_drops(session: AsyncSession, min_price: float = 15000.0) -> list[dict]:
    """Последние 4 дропа дороже min_price среди всех игроков."""
    rows = (await session.scalars(
        select(InventoryItem)
        .join(InventoryItem.item)
        .join(InventoryItem.user)
        .where(Item.price >= min_price)
        .order_by(InventoryItem.acquired_at.desc())
        .limit(4)
        .options(selectinload(InventoryItem.item), selectinload(InventoryItem.user))
    )).all()
    result = []
    for r in rows:
        result.append({
            **_item_json(r.item),
            "player_name": r.user.first_name or "Player",
        })
    return result


def free_case_available(user: User, case_id: int) -> bool:
    """Проверяет, прошло ли 5 минут с последнего открытия бесплатного кейса."""
    last = game._aware(user.last_free_case_at)
    return last is None or (game.now() - last) >= game.FREE_CASE_COOLDOWN


def free_case_seconds_left(user: User) -> int:
    last = game._aware(user.last_free_case_at)
    if last is None:
        return 0
    left = game.FREE_CASE_COOLDOWN - (game.now() - last)
    return max(int(left.total_seconds()), 0)


async def battle(session: AsyncSession, user: User, case_id: int) -> dict:
    case = await session.scalar(
        select(Case).where(Case.id == case_id).options(
            selectinload(Case.items).selectinload(CaseItem.item)
        )
    )
    if case is None or not case.items:
        return {"ok": False, "reason": "not_found"}
    if user.balance < case.price:
        return {"ok": False, "reason": "not_enough", "price": round(case.price, 2)}

    user.balance -= case.price
    weights = [ci.weight for ci in case.items]
    my = random.choices(case.items, weights=weights, k=1)[0].item
    bot = random.choices(case.items, weights=weights, k=1)[0].item

    win = my.price >= bot.price
    pot = round(my.price + bot.price, 2)
    if win:
        user.balance += pot
        game.apply_xp(user, 20)
    return {
        "ok": True,
        "win": win,
        "my_item": _item_json(my),
        "bot_item": _item_json(bot),
        "pot": pot,
    }
