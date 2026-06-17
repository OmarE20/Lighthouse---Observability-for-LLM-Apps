"""Latency percentile aggregation -- p50/p95/p99, not averages.

Uses the nearest-rank method: sort the samples, pick the value at
ceil(p * n) - 1. This is the standard definition used by most APM tools and
is deterministic/easy to verify against known inputs in tests, unlike
interpolation-based methods that vary by convention.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class PercentileResult:
    p50: float
    p95: float
    p99: float
    count: int
    min: float
    max: float
    avg: float


def _nearest_rank(sorted_values: list[float], pct: float) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.0
    rank = max(1, math.ceil(pct * n))
    return sorted_values[min(rank, n) - 1]


def compute_percentiles(values: list[float]) -> PercentileResult:
    if not values:
        return PercentileResult(p50=0, p95=0, p99=0, count=0, min=0, max=0, avg=0)
    sorted_values = sorted(values)
    return PercentileResult(
        p50=_nearest_rank(sorted_values, 0.50),
        p95=_nearest_rank(sorted_values, 0.95),
        p99=_nearest_rank(sorted_values, 0.99),
        count=len(sorted_values),
        min=sorted_values[0],
        max=sorted_values[-1],
        avg=sum(sorted_values) / len(sorted_values),
    )
