from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StandardEnvelope(BaseModel, Generic[T]):
    status: str = "success"
    code: int = 200
    data: T
    metadata: dict[str, Any] = Field(default_factory=dict)


def success_envelope(
    data: Any,
    *,
    code: int = 200,
    metadata: dict[str, Any] | None = None,
) -> dict:
    meta = metadata or {}
    meta.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    return {"status": "success", "code": code, "data": data, "metadata": meta}


def error_envelope(
    detail: str,
    *,
    code: int = 400,
    metadata: dict[str, Any] | None = None,
) -> dict:
    meta = metadata or {}
    meta.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    return {"status": "error", "code": code, "data": None, "metadata": meta, "detail": detail}
