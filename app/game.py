"""Игровые формулы и константы: уровни, доход, стоимость улучшений, бонусы."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import User

# --- Экономика улучшений -------------------------------------------------

# Базовые значения дохода
BASE_CLICK = 1.0          # доход за клик на 1 уровне
CLICK_STEP = 0.35         # прибавка за каждый уровень "Доход за клик"
BASE_PER_SECOND = 0.0
PER_SECOND_STEP = 0.25    # прибавка за каждый уровень "Доход в секунду"
AUTOCLICK_STEP = 0.15     # автоклик добавляет доход в секунду

# Стоимость апгрейда: base * (growth ** level)
UPGRADE_CONFIG = {
    "click": {"base": 75, "growth": 1.22, "step": CLICK_STEP, "title": "Доход за клик"},
    "income": {"base": 300, "growth": 1.28, "step": PER_SECOND_STEP, "title": "Доход в секунду"},
    "autoclick": {"base": 900, "growth": 1.35, "step": AUTOCLICK_STEP, "title": "Автоклик"},
}

# Ежедневный бонус растёт со стриком (но здесь простой вариант — фикс за день)
DAILY_BONUS = 500.0
DAILY_COOLDOWN = timedelta(hours=24)

# Буст удваивает доход
BOOST_MULTIPLIER = 2.0
BOOST_DURATION = timedelta(minutes=15)
BOOST_COST = 2000.0

FREE_CASE_COOLDOWN = timedelta(minutes=5)
BIG_DROP_MIN_PRICE = 15000.0

# XP
XP_PER_CLICK = 1
XP_PER_CASE = 50


def now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite может вернуть naive datetime — приводим к UTC-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# --- Уровни --------------------------------------------------------------

def xp_for_level(level: int) -> int:
    """Сколько всего XP нужно, чтобы достичь начала данного уровня."""
    # Плавная кривая: сумма 1000 * n^1.5
    total = 0
    for n in range(1, level):
        total += int(1000 * (n ** 1.4))
    return total


def level_progress(user: User) -> dict:
    """Возвращает данные прогресса уровня для UI."""
    current_start = xp_for_level(user.level)
    next_start = xp_for_level(user.level + 1)
    span = max(next_start - current_start, 1)
    into = max(user.xp - current_start, 0)
    return {
        "level": user.level,
        "xp": user.xp,
        "xp_into_level": into,
        "xp_for_next": span,
        "xp_total_next": next_start,
        "progress": min(into / span, 1.0),
    }


def apply_xp(user: User, amount: int) -> int:
    """Начисляет XP и повышает уровень при необходимости. Возвращает кол-во новых уровней."""
    user.xp += amount
    levels_gained = 0
    while user.xp >= xp_for_level(user.level + 1):
        user.level += 1
        levels_gained += 1
    return levels_gained


# --- Доход ---------------------------------------------------------------

def click_income(user: User) -> float:
    return BASE_CLICK + CLICK_STEP * (user.click_level - 1)


def per_second_income(user: User) -> float:
    return (BASE_PER_SECOND
            + PER_SECOND_STEP * user.income_level
            + AUTOCLICK_STEP * user.autoclick_level)


def is_boost_active(user: User) -> bool:
    b = _aware(user.boost_until)
    return b is not None and b > now()


def boost_seconds_left(user: User) -> int:
    b = _aware(user.boost_until)
    if b is None:
        return 0
    return max(int((b - now()).total_seconds()), 0)


def income_multiplier(user: User) -> float:
    return BOOST_MULTIPLIER if is_boost_active(user) else 1.0


# --- Оффлайн доход -------------------------------------------------------

MAX_OFFLINE_SECONDS = 8 * 3600  # копим максимум 8 часов


def collect_passive_income(user: User) -> float:
    """Начисляет пассивный доход, накопленный с момента last_income_at."""
    last = _aware(user.last_income_at) or now()
    elapsed = (now() - last).total_seconds()
    elapsed = min(max(elapsed, 0), MAX_OFFLINE_SECONDS)
    earned = per_second_income(user) * elapsed * income_multiplier(user)
    if earned > 0:
        user.balance += earned
    user.last_income_at = now()
    return earned


# --- Улучшения -----------------------------------------------------------

def upgrade_cost(kind: str, current_level: int) -> float:
    cfg = UPGRADE_CONFIG[kind]
    return round(cfg["base"] * (cfg["growth"] ** current_level), 2)


def get_upgrade_level(user: User, kind: str) -> int:
    return {
        "click": user.click_level,
        "income": user.income_level,
        "autoclick": user.autoclick_level,
    }[kind]


def upgrades_state(user: User) -> list[dict]:
    """Данные по всем улучшениям для UI."""
    out = []
    for kind, cfg in UPGRADE_CONFIG.items():
        lvl = get_upgrade_level(user, kind)
        out.append({
            "kind": kind,
            "title": cfg["title"],
            "level": lvl,
            "step": cfg["step"],
            "cost": upgrade_cost(kind, lvl),
        })
    return out
