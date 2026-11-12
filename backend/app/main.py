import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.config import settings
from app.db import User, get_db, init_db

security = HTTPBearer(auto_error=False)
PORTFOLIO_STATE = {"cash": 100_000.0, "positions": {}}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be set before the application can start.")
    await init_db()
    yield


app = FastAPI(
    title="Trading AI Assistant",
    description="Minimal auth-enabled backend scaffold with a paper-trading demo.",
    lifespan=lifespan,
)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(RegisterRequest):
    pass


class DemoOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/auth/register")
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)):
    existing = await session.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"username": user.username}


@app.post("/auth/login")
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"token": create_access_token(user.username), "token_type": "bearer"}


@app.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}


def _simulated_price(symbol: str) -> float:
    digest = sum(ord(ch) for ch in symbol.upper())
    return round(50 + (digest % 250) / 10, 2)


@app.get("/portfolio")
async def portfolio(current_user: User = Depends(get_current_user)):
    positions = []
    total_value = float(PORTFOLIO_STATE["cash"])
    for symbol, position in PORTFOLIO_STATE["positions"].items():
        market_price = _simulated_price(symbol)
        units = float(position["quantity"])
        market_value = units * market_price
        pnl = (market_price - float(position["avg_price"])) * units
        total_value += market_value
        positions.append(
            {
                "symbol": symbol,
                "quantity": units,
                "avg_price": float(position["avg_price"]),
                "market_price": market_price,
                "market_value": round(market_value, 2),
                "pnl": round(pnl, 2),
            }
        )
    return {
        "username": current_user.username,
        "cash": round(float(PORTFOLIO_STATE["cash"]), 2),
        "total_value": round(total_value, 2),
        "positions": positions,
    }


@app.post("/portfolio/order")
async def simulate_order(
    payload: DemoOrderRequest,
    current_user: User = Depends(get_current_user),
):
    symbol = payload.symbol.upper()
    price = payload.price if payload.price is not None else _simulated_price(symbol)
    trade_value = payload.quantity * price
    existing = PORTFOLIO_STATE["positions"].get(symbol, {"quantity": 0.0, "avg_price": 0.0})

    if payload.side == "buy":
        if trade_value > float(PORTFOLIO_STATE["cash"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough cash for this simulated trade")
        new_quantity = float(existing["quantity"]) + payload.quantity
        old_cost = float(existing["quantity"]) * float(existing["avg_price"])
        new_cost = old_cost + trade_value
        new_avg = new_cost / new_quantity if new_quantity else 0.0
        PORTFOLIO_STATE["cash"] = round(float(PORTFOLIO_STATE["cash"]) - trade_value, 2)
        PORTFOLIO_STATE["positions"][symbol] = {"quantity": new_quantity, "avg_price": new_avg}
    else:
        current_quantity = float(existing["quantity"])
        if current_quantity < payload.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough shares in the simulated portfolio")
        PORTFOLIO_STATE["cash"] = round(float(PORTFOLIO_STATE["cash"]) + trade_value, 2)
        remaining = current_quantity - payload.quantity
        if remaining <= 0:
            PORTFOLIO_STATE["positions"].pop(symbol, None)
        else:
            PORTFOLIO_STATE["positions"][symbol] = {"quantity": remaining, "avg_price": float(existing["avg_price"]) }

    return {
        "username": current_user.username,
        "status": "simulated",
        "symbol": symbol,
        "side": payload.side,
        "quantity": payload.quantity,
        "price": price,
        "portfolio": await portfolio(current_user),
    }
