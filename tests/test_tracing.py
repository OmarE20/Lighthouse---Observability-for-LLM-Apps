"""Fan-out calls made inside one `with lighthouse.trace(...)` block must
land under a single trace_id.
"""
from lighthouse.trace import trace as trace_block
from lighthouse.capture.openai_wrapper import wrap_openai

from .conftest import make_fake_openai_client


def test_calls_inside_one_trace_block_share_trace_id(storage, emitter):
    client = wrap_openai(make_fake_openai_client(), storage, emitter)

    with trace_block("answer_question") as trace_id:
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "retrieve"}])
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "generate"}])

    emitter.flush()
    calls = storage.list_calls(limit=10)
    assert len(calls) == 2
    assert {c.trace_id for c in calls} == {trace_id}


def test_calls_outside_any_trace_block_get_distinct_traces(storage, emitter):
    client = wrap_openai(make_fake_openai_client(), storage, emitter)

    client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "a"}])
    client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "b"}])

    emitter.flush()
    calls = storage.list_calls(limit=10)
    assert len(calls) == 2
    assert calls[0].trace_id != calls[1].trace_id


def test_traces_are_independent_across_blocks(storage, emitter):
    client = wrap_openai(make_fake_openai_client(), storage, emitter)

    with trace_block("op1") as t1:
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "a"}])
    with trace_block("op2") as t2:
        client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "b"}])

    assert t1 != t2
    emitter.flush()
