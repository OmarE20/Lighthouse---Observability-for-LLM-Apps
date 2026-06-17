"""Per-model pricing table: USD per 1M tokens, input vs output.

Prices are a point-in-time snapshot (mid-2025 list pricing) and will drift as
providers change rates -- this is exactly the kind of thing a real deployment
should periodically reconcile against actual provider invoices (see
metrics.cost.compare_to_invoice). Unknown models fall back to a configurable
default rather than raising, so capture never breaks on a new/unlisted model.
"""
from __future__ import annotations

# USD per 1,000,000 tokens
PRICING_TABLE: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    # Anthropic
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}

DEFAULT_PRICING = {"input": 1.00, "output": 3.00}


def price_for_model(model: str) -> dict[str, float]:
    if model in PRICING_TABLE:
        return PRICING_TABLE[model]
    for known_model, price in PRICING_TABLE.items():
        if model.startswith(known_model):
            return price
    return DEFAULT_PRICING


def compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = price_for_model(model)
    return (input_tokens / 1_000_000) * price["input"] + (output_tokens / 1_000_000) * price["output"]
