"""Trace context: groups fan-out LLM calls (retrieval, planning, generation)
under one user-facing operation using a contextvar, so nested/sequential
calls inside a `with trace(...):` block share a trace_id without the caller
threading an id through every function signature.
"""
from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager

_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "lighthouse_trace_id", default=None
)
_current_trace_name: contextvars.ContextVar[str] = contextvars.ContextVar(
    "lighthouse_trace_name", default="trace"
)


def current_trace_id() -> str | None:
    return _current_trace_id.get()


def current_trace_name() -> str:
    return _current_trace_name.get()


@contextmanager
def trace(name: str = "trace"):
    """Group every Lighthouse-captured call made inside this block into one trace.

    Usage:
        with lighthouse.trace("answer_question"):
            retrieve(...)   # captured call 1
            generate(...)   # captured call 2  -- same trace_id as call 1
    """
    token_id = _current_trace_id.set(str(uuid.uuid4()))
    token_name = _current_trace_name.set(name)
    try:
        yield current_trace_id()
    finally:
        _current_trace_id.reset(token_id)
        _current_trace_name.reset(token_name)


def get_or_create_trace_id() -> tuple[str, str]:
    """Return (trace_id, trace_name) for the active trace, or mint a fresh
    one-off trace per call when nothing wraps it -- so every call always
    belongs to exactly one trace, even outside an explicit `trace()` block.
    """
    tid = current_trace_id()
    if tid is None:
        return str(uuid.uuid4()), "untraced-call"
    return tid, current_trace_name()
