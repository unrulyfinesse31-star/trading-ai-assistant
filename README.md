# Trading AI Assistant

FastAPI backend scaffold for a trading AI demo. Broker adapters, order submission, database persistence, and a model pipeline are not implemented. This is not financial advice or production-ready trading software.

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

- Set a strong `JWT_SECRET`; the application refuses to start without one. Authentication is not implemented yet, so this setting is only a startup prerequisite.
- `DATABASE_URL` is reserved for future persistence; the scaffold does not connect to a database.
- No broker adapters or order methods are included. Any future integration must use Binance sandbox, OANDA practice, and Interactive Brokers paper-trading port `7497` by default, and must require `ENABLE_LIVE_ORDERS=true` before any live order submission.
- Store credentials in a secret manager or environment variables. Never commit credentials or `.env` files.

No model pipeline is included. Validate data, costs, and risk controls independently before any future use.

Run backend tests with `pip install -r backend/requirements-dev.txt` and `python -m pytest`.
