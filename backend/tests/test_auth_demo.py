import importlib
import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("JWT_SECRET", "a-very-long-development-secret-key-123456")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import app.config
import app.db
import app.main

importlib.reload(app.config)
importlib.reload(app.db)
importlib.reload(app.main)


@pytest.mark.asyncio
async def test_demo_auth_flow() -> None:
    client = AsyncClient(transport=ASGITransport(app=app.main.app), base_url="http://testserver")
    async with client:
        reg = await client.post("/auth/register", json={"username": "demo-user", "password": "secure-pass-123"})
        assert reg.status_code == 200, reg.text
        login = await client.post("/auth/login", json={"username": "demo-user", "password": "secure-pass-123"})
        assert login.status_code == 200, login.text
        token = login.json()["token"]
        me = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
        assert me.json()["username"] == "demo-user"

        health = await client.get("/health")
        assert health.status_code == 200
        assert health.text == "ok"
