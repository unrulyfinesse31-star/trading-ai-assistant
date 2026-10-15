import React from "react";
import PriceChart from "./chart/PriceChart";

function App() {
  return (
    <div style={{ padding: 16 }}>
      <h2>Institutional Trading AI — Live Demo (Simulation)</h2>
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ width: "800px", height: "400px", border: "1px solid #ccc" }}>
          <PriceChart symbol="BTC-USDT" wsUrl="ws://localhost:8000/ws/BTC-USDT" />
        </div>
        <div style={{ width: "420px" }}>
          <h4>Blotter / Signals (demo)</h4>
          <div id="blotter">No trades in demo. Extend by connecting signals endpoint.</div>
        </div>
      </div>
    </div>
  );
}

export default App;
