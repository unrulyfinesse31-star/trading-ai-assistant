import asyncio
import random
import time
from typing import Dict, List
import numpy as np

class CandleGenerator:
    def __init__(self, start_price: float = 100.0, volatility: float = 0.002):
        self.price = start_price
        self.volatility = volatility

    def next_candle(self, interval_seconds: int = 1):
        # simple random-walk to generate OHLCV in seconds (demo)
        open_p = self.price
        # make random walk step
        step = np.random.normal(loc=0.0, scale=self.volatility) * self.price
        close_p = max(0.0001, open_p + step)
        high_p = max(open_p, close_p) + abs(np.random.normal(0, self.volatility) * self.price)
        low_p = min(open_p, close_p) - abs(np.random.normal(0, self.volatility) * self.price)
        volume = max(0.01, np.random.exponential(scale=1.0))
        self.price = close_p
        ts = int(time.time() * 1000)
        return {
            "timestamp": ts,
            "open": round(open_p, 6),
            "high": round(high_p, 6),
            "low": round(low_p, 6),
            "close": round(close_p, 6),
            "volume": round(float(volume), 6),
        }

class MarketSimulator:
    def __init__(self, symbols: Dict[str, Dict]):
        # symbols: { "BTC-USDT": {"start": 28000, "vol": 0.002}, ... }
        self.symbols = symbols
        self.generators = {s: CandleGenerator(start_price=params.get("start", 100), volatility=params.get("vol", 0.002)) for s, params in symbols.items()}

    async def stream(self, symbol: str, send_json, interval_seconds: int = 1):
        gen = self.generators.get(symbol)
        if gen is None:
            raise ValueError("Unknown symbol")
        while True:
            candle = gen.next_candle(interval_seconds)
            await send_json(candle)
            await asyncio.sleep(interval_seconds)
