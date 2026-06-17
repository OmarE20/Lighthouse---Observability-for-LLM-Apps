"""Measures the per-call latency Lighthouse instrumentation adds on top of a
raw (unwrapped) call, using a fake client with zero simulated network delay
so the only thing being timed is the wrapper's own overhead. Prints a number
suitable for pasting into the README.

Run: python examples/measure_overhead.py
"""
from __future__ import annotations

import statistics
import time
import types

from lighthouse.capture.emitter import Emitter
from lighthouse.capture.openai_wrapper import wrap_openai
from lighthouse.storage.backend import Storage

N_CALLS = 500


def _build_instant_client():
    class Usage:
        prompt_tokens = 50
        completion_tokens = 20

    class Message:
        content = "ok"

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]
        usage = Usage()

    def create(*args, **kwargs):
        return Response()

    completions = types.SimpleNamespace(create=create)
    chat = types.SimpleNamespace(completions=completions)
    return types.SimpleNamespace(chat=chat)


def main():
    raw_client = _build_instant_client()

    # Baseline: call the unwrapped function directly.
    baseline_times = []
    for _ in range(N_CALLS):
        start = time.perf_counter()
        raw_client.chat.completions.create(model="gpt-4o-mini", messages=[])
        baseline_times.append((time.perf_counter() - start) * 1000)

    storage = Storage("sqlite:///:memory:")
    emitter = Emitter(storage)
    wrapped_client = wrap_openai(_build_instant_client(), storage, emitter)

    wrapped_times = []
    for _ in range(N_CALLS):
        start = time.perf_counter()
        wrapped_client.chat.completions.create(model="gpt-4o-mini", messages=[])
        wrapped_times.append((time.perf_counter() - start) * 1000)

    baseline_avg = statistics.mean(baseline_times)
    wrapped_avg = statistics.mean(wrapped_times)
    overhead_ms = wrapped_avg - baseline_avg

    print(f"Baseline avg call time:    {baseline_avg:.4f} ms")
    print(f"Instrumented avg call time: {wrapped_avg:.4f} ms")
    print(f"Lighthouse overhead:        {overhead_ms:.4f} ms/call")
    print(f"({N_CALLS} calls each, SQLite in-memory storage, background emitter thread)")


if __name__ == "__main__":
    main()
