"""FastAPI backend serving the dashboard.

Reads directly from the same Storage interface the capture layer writes
through (lighthouse.storage.backend.Storage) -- no separate read model, so
the dashboard is always looking at exactly what got captured.
"""
from __future__ import annotations

import datetime as dt
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from lighthouse.metrics import compute_percentiles, cost_over_time, rollup_by_key
from lighthouse.prompts import diff_prompt_versions
from lighthouse.storage.backend import Storage

load_dotenv()

app = FastAPI(title="Lighthouse API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("LIGHTHOUSE_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = Storage(os.environ.get("LIGHTHOUSE_DATABASE_URL"))


def _parse_window(hours: int) -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/calls")
def list_calls(
    hours: int = Query(24, ge=1, le=24 * 30),
    model: str | None = None,
    endpoint: str | None = None,
    trace_id: str | None = None,
    limit: int = Query(200, le=1000),
    offset: int = 0,
):
    since = _parse_window(hours)
    calls = storage.list_calls(since=since, model=model, endpoint=endpoint, trace_id=trace_id, limit=limit, offset=offset)
    return [_serialize_call(c) for c in calls]


@app.get("/api/traces")
def list_traces(limit: int = Query(100, le=500), offset: int = 0):
    traces = storage.list_traces(limit=limit, offset=offset)
    out = []
    for t in traces:
        calls = t.calls
        out.append(
            {
                "id": t.id,
                "name": t.name,
                "started_at": t.started_at.isoformat(),
                "call_count": len(calls),
                "total_cost_usd": sum(c.cost_usd for c in calls),
                "total_latency_ms": sum(c.latency_ms for c in calls),
                "models": sorted({c.model for c in calls}),
                "status": "error" if any(c.status == "error" for c in calls) else "ok",
            }
        )
    return out


@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    t = storage.get_trace(trace_id)
    if t is None:
        raise HTTPException(404, "trace not found")
    return {
        "id": t.id,
        "name": t.name,
        "started_at": t.started_at.isoformat(),
        "calls": [_serialize_call(c) for c in sorted(t.calls, key=lambda c: c.created_at)],
    }


@app.get("/api/metrics/cost")
def metrics_cost(hours: int = Query(24, ge=1, le=24 * 30), bucket_minutes: int = 60):
    since = _parse_window(hours)
    calls = storage.list_calls(since=since, limit=100_000)
    return {
        "by_model": rollup_by_key(calls, "model"),
        "by_endpoint": rollup_by_key(calls, "endpoint"),
        "over_time": cost_over_time(calls, bucket_minutes=bucket_minutes),
        "total_usd": sum(c.cost_usd for c in calls),
    }


@app.get("/api/metrics/latency")
def metrics_latency(hours: int = Query(24, ge=1, le=24 * 30), model: str | None = None):
    since = _parse_window(hours)
    calls = storage.list_calls(since=since, model=model, limit=100_000)
    result = compute_percentiles([c.latency_ms for c in calls])
    return {
        "p50": result.p50,
        "p95": result.p95,
        "p99": result.p99,
        "count": result.count,
        "min": result.min,
        "max": result.max,
        "avg": result.avg,
    }


@app.get("/api/metrics/volume")
def metrics_volume(hours: int = Query(24, ge=1, le=24 * 30)):
    since = _parse_window(hours)
    calls = storage.list_calls(since=since, limit=100_000)
    return {
        "total_calls": len(calls),
        "error_count": sum(1 for c in calls if c.status == "error"),
        "total_tokens": sum(c.input_tokens + c.output_tokens for c in calls),
    }


@app.get("/api/prompts")
def list_prompts():
    versions = storage.list_prompt_versions()
    by_name: dict[str, list[int]] = {}
    for pv in versions:
        by_name.setdefault(pv.name, []).append(pv.version)
    return [{"name": name, "versions": sorted(v)} for name, v in by_name.items()]


@app.get("/api/prompts/{name}/diff")
def prompt_diff(name: str, version_a: int, version_b: int):
    try:
        return diff_prompt_versions(storage, name, version_a, version_b)
    except ValueError as e:
        raise HTTPException(404, str(e))


def _serialize_call(c) -> dict:
    return {
        "id": c.id,
        "trace_id": c.trace_id,
        "provider": c.provider,
        "model": c.model,
        "endpoint": c.endpoint,
        "prompt_version_id": c.prompt_version_id,
        "input_tokens": c.input_tokens,
        "output_tokens": c.output_tokens,
        "latency_ms": c.latency_ms,
        "cost_usd": c.cost_usd,
        "status": c.status,
        "error": c.error,
        "created_at": c.created_at.isoformat(),
    }
