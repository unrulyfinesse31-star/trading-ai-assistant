# Project: Institutional Trading AI — Demo (simulation + live dashboard)

This demo includes:
- backend: FastAPI simulation server that streams simulated candle data over WebSockets.
- frontend: React + TypeScript app using Lightweight-Charts to display live candles.

Quickstart (local)
1) Backend
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

2) Frontend (Create React App TypeScript recommended)
   cd frontend
   # If you don't have a project yet, create one:
   npx create-react-app . --template typescript
   npm install lightweight-charts
   # Replace src/App.tsx and add src/chart/PriceChart.tsx from this scaffold
   npm start

WebSocket endpoints
- ws://localhost:8000/ws/{symbol}
  Example: ws://localhost:8000/ws/BTC-USDT

Notes
- This uses simulation only. When you give me repository owner/name, I can push this scaffold to GitHub and add CI/CD and Docker builds.
- Next options: add simulated/exchange order execution, blotter, P&L, signals, model-serving endpoints, and role-based auth.
