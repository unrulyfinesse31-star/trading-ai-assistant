# Trading AI Assistant

Institutional trading AI demo scaffold with a FastAPI backend. Broker adapters default to paper/test environments; order submission is disabled unless explicitly enabled. This is a demo, not financial advice or production-ready trading software.

## Backend

Build from the `backend/` directory:

```sh
docker build -t trading-ai-backend ./backend
docker run --rm -p 8000:8000 -e JWT_SECRET='set-a-long-random-secret' trading-ai-backend
```

Or run locally:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
JWT_SECRET='set-a-long-random-secret' uvicorn app.main:app --app-dir backend --reload
```

Health check: `GET /health`; Prometheus metrics: `GET /metrics`.

### Configuration and safety

- Configure `DATABASE_URL` to use PostgreSQL. The default is a local development URL.
- Set a strong `JWT_SECRET`; the application refuses to start without one.
- Binance uses sandbox mode by default. OANDA defaults to its practice API; Interactive Brokers defaults to paper-trading port `7497`.
- All adapter order methods require `ENABLE_LIVE_ORDERS=true`. Keep it unset unless you understand and have independently validated the risks. Use broker paper accounts and explicit risk controls before any live use.
- Store credentials in a secret manager or environment variables. Never commit credentials or `.env` files.

The included model pipeline is a training example; its output is not a trading recommendation. Validate data, costs, and risk controls independently before use.
