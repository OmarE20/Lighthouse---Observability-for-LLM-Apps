import { useEffect, useState } from "react";
import { api } from "../api";

export default function TraceList() {
  const [traces, setTraces] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    api.traces().then(setTraces).catch(() => setTraces([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.trace(selected).then(setDetail).catch(() => setDetail(null));
  }, [selected]);

  return (
    <div className="card">
      <h3>Traces (sortable, drill-down)</h3>
      <table>
        <thead>
          <tr>
            <th>Started</th>
            <th>Name</th>
            <th>Calls</th>
            <th>Cost</th>
            <th>Latency</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr key={t.id} className="clickable" onClick={() => setSelected(t.id)}>
              <td>{new Date(t.started_at).toLocaleString()}</td>
              <td>{t.name}</td>
              <td>{t.call_count}</td>
              <td>${t.total_cost_usd.toFixed(6)}</td>
              <td>{t.total_latency_ms.toFixed(0)}ms</td>
              <td className={t.status === "ok" ? "status-ok" : "status-error"}>{t.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {detail && (
        <div style={{ marginTop: 16 }}>
          <h3>Trace {detail.id.slice(0, 8)} -- {detail.name}</h3>
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Endpoint</th>
                <th>Tokens (in/out)</th>
                <th>Latency</th>
                <th>Cost</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.calls.map((c) => (
                <tr key={c.id}>
                  <td>{c.model}</td>
                  <td>{c.endpoint}</td>
                  <td>{c.input_tokens}/{c.output_tokens}</td>
                  <td>{c.latency_ms.toFixed(0)}ms</td>
                  <td>${c.cost_usd.toFixed(6)}</td>
                  <td className={c.status === "ok" ? "status-ok" : "status-error"}>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
