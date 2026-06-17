"""Non-blocking emit path.

This is the single most important file in the library: capture must never
slow down or break the wrapped call. A bounded queue + one background daemon
thread decouples "record this call" from "the call returned" -- emit() does
a non-blocking queue.put and returns in microseconds. If the queue is full
(storage backend wedged) we drop the record rather than block the caller's
app; if the storage write itself raises, the worker swallows it. Either way
the LLM call's return value to the user is untouched.
"""
from __future__ import annotations

import atexit
import queue
import threading
from typing import Callable

from lighthouse.storage.backend import CallRecord, Storage


class Emitter:
    def __init__(self, storage: Storage, maxsize: int = 10_000):
        self._storage = storage
        self._queue: "queue.Queue[CallRecord | None]" = queue.Queue(maxsize=maxsize)
        self._dropped = 0
        self._thread = threading.Thread(target=self._run, daemon=True, name="lighthouse-emitter")
        self._thread.start()
        atexit.register(self._shutdown)

    def emit(self, record: CallRecord, on_dropped: Callable[[], None] | None = None) -> None:
        # Pure enqueue -- no storage I/O on the caller's thread. ensure_trace
        # also happens in the worker so a slow/unreachable DB never adds
        # latency to the wrapped call, only to (irrelevant) capture lag.
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            self._dropped += 1
            if on_dropped:
                on_dropped()
        except Exception:
            # Never let a storage/queue problem propagate into the caller's app.
            pass

    @property
    def dropped_count(self) -> int:
        return self._dropped

    def _run(self) -> None:
        while True:
            record = self._queue.get()
            try:
                if record is None:
                    break
                try:
                    self._storage.ensure_trace(record.trace_id, record.trace_name)
                    self._storage.record_call(record)
                except Exception:
                    # Swallow: a broken storage backend must not crash the app
                    # or the emitter thread.
                    pass
            finally:
                self._queue.task_done()

    def _shutdown(self) -> None:
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass

    def flush(self, timeout: float = 2.0) -> None:
        """Block until every queued record has been processed (not just
        dequeued) -- used by tests/examples, never on the hot path. Relies
        on queue.task_done()/join() rather than polling .empty(), since
        .empty() goes true as soon as a record is dequeued, before its
        storage write has actually finished.
        """
        done = threading.Event()

        def waiter():
            self._queue.join()
            done.set()

        threading.Thread(target=waiter, daemon=True).start()
        done.wait(timeout)
