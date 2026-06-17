import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function CostByModel({ data }) {
  const rows = Object.entries(data?.by_model || {}).map(([model, stats]) => ({
    model,
    cost_usd: stats.cost_usd,
    calls: stats.calls,
  }));

  return (
    <div className="card">
      <h3>Cost by Model</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows}>
          <CartesianGrid stroke="#1f2430" strokeDasharray="3 3" />
          <XAxis dataKey="model" stroke="#8b92a3" fontSize={11} />
          <YAxis stroke="#8b92a3" fontSize={11} tickFormatter={(v) => `$${v.toFixed(3)}`} />
          <Tooltip
            contentStyle={{ background: "#131722", border: "1px solid #1f2430" }}
            formatter={(v) => [`$${v.toFixed(6)}`, "cost"]}
          />
          <Bar dataKey="cost_usd" fill="#4ea1ff" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
