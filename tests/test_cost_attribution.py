from lighthouse.pricing import PRICING_TABLE, compute_cost_usd, price_for_model


def test_known_model_matches_table_math():
    price = PRICING_TABLE["gpt-4o-mini"]
    expected = (1_000_000 / 1_000_000) * price["input"] + (500_000 / 1_000_000) * price["output"]
    assert compute_cost_usd("gpt-4o-mini", 1_000_000, 500_000) == expected


def test_zero_tokens_costs_nothing():
    assert compute_cost_usd("gpt-4o", 0, 0) == 0.0


def test_unknown_model_falls_back_to_default_rather_than_raising():
    price = price_for_model("some-future-model-nobody-has-heard-of")
    assert price == {"input": 1.00, "output": 3.00}
    # Should not raise, and should produce a positive, finite cost.
    cost = compute_cost_usd("some-future-model-nobody-has-heard-of", 1000, 1000)
    assert cost > 0


def test_versioned_model_prefix_matches_base_pricing():
    base = price_for_model("claude-3-5-sonnet-20241022")
    prefixed = price_for_model("claude-3-5-sonnet-20241022-extra-suffix")
    assert base == prefixed
