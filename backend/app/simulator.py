import asyncio
import time
import numpy as np


class CandleGenerator:
    def __init__(self, start_price: float = 100.0, volatility: float = 0.002):
        self.price = start_price
        self.volatility = volatility

    def next_candle(self, interval_seconds: int = 1):
        open_p = self.price
        step = np.random.normal(loc=0.0, scale=self.volatility) * self.price
        close_p = max(0.0001, open_p + step)
        high_p = max(open_p, close_p) + abs(np.random.normal(0, self.volatility) * self.price)
        low_p = min(open_p, close_p) - abs(np.random.normal(0, self.volatility) * self.price)
        volume = max(0.01, np.random.exponential(scale=1.0))
        self.price = close_p
        ts = int(time.time() * 1000)
        return {
            "timestamp": ts,
            "open": round(float(open_p), 6),
            "high": round(float(high_p), 6),
            "low": round(float(low_p), 6),
            "close": round(float(close_p), 6),
            "volume": round(float(volume), 6),
        }


class MarketSimulator:
    def __init__(self, symbols: dict):
        self.symbols = symbols
        self.generators = {
            symbol: CandleGenerator(start_price=params.get("start", 100), volatility=params.get("vol", 0.002))
            for symbol, params in symbols.items()
        }
        self.series = {symbol: [] for symbol in symbols}

    def get_series(self, symbol: str):
        return list(self.series.get(symbol, []))

    async def stream(self, symbol: str, send_json, interval_seconds: int = 1):
        gen = self.generators.get(symbol)
        if gen is None:
            raise ValueError("Unknown symbol")

        while True:
            candle = gen.next_candle(interval_seconds)
            self.series.setdefault(symbol, []).append(candle)
            if len(self.series[symbol]) > 200:
                self.series[symbol] = self.series[symbol][-200:]
            await send_json(candle)
            await asyncio.sleep(interval_seconds)
