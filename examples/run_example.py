"""Tiny example app that doubles as the demo and a smoke test.

Runs a few "summarize an article" operations through two prompt versions,
grouping each operation's retrieval + generation calls into one trace. Uses
the real OpenAI client if OPENAI_API_KEY is set; otherwise falls back to a
local fake client with simulated latency/tokens so the example (and the
dashboard screenshots it feeds) works with zero setup.

Run: python examples/run_example.py
"""
from __future__ import annotations

import os
import random
import time
import types

from dotenv import load_dotenv

import lighthouse

load_dotenv()

ARTICLES = [
    "The city council approved a new transit line after years of debate.",
    "Researchers found a new exoplanet in a nearby star system.",
    "The local bakery celebrated fifty years of business this weekend.",
    "A startup raised funding to build cheaper batteries for EVs.",
]


def _build_fake_openai_client():
    """Simulated OpenAI-shaped client: no network, randomized latency/tokens
    so percentile charts and cost rollups have something interesting to show.
    """

    class Usage:
        def __init__(self, prompt_tokens, completion_tokens):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens

    class Message:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, content):
            self.message = Message(content)

    class Response:
        def __init__(self, content, prompt_tokens, completion_tokens):
            self.choices = [Choice(content)]
            self.usage = Usage(prompt_tokens, completion_tokens)

    def create(*, model, messages, **kwargs):
        # Simulate real network/inference latency, including an occasional
        # slow tail call so p99 in the dashboard isn't flat.
        time.sleep(random.choice([0.05, 0.08, 0.06, 0.4]))
        prompt_text = messages[-1]["content"]
        completion = f"[{model} summary] {prompt_text[:60]}..."
        return Response(
            content=completion,
            prompt_tokens=random.randint(80, 200),
            completion_tokens=random.randint(20, 60),
        )

    completions = types.SimpleNamespace(create=create)
    chat = types.SimpleNamespace(completions=completions)
    return types.SimpleNamespace(chat=chat)


def get_client():
    if os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI

        return OpenAI(), "gpt-4o-mini"
    print("OPENAI_API_KEY not set -- using a simulated client so the example runs with zero setup.")
    return _build_fake_openai_client(), "gpt-4o-mini"


def main():
    raw_client, model = get_client()
    client = lighthouse.wrap(raw_client)

    summarize = lighthouse.prompt("article_summary")
    summarize.new_version("Summarize this article in one sentence: {article}")
    v1 = summarize

    for article in ARTICLES:
        with lighthouse.trace("summarize_article"):
            # retrieval step (fan-out call #1 in the trace)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": f"Extract key facts from: {article}"}],
            )
            # generation step using prompt v1 (fan-out call #2, same trace)
            rendered = v1.render(article=article)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": rendered.text}],
                lighthouse_prompt_version_id=rendered.prompt_version_id,
                lighthouse_prompt_inputs={"article": article},
            )

    # A "silent" prompt change: shorter, more casual phrasing -- the kind of
    # tweak that the diff viewer is built to surface.
    summarize.new_version("Summarize this article in one casual sentence, like a tweet: {article}")
    v2 = summarize

    for article in ARTICLES:
        with lighthouse.trace("summarize_article"):
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": f"Extract key facts from: {article}"}],
            )
            rendered = v2.render(article=article)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": rendered.text}],
                lighthouse_prompt_version_id=rendered.prompt_version_id,
                lighthouse_prompt_inputs={"article": article},
            )

    time.sleep(0.5)  # let the background emitter drain before we summarize
    storage = lighthouse.get_storage()
    calls = storage.list_calls(limit=1000)
    print(f"\nCaptured {len(calls)} calls across {len({c.trace_id for c in calls})} traces.")
    print(f"Total cost: ${sum(c.cost_usd for c in calls):.6f}")
    print("Start the dashboard (`make serve` + `make dashboard`) to explore traces, costs, and the prompt diff view.")


if __name__ == "__main__":
    main()
