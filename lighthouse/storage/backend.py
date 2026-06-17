"""Storage interface.

One SQLAlchemy-backed implementation handles both SQLite (dev, zero-config)
and Postgres (prod) -- the dialect lives entirely in the connection URL, so
swapping backends is a config change, not a code change. This satisfies
"behind an interface" without hand-maintaining two parallel query layers.
"""
from __future__ import annotations

import datetime as dt
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from lighthouse.storage.models import Base, Call, PromptVersion, Trace

DEFAULT_SQLITE_PATH = os.path.expanduser("~/.lighthouse/lighthouse.db")


@dataclass
class CallRecord:
    trace_id: str
    trace_name: str
    provider: str
    model: str
    endpoint: str = "chat.completions"
    prompt_version_id: str | None = None
    prompt_inputs: dict | None = None
    request: dict | None = None
    response_text: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    status: str = "ok"
    error: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class Storage:
    """Thin persistence layer used by both the capture path and the API server."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or self._default_url()
        connect_args = {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        self.engine = create_engine(self.database_url, connect_args=connect_args)
        self._SessionFactory: sessionmaker = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _default_url() -> str:
        env_url = os.environ.get("LIGHTHOUSE_DATABASE_URL")
        if env_url:
            return env_url
        os.makedirs(os.path.dirname(DEFAULT_SQLITE_PATH), exist_ok=True)
        return f"sqlite:///{DEFAULT_SQLITE_PATH}"

    @contextmanager
    def session(self) -> Iterable[Session]:
        s = self._SessionFactory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # -- writes -----------------------------------------------------------

    def ensure_trace(self, trace_id: str, name: str = "trace") -> None:
        with self.session() as s:
            existing = s.get(Trace, trace_id)
            if existing is None:
                s.add(Trace(id=trace_id, name=name))

    def record_call(self, record: CallRecord) -> None:
        with self.session() as s:
            s.add(
                Call(
                    id=record.id,
                    trace_id=record.trace_id,
                    prompt_version_id=record.prompt_version_id,
                    provider=record.provider,
                    model=record.model,
                    endpoint=record.endpoint,
                    prompt_inputs=record.prompt_inputs,
                    request=record.request,
                    response_text=record.response_text,
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    latency_ms=record.latency_ms,
                    cost_usd=record.cost_usd,
                    status=record.status,
                    error=record.error,
                )
            )

    def create_prompt_version(self, name: str, template: str) -> PromptVersion:
        with self.session() as s:
            latest = (
                s.execute(
                    select(PromptVersion)
                    .where(PromptVersion.name == name)
                    .order_by(PromptVersion.version.desc())
                )
                .scalars()
                .first()
            )
            next_version = (latest.version + 1) if latest else 1
            pv = PromptVersion(id=str(uuid.uuid4()), name=name, version=next_version, template=template)
            s.add(pv)
            s.flush()
            s.refresh(pv)
            return pv

    # -- reads --------------------------------------------------------------

    def list_calls(
        self,
        since: dt.datetime | None = None,
        until: dt.datetime | None = None,
        model: str | None = None,
        endpoint: str | None = None,
        trace_id: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Call]:
        with self.session() as s:
            stmt = select(Call).order_by(Call.created_at.desc())
            if since:
                stmt = stmt.where(Call.created_at >= since)
            if until:
                stmt = stmt.where(Call.created_at <= until)
            if model:
                stmt = stmt.where(Call.model == model)
            if endpoint:
                stmt = stmt.where(Call.endpoint == endpoint)
            if trace_id:
                stmt = stmt.where(Call.trace_id == trace_id)
            stmt = stmt.limit(limit).offset(offset)
            rows = s.execute(stmt).scalars().all()
            s.expunge_all()
            return rows

    def list_traces(self, limit: int = 100, offset: int = 0) -> list[Trace]:
        with self.session() as s:
            stmt = select(Trace).order_by(Trace.started_at.desc()).limit(limit).offset(offset)
            rows = s.execute(stmt).scalars().all()
            for t in rows:
                _ = len(t.calls)
            s.expunge_all()
            return rows

    def get_trace(self, trace_id: str) -> Trace | None:
        with self.session() as s:
            trace = s.get(Trace, trace_id)
            if trace:
                _ = len(trace.calls)
                s.expunge_all()
            return trace

    def list_prompt_versions(self, name: str | None = None) -> list[PromptVersion]:
        with self.session() as s:
            stmt = select(PromptVersion).order_by(PromptVersion.name, PromptVersion.version)
            if name:
                stmt = stmt.where(PromptVersion.name == name)
            rows = s.execute(stmt).scalars().all()
            s.expunge_all()
            return rows

    def get_calls_for_prompt_version(self, prompt_version_id: str) -> list[Call]:
        with self.session() as s:
            stmt = (
                select(Call)
                .where(Call.prompt_version_id == prompt_version_id)
                .order_by(Call.created_at.desc())
            )
            rows = s.execute(stmt).scalars().all()
            s.expunge_all()
            return rows


_default_storage: Storage | None = None


def get_default_storage() -> Storage:
    global _default_storage
    if _default_storage is None:
        _default_storage = Storage()
    return _default_storage
