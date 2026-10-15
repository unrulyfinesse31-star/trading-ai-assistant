import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict
from .simulator import MarketSimulator
import asyncio

app = FastAPI(title="Trading AI Demo — Simulation")

# configure demo symbols (BTC, EURUSD, BTC-PERP)
SYMBOLS = {
    "BTC-USDT": {"start": 28000, "vol": 0.002},
    "EUR-USD": {"start": 1.08, "vol": 0.00005},
    "BTC-PERP": {"start": 28000, "vol": 0.002},
}

sim = MarketSimulator(SYMBOLS)

@app.get("/api/symbols")
async def get_symbols():
    return JSONResponse(list(SYMBOLS.keys()))

@app.websocket("/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await websocket.accept()
    if symbol not in SYMBOLS:
        await websocket.send_json({"error": "unknown symbol"})
        await websocket.close()
        return
    try:
        # stream candles every 1 second (demo). In production, stream real data and allow timeframe param.
        await sim.stream(symbol, websocket.send_json, interval_seconds=1)
    except WebSocketDisconnect:
        return
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
