"""The non-blocking guarantee: a failing/raising storage backend must not
break or measurably slow down the wrapped call.
"""
import time

from lighthouse.capture.emitter import Emitter
from lighthouse.capture.openai_wrapper import wrap_openai
from lighthouse.storage.backend import CallRecord, Storage

from .conftest import make_fake_openai_client


class ExplodingStorage(Storage):
    def __init__(self):
        # Skip the real Storage.__init__ entirely -- this fake never touches a DB.
        pass

    def ensure_trace(self, trace_id, name="trace"):
        raise RuntimeError("storage is down")

    def record_call(self, record: CallRecord):
        raise RuntimeError("storage is down")


def test_failing_storage_does_not_raise_or_break_call():
    storage = ExplodingStorage()
    emitter = Emitter(storage)
    client = make_fake_openai_client()
    wrapped = wrap_openai(client, storage, emitter)

    response = wrapped.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])

    assert response.choices[0].message.content == "hello"
    emitter.flush()


def test_failing_storage_does_not_add_meaningful_latency():
    storage = ExplodingStorage()
    emitter = Emitter(storage)
    client = make_fake_openai_client()
    wrapped = wrap_openai(client, storage, emitter)

    start = time.perf_counter()
    for _ in range(50):
        wrapped.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
    elapsed_per_call_ms = (time.perf_counter() - start) * 1000 / 50

    assert elapsed_per_call_ms < 5.0
    emitter.flush()


def test_raising_underlying_call_still_propagates(storage, emitter):
    client = make_fake_openai_client(responses="raise")
    wrapped = wrap_openai(client, storage, emitter)

    try:
        wrapped.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass

    emitter.flush()
    calls = storage.list_calls(limit=10)
    assert len(calls) == 1
    assert calls[0].status == "error"
