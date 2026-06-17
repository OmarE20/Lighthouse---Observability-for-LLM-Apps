"""Lighthouse: drop-in observability for LLM apps.

Public API surface -- this is intentionally the entire integration contract.
Three lines to instrument a client:

    import lighthouse
    from openai import OpenAI
    client = lighthouse.wrap(OpenAI())

Everything else (storage, the emitter thread, trace grouping) is wired up
with sane defaults the first time `wrap()` is called, so there's no required
setup step before that. Call `lighthouse.init(database_url=...)` first only
if you want to override storage (e.g. point at Postgres in prod).
"""
from __future__ import annotations

from typing import Any

from dotenv import load_dotenv

from lighthouse.capture.emitter import Emitter
from lighthouse.prompts import PromptTemplate
from lighthouse.storage.backend import Storage
from lighthouse.trace import current_trace_id, trace

load_dotenv()

_storage: Storage | None = None
_emitter: Emitter | None = None


def init(database_url: str | None = None) -> Storage:
    """Explicitly configure storage (e.g. Postgres in prod). Optional --
    `wrap()` will lazily call this with defaults (local SQLite) if you skip it.
    """
    global _storage, _emitter
    _storage = Storage(database_url)
    _emitter = Emitter(_storage)
    return _storage


def _ensure_initialized() -> tuple[Storage, Emitter]:
    global _storage, _emitter
    if _storage is None:
        init()
    return _storage, _emitter  # type: ignore[return-value]


def wrap(client: Any) -> Any:
    """Instrument an OpenAI or Anthropic client instance in place. Detected
    by duck-typing the client's shape (chat.completions vs messages) so
    callers don't need a separate function per provider.
    """
    storage, emitter = _ensure_initialized()

    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        from lighthouse.capture.openai_wrapper import wrap_openai

        return wrap_openai(client, storage, emitter)
    if hasattr(client, "messages"):
        from lighthouse.capture.anthropic_wrapper import wrap_anthropic

        return wrap_anthropic(client, storage, emitter)

    raise TypeError(
        "lighthouse.wrap() only supports OpenAI and Anthropic client instances "
        "(expected `.chat.completions.create` or `.messages.create`)."
    )


def prompt(name: str) -> PromptTemplate:
    """Get (or implicitly create) a versioned prompt template by name."""
    storage, _ = _ensure_initialized()
    return PromptTemplate(name, storage)


def get_storage() -> Storage:
    storage, _ = _ensure_initialized()
    return storage


__all__ = ["wrap", "init", "trace", "prompt", "current_trace_id", "get_storage"]
