from __future__ import annotations

import functools
from typing import Any

from lighthouse.capture.common import capture_call
from lighthouse.storage.backend import Storage


def _extract(response: Any) -> tuple[int, int, str | None]:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    output_tokens = getattr(usage, "output_tokens", 0) or 0
    text = None
    try:
        block = response.content[0]
        text = getattr(block, "text", None)
    except Exception:
        pass
    return input_tokens, output_tokens, text


def wrap_anthropic(client: Any, storage: Storage, emitter) -> Any:
    """Instrument an Anthropic client instance in place and return it.

    Mirrors `wrap_openai`: patches `client.messages.create` on this instance
    only, and strips the `lighthouse_*` kwargs before forwarding to the real
    SDK call.
    """
    original_create = client.messages.create

    @functools.wraps(original_create)
    def patched_create(*args, **kwargs):
        prompt_version_id = kwargs.pop("lighthouse_prompt_version_id", None)
        prompt_inputs = kwargs.pop("lighthouse_prompt_inputs", None)
        model = kwargs.get("model", "unknown")
        request_summary = {"model": model, "messages": kwargs.get("messages")}

        return capture_call(
            emitter,
            provider="anthropic",
            endpoint="messages",
            model=model,
            fn=lambda: original_create(*args, **kwargs),
            extract=_extract,
            prompt_version_id=prompt_version_id,
            prompt_inputs=prompt_inputs,
            request_summary=request_summary,
        )

    client.messages.create = patched_create
    return client
