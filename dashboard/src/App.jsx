import { useEffect, useState } from "react";
import { api } from "./api";
import CostChart from "./components/CostChart";
import CostByModel from "./components/CostByModel";
import LatencyChart from "./components/LatencyChart";
import TraceList from "./components/TraceList";
import PromptDiff from "./components/PromptDiff";

const TABS = ["Overview", "Traces", "Prompt Diff"];

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [hours, setHours] = useState(24);
  const [cost, setCost] = useState(null);
  const [latency, setLatency] = useState(null);
  const [volume, setVolume] = useState(null);

  useEffect(() => {
    api.cost(hours).then(setCost).catch(() => setCost(null));
    api.latency(hours).then(setLatency).catch(() => setLatency(null));
    api.volume(hours).then(setVolume).catch(() => setVolume(null));
  }, [hours]);

  return (
    <div className="app">
      <h1>Lighthouse</h1>
      <p className="subtitle">Observability for LLM apps -- traces, cost, latency percentiles, prompt diffs.</p>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
        <div style={{ marginLeft: "auto", alignSelf: "center" }}>
          <select value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            <option value={1}>Last 1h</option>
            <option value={24}>Last 24h</option>
            <option value={24 * 7}>Last 7d</option>
            <option value={24 * 30}>Last 30d</option>
          </select>
        </div>
      </div>

      {tab === "Overview" && (
        <>
          <div className="stat-row">
            <div className="stat">
              <div className="value">${(cost?.total_usd ?? 0).toFixed(6)}</div>
              <div className="label">Total Cost</div>
            </div>
            <div className="stat">
              <div className="value">{volume?.total_calls ?? 0}</div>
              <div className="label">Requests</div>
            </div>
            <div className="stat">
              <div className="value">{volume?.error_count ?? 0}</div>
              <div className="label">Errors</div>
            </div>
            <div className="stat">
              <div className="value">{volume?.total_tokens ?? 0}</div>
              <div className="label">Total Tokens</div>
            </div>
          </div>
          <div className="grid">
            <CostChart data={cost} />
            <CostByModel data={cost} />
          </div>
          <LatencyChart data={latency} />
        </>
      )}

      {tab === "Traces" && <TraceList />}
      {tab === "Prompt Diff" && <PromptDiff />}
    </div>
  );
}
