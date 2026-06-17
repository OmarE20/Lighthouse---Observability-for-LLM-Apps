"""Cost attribution rollups: by model, by endpoint, over time windows.

Costs are computed once at capture time (lighthouse.pricing) and stored on
each call row, so rollups here are pure aggregation -- no re-pricing, which
keeps historical costs stable even if the pricing table changes later.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from lighthouse.storage.models import Call


def rollup_by_key(calls: list[Call], key: str) -> dict[str, dict[str, float]]:
    """Roll up cost + token + call-count totals by `model` or `endpoint`."""
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0})
    for call in calls:
        k = getattr(call, key)
        bucket = totals[k]
        bucket["cost_usd"] += call.cost_usd
        bucket["calls"] += 1
        bucket["input_tokens"] += call.input_tokens
        bucket["output_tokens"] += call.output_tokens
    return dict(totals)


def cost_over_time(calls: list[Call], bucket_minutes: int = 60) -> list[dict]:
    """Bucket cost into fixed-width time windows for a time-series chart."""
    buckets: dict[dt.datetime, float] = defaultdict(float)
    for call in calls:
        ts = call.created_at
        epoch_minutes = int(ts.timestamp() // 60)
        bucket_start_minutes = (epoch_minutes // bucket_minutes) * bucket_minutes
        bucket_start = dt.datetime.fromtimestamp(bucket_start_minutes * 60, tz=dt.timezone.utc)
        buckets[bucket_start] += call.cost_usd
    return [{"timestamp": ts.isoformat(), "cost_usd": cost} for ts, cost in sorted(buckets.items())]


def compare_to_invoice(calls: list[Call], actual_invoice_usd: float) -> dict:
    """Compare Lighthouse's computed cost against a real provider invoice
    for the same period -- the method the README calls out for validating
    cost-attribution accuracy against actual billing.
    """
    computed = sum(c.cost_usd for c in calls)
    delta = computed - actual_invoice_usd
    pct_error = (delta / actual_invoice_usd * 100) if actual_invoice_usd else 0.0
    return {
        "computed_usd": computed,
        "actual_invoice_usd": actual_invoice_usd,
        "delta_usd": delta,
        "pct_error": pct_error,
    }
