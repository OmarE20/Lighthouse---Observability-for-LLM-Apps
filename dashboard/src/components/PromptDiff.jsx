import { useEffect, useState } from "react";
import { api } from "../api";

export default function PromptDiff() {
  const [prompts, setPrompts] = useState([]);
  const [name, setName] = useState(null);
  const [versionA, setVersionA] = useState(null);
  const [versionB, setVersionB] = useState(null);
  const [diff, setDiff] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.prompts().then((data) => {
      setPrompts(data);
      if (data.length > 0) {
        setName(data[0].name);
        const versions = data[0].versions;
        setVersionA(versions[0]);
        setVersionB(versions[versions.length - 1]);
      }
    });
  }, []);

  useEffect(() => {
    if (!name || versionA == null || versionB == null) return;
    setError(null);
    api.promptDiff(name, versionA, versionB).then(setDiff).catch((e) => setError(e.message));
  }, [name, versionA, versionB]);

  const selected = prompts.find((p) => p.name === name);

  return (
    <div className="card">
      <h3>Prompt-Version Diff -- the headline feature</h3>
      <p style={{ color: "#8b92a3", fontSize: 13, marginTop: -8 }}>
        See exactly how outputs changed when a prompt template changed, side by side, on real captured runs.
      </p>

      {prompts.length === 0 && <p>No prompt versions captured yet. Run the example app first.</p>}

      {prompts.length > 0 && (
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          <select value={name || ""} onChange={(e) => setName(e.target.value)}>
            {prompts.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
          <select value={versionA ?? ""} onChange={(e) => setVersionA(Number(e.target.value))}>
            {selected?.versions.map((v) => (
              <option key={v} value={v}>
                v{v}
              </option>
            ))}
          </select>
          <span style={{ alignSelf: "center", color: "#8b92a3" }}>vs</span>
          <select value={versionB ?? ""} onChange={(e) => setVersionB(Number(e.target.value))}>
            {selected?.versions.map((v) => (
              <option key={v} value={v}>
                v{v}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <p className="status-error">{error}</p>}

      {diff && (
        <div className="diff-grid">
          <div>
            <div className="diff-template">{diff.version_a.template}</div>
            {diff.runs_a.length === 0 && <p style={{ color: "#8b92a3" }}>No captured runs for this version.</p>}
            {diff.runs_a.map((run) => (
              <div key={run.id} className="diff-run">
                <div>{run.output}</div>
                <div className="meta">
                  {JSON.stringify(run.inputs)} -- {run.latency_ms.toFixed(0)}ms -- ${run.cost_usd.toFixed(6)}
                </div>
              </div>
            ))}
          </div>
          <div>
            <div className="diff-template">{diff.version_b.template}</div>
            {diff.runs_b.length === 0 && <p style={{ color: "#8b92a3" }}>No captured runs for this version.</p>}
            {diff.runs_b.map((run) => (
              <div key={run.id} className="diff-run">
                <div>{run.output}</div>
                <div className="meta">
                  {JSON.stringify(run.inputs)} -- {run.latency_ms.toFixed(0)}ms -- ${run.cost_usd.toFixed(6)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
