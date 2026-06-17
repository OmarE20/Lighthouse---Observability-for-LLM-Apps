from lighthouse.metrics.percentiles import compute_percentiles


def test_percentiles_on_known_uniform_distribution():
    # 1..100 ms, nearest-rank method: p50 -> 50th, p95 -> 95th, p99 -> 99th value.
    values = list(range(1, 101))
    result = compute_percentiles([float(v) for v in values])
    assert result.p50 == 50
    assert result.p95 == 95
    assert result.p99 == 99
    assert result.min == 1
    assert result.max == 100
    assert result.count == 100


def test_percentiles_empty_input():
    result = compute_percentiles([])
    assert result.count == 0
    assert result.p50 == result.p95 == result.p99 == 0


def test_percentile_tail_sensitivity_vs_average():
    # The top 20% of requests are a slow tail; p99 must surface it even
    # though it's a minority of traffic, while p50 stays on the fast path.
    values = [10.0] * 80 + [10_000.0] * 20
    result = compute_percentiles(values)
    assert result.p50 == 10.0
    assert result.p99 == 10_000.0
    assert result.avg < result.p99  # average dilutes the tail; p99 doesn't
