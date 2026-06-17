from __future__ import annotations

import functools
from typing import Any

from lighthouse.capture.common import capture_call
from lighthouse.storage.backend import Storage


def _extract(response: Any) -> tuple[int, int, str | None]:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    text = None
    try:
        choice = response.choices[0]
        text = getattr(getattr(choice, "message", None), "content", None)
    except Exception:
        pass
    return input_tokens, output_tokens, text


def wrap_openai(client: Any, storage: Storage, emitter) -> Any:
    """Instrument an OpenAI client instance in place and return it.

    Patches `client.chat.completions.create` only on this instance (not the
    class), so unwrapped clients elsewhere in the process are unaffected.
    Pops the optional `lighthouse_prompt_name` / `lighthouse_prompt_version_id`
    / `lighthouse_prompt_inputs` kwargs before forwarding the call, so the
    real OpenAI SDK never sees Lighthouse-specific arguments.
    """
    original_create = client.chat.completions.create

    @functools.wraps(original_create)
    def patched_create(*args, **kwargs):
        prompt_version_id = kwargs.pop("lighthouse_prompt_version_id", None)
        prompt_inputs = kwargs.pop("lighthouse_prompt_inputs", None)
        model = kwargs.get("model", "unknown")
        request_summary = {"model": model, "messages": kwargs.get("messages")}

        return capture_call(
            emitter,
            provider="openai",
            endpoint="chat.completions",
            model=model,
            fn=lambda: original_create(*args, **kwargs),
            extract=_extract,
            prompt_version_id=prompt_version_id,
            prompt_inputs=prompt_inputs,
            request_summary=request_summary,
        )

    client.chat.completions.create = patched_create
    return client
