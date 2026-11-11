import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not os.getenv("JWT_SECRET", "").strip():
        raise RuntimeError("JWT_SECRET must be set before the application can start.")
    yield


app = FastAPI(
    title="Trading AI Assistant",
    description="Backend API scaffold. No broker execution or trading recommendations are provided.",
    lifespan=lifespan,
)


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
