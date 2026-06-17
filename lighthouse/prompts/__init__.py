"""Versioned prompt templates.

A `PromptTemplate` is registered under a name; every call to `.new_version()`
persists a new immutable version row (storage.create_prompt_version handles
auto-incrementing the version number). Rendering returns both the filled
text and the prompt_version_id, so a caller can pass that id straight into
`lighthouse_prompt_version_id` on a wrapped client call -- that's the link
that makes the diff viewer possible: every captured call knows which exact
template+version produced it.
"""
from __future__ import annotations

from dataclasses import dataclass

from lighthouse.storage.backend import Storage


@dataclass
class RenderedPrompt:
    text: str
    prompt_version_id: str
    version: int


class PromptTemplate:
    def __init__(self, name: str, storage: Storage):
        self.name = name
        self._storage = storage
        self._active: tuple[str, int, str] | None = None  # (id, version, template)

    def new_version(self, template: str) -> "PromptTemplate":
        pv = self._storage.create_prompt_version(self.name, template)
        self._active = (pv.id, pv.version, pv.template)
        return self

    def render(self, **inputs) -> RenderedPrompt:
        if self._active is None:
            raise ValueError(f"Prompt '{self.name}' has no version yet -- call new_version() first")
        pv_id, version, template = self._active
        return RenderedPrompt(text=template.format(**inputs), prompt_version_id=pv_id, version=version)


def diff_prompt_versions(storage: Storage, name: str, version_a: int, version_b: int) -> dict:
    """Build the data the side-by-side diff view needs: the two templates,
    plus every captured call run under each version so a human can compare
    real outputs for matching inputs across the prompt change.
    """
    versions = {pv.version: pv for pv in storage.list_prompt_versions(name)}
    if version_a not in versions or version_b not in versions:
        raise ValueError(f"Unknown version for prompt '{name}'")

    pv_a, pv_b = versions[version_a], versions[version_b]
    calls_a = storage.get_calls_for_prompt_version(pv_a.id)
    calls_b = storage.get_calls_for_prompt_version(pv_b.id)

    return {
        "name": name,
        "version_a": {"version": pv_a.version, "template": pv_a.template},
        "version_b": {"version": pv_b.version, "template": pv_b.template},
        "runs_a": [
            {
                "id": c.id,
                "inputs": c.prompt_inputs,
                "output": c.response_text,
                "latency_ms": c.latency_ms,
                "cost_usd": c.cost_usd,
                "created_at": c.created_at.isoformat(),
            }
            for c in calls_a
        ],
        "runs_b": [
            {
                "id": c.id,
                "inputs": c.prompt_inputs,
                "output": c.response_text,
                "latency_ms": c.latency_ms,
                "cost_usd": c.cost_usd,
                "created_at": c.created_at.isoformat(),
            }
            for c in calls_b
        ],
    }
