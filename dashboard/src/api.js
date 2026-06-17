const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  cost: (hours = 24) => get(`/api/metrics/cost?hours=${hours}`),
  latency: (hours = 24, model) =>
    get(`/api/metrics/latency?hours=${hours}${model ? `&model=${model}` : ""}`),
  volume: (hours = 24) => get(`/api/metrics/volume?hours=${hours}`),
  traces: (limit = 100) => get(`/api/traces?limit=${limit}`),
  trace: (id) => get(`/api/traces/${id}`),
  calls: (hours = 24, limit = 200) => get(`/api/calls?hours=${hours}&limit=${limit}`),
  prompts: () => get(`/api/prompts`),
  promptDiff: (name, versionA, versionB) =>
    get(`/api/prompts/${encodeURIComponent(name)}/diff?version_a=${versionA}&version_b=${versionB}`),
};
