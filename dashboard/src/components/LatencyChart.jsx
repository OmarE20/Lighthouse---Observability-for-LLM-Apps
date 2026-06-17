import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function LatencyChart({ data }) {
  if (!data) return null;
  const rows = [
    { label: "p50", value: data.p50 },
    { label: "p95", value: data.p95 },
    { label: "p99", value: data.p99 },
  ];

  return (
    <div className="card">
      <h3>Latency Percentiles (not averages)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows}>
          <CartesianGrid stroke="#1f2430" strokeDasharray="3 3" />
          <XAxis dataKey="label" stroke="#8b92a3" fontSize={11} />
          <YAxis stroke="#8b92a3" fontSize={11} tickFormatter={(v) => `${v.toFixed(0)}ms`} />
          <Tooltip
            contentStyle={{ background: "#131722", border: "1px solid #1f2430" }}
            formatter={(v) => [`${v.toFixed(1)}ms`, "latency"]}
          />
          <Bar dataKey="value" fill="#f0b429" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="stat-row" style={{ marginTop: 12, marginBottom: 0 }}>
        <div className="stat">
          <div className="value">{data.count}</div>
          <div className="label">Requests</div>
        </div>
        <div className="stat">
          <div className="value">{data.avg.toFixed(1)}ms</div>
          <div className="label">Average (hides the tail)</div>
        </div>
      </div>
    </div>
  );
}
