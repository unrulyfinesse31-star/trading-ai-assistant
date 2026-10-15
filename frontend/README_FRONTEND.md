Frontend: React + TypeScript with Lightweight-Charts

1) Create project (if not already):
   npx create-react-app frontend --template typescript
   cd frontend
   npm install lightweight-charts

2) Replace src/App.tsx and add src/chart/PriceChart.tsx from scaffold.

3) Start:
   npm start

The frontend connects to ws://localhost:8000/ws/BTC-USDT by default. You can change the symbol prop when instantiating PriceChart.
