"""FastAPI-приложение: игровое API + раздача WebApp (статики)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.auth import parse_init_data
from app.config import settings
from app.database import get_session, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CS Case Bot API", lifespan=lifespan)


# --- Зависимость авторизации --------------------------------------------

async def current_user(
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    tg = parse_init_data(x_init_data)
    if tg is None:
        raise HTTPException(status_code=401, detail="Invalid Telegram init data")
    user = await service.get_or_create_user(session, tg)
    # начисляем накопленный пассивный доход при каждом обращении
    service.game.collect_passive_income(user)
    return user, session


# --- Тела запросов -------------------------------------------------------

class ClickBody(BaseModel):
    taps: int = 1


class UpgradeBody(BaseModel):
    kind: str


class CaseBody(BaseModel):
    case_id: int


class SellBody(BaseModel):
    inv_id: int


class ItemUpgradeBody(BaseModel):
    inv_id: int
    target_item_id: int


class ContractBody(BaseModel):
    inv_ids: list[int]


# --- Эндпоинты состояния -------------------------------------------------

@app.get("/api/state")
async def get_state(ctx=Depends(current_user)):
    user, session = ctx
    data = service.serialize_user(user)
    await session.commit()
    return data


@app.post("/api/click")
async def click(body: ClickBody, ctx=Depends(current_user)):
    user, session = ctx
    result = service.do_click(user, body.taps)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


@app.post("/api/daily")
async def daily(ctx=Depends(current_user)):
    user, session = ctx
    result = service.claim_daily(user)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


@app.post("/api/boost")
async def boost(ctx=Depends(current_user)):
    user, session = ctx
    result = service.activate_boost(user)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


@app.post("/api/upgrade")
async def upgrade(body: UpgradeBody, ctx=Depends(current_user)):
    user, session = ctx
    result = service.buy_upgrade(user, body.kind)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


# --- Кейсы и инвентарь ---------------------------------------------------

@app.get("/api/cases")
async def cases(ctx=Depends(current_user)):
    user, session = ctx
    result = await service.list_cases(session)
    await session.commit()
    return {"cases": result}


@app.post("/api/cases/open")
async def cases_open(body: CaseBody, ctx=Depends(current_user)):
    user, session = ctx
    result = await service.open_case(session, user, body.case_id)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


@app.get("/api/inventory")
async def inventory(ctx=Depends(current_user)):
    user, session = ctx
    items = await service.get_inventory(session, user)
    await session.commit()
    return {"items": items}


@app.post("/api/inventory/sell")
async def inventory_sell(body: SellBody, ctx=Depends(current_user)):
    user, session = ctx
    result = await service.sell_item(session, user, body.inv_id)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


# --- Апгрейд / Контракты / Сражения -------------------------------------

@app.post("/api/items/upgrade")
async def items_upgrade(body: ItemUpgradeBody, ctx=Depends(current_user)):
    user, session = ctx
    result = await service.upgrade_item(session, user, body.inv_id, body.target_item_id)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


@app.post("/api/contract")
async def contract(body: ContractBody, ctx=Depends(current_user)):
    user, session = ctx
    result = await service.contract(session, user, body.inv_ids)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


@app.post("/api/battle")
async def battle(body: CaseBody, ctx=Depends(current_user)):
    user, session = ctx
    result = await service.battle(session, user, body.case_id)
    data = service.serialize_user(user)
    await session.commit()
    return {**result, "state": data}


# --- Каталог предметов (для экрана апгрейда) -----------------------------

@app.get("/api/items")
async def items(ctx=Depends(current_user)):
    from sqlalchemy import select

    from app.models import Item
    user, session = ctx
    rows = (await session.scalars(select(Item).order_by(Item.price))).all()
    await session.commit()
    return {"items": [service._item_json(i) for i in rows]}


@app.get("/api/leaderboard")
async def leaderboard(kind: str = "level", ctx=Depends(current_user)):
    user, session = ctx
    if kind not in {"level", "balance"}:
        raise HTTPException(status_code=400, detail="Unknown leaderboard kind")
    rows = await service.leaderboard(session, kind)
    await session.commit()
    return {"players": rows}


@app.get("/api/drops/best")
async def best_drops(ctx=Depends(current_user)):
    user, session = ctx
    rows = await service.best_real_drops(session)
    await session.commit()
    return {"drops": rows}


# --- Статика / WebApp ----------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "debug": settings.debug}
