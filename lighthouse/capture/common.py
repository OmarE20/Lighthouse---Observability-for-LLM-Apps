from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from lighthouse.trace import get_or_create_trace_id
from lighthouse.pricing import compute_cost_usd
from lighthouse.storage.backend import CallRecord


def capture_call(
    emitter,
    *,
    provider: str,
    endpoint: str,
    model: str,
    fn: Callable[[], Any],
    extract: Callable[[Any], tuple[int, int, str]],
    prompt_version_id: str | None = None,
    prompt_inputs: dict | None = None,
    request_summary: dict | None = None,
) -> Any:
    """Run `fn()` (the real, synchronous SDK call) and emit a non-blocking
    record around it. `extract` pulls (input_tokens, output_tokens,
    response_text) out of the SDK's response object -- the only piece that
    differs between providers.

    On success or failure the timing/record logic is identical; on failure
    we still emit a record (status="error") and then re-raise so the
    caller's error handling is completely unaffected by instrumentation.
    """
    trace_id, trace_name = get_or_create_trace_id()
    start = time.perf_counter()
    status, error, input_tokens, output_tokens, response_text = "ok", None, 0, 0, None
    try:
        result = fn()
        input_tokens, output_tokens, response_text = extract(result)
        return result
    except Exception as exc:
        status, error = "error", str(exc)
        raise
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        cost_usd = compute_cost_usd(model, input_tokens, output_tokens)
        record = CallRecord(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            trace_name=trace_name,
            provider=provider,
            model=model,
            endpoint=endpoint,
            prompt_version_id=prompt_version_id,
            prompt_inputs=prompt_inputs,
            request=request_summary,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            status=status,
            error=error,
        )
        emitter.emit(record)
