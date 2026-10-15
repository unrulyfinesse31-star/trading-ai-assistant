import React from "react";
import { useState, useEffect } from "react";
import PriceChart from "./chart/PriceChart";
import "./styles.css";

const defaultApi = "http://localhost:8000";

function App() {
  const [symbols, setSymbols] = useState<string[]>(["BTC-USDT"]);
  const [selectedSymbol, setSelectedSymbol] = useState("BTC-USDT");
  const [overview, setOverview] = useState<any>({ portfolio: {}, signals: {}, positions: [], orders: [] });
  const [selectedSide, setSelectedSide] = useState("BUY");
  const [quantity, setQuantity] = useState("0.25");

  useEffect(() => {
    fetch(`${defaultApi}/api/symbols`)
      .then((r) => r.json())
      .then((data) => {
        setSymbols(data.symbols || []);
      })
      .catch((err) => console.error("Error fetching symbols", err));
  }, []);

  useEffect(() => {
    const loadOverview = () => {
      fetch(`${defaultApi}/api/overview`)
        .then((r) => r.json())
        .then((data) => setOverview(data))
        .catch((err) => console.error("Error fetching overview", err));
    };

    loadOverview();
    const interval = setInterval(loadOverview, 2000);
    return () => clearInterval(interval);
  }, []);

  const onPlaceOrder = async () => {
    const payload = {
      symbol: selectedSymbol,
      side: selectedSide,
      quantity: Number(quantity),
      strategy: "baseline",
    };

    const response = await fetch(`${defaultApi}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      alert(data.detail || "Order rejected");
      return;
    }
    alert(`Order filled: ${data.order.side} ${data.order.quantity} ${data.order.symbol}`);
  };

  const currentSignal = overview?.signals?.[selectedSymbol] || { side: "HOLD", confidence: 0.0, reasons: [] };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">LIVE TRADING DESK</div>
          <h1>Institutional Trading AI</h1>
        </div>
        <div className="status-pill">Paper trading / simulation</div>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Portfolio Equity</div>
          <div className="stat-value">${(overview.portfolio?.equity ?? 0).toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Unrealized P&L</div>
          <div className="stat-value positive">${(overview.portfolio?.unrealized_pnl ?? 0).toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Daily P&L</div>
          <div className="stat-value">${(overview.portfolio?.daily_pnl ?? 0).toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Positions</div>
          <div className="stat-value">{overview.portfolio?.active_positions ?? 0}</div>
        </div>
      </section>

      <section className="workspace">
        <div className="chart-panel panel">
          <div className="panel-header">
            <label>
              Symbol
              <select value={selectedSymbol} onChange={(e) => setSelectedSymbol(e.target.value)}>
                {symbols.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <div className={`signal-tag ${currentSignal.side.toLowerCase()}`}>
              {currentSignal.side} {Number(currentSignal.confidence || 0).toFixed(2)}
            </div>
          </div>
          <PriceChart symbol={selectedSymbol} wsUrl={`ws://localhost:8000/ws/${selectedSymbol}`} />
          <div className="signal-reasons">
            {(currentSignal.reasons || []).map((reason: string, idx: number) => (
              <div key={idx}>• {reason}</div>
            ))}
          </div>
        </div>

        <aside className="sidebar panel">
          <h3>Paper Order Ticket</h3>
          <label>
            Side
            <select value={selectedSide} onChange={(e) => setSelectedSide(e.target.value)}>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </label>
          <label>
            Quantity
            <input type="number" value={quantity} min="0.01" step="0.01" onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <button className="primary" onClick={onPlaceOrder}>Submit Order</button>

          <div className="mini-block">
            <h4>Position Book</h4>
            {overview.positions?.length ? (
              <ul>
                {overview.positions.map((pos: any) => (
                  <li key={pos.symbol}>
                    <span>{pos.symbol}</span>
                    <span>{pos.qty}</span>
                    <span>${pos.unrealized_pnl.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div>No positions</div>
            )}
          </div>
        </aside>
      </section>

      <section className="panel orders-panel">
        <h3>Recent orders</h3>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Symbol</th>
              <th>Side</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Strategy</th>
            </tr>
          </thead>
          <tbody>
            {(overview.orders || []).map((order: any) => (
              <tr key={order.id}>
                <td>{order.created_at || "now"}</td>
                <td>{order.symbol}</td>
                <td>{order.side}</td>
                <td>{order.quantity}</td>
                <td>{order.price}</td>
                <td>{order.strategy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export default App;
