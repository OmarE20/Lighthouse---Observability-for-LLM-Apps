import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function CostChart({ data }) {
  const points = (data?.over_time || []).map((p) => ({
    time: new Date(p.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    cost_usd: p.cost_usd,
  }));

  return (
    <div className="card">
      <h3>Cost Over Time</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={points}>
          <CartesianGrid stroke="#1f2430" strokeDasharray="3 3" />
          <XAxis dataKey="time" stroke="#8b92a3" fontSize={11} />
          <YAxis stroke="#8b92a3" fontSize={11} tickFormatter={(v) => `$${v.toFixed(3)}`} />
          <Tooltip
            contentStyle={{ background: "#131722", border: "1px solid #1f2430" }}
            formatter={(v) => [`$${v.toFixed(6)}`, "cost"]}
          />
          <Line type="monotone" dataKey="cost_usd" stroke="#4ea1ff" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
