from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

_EVENT_TYPE_RE = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+\.v[0-9]+$")
_FORBIDDEN = re.compile(
    r"(access_token|secret|password|api[_-]?key|authorization|private[_-]?key)", re.I
)
_RESTRICTED_REF = re.compile(r"^[a-z0-9_]*(id|ref|hash|count)$", re.I)
MAX_PAYLOAD_BYTES = 16 * 1024


class Actor(BaseModel):
    kind: Literal["user", "agent", "system"]
    id: str = Field(min_length=1)


class Producer(BaseModel):
    service: str = Field(min_length=1)
    version: str = Field(min_length=1)


class Envelope(BaseModel):
    model_config = {"extra": "forbid"}

    eventId: str
    eventType: str
    schemaVersion: int = Field(ge=1)
    occurredAt: str
    workspaceId: str = Field(min_length=1)
    aggregateType: str = Field(min_length=1)
    aggregateId: str = Field(min_length=1)
    correlationId: str = Field(min_length=1)
    causationId: str | None = None
    actor: Actor
    producer: Producer
    classification: Literal["internal", "confidential", "restricted"]
    payload: dict[str, Any]

    @field_validator("eventType")
    @classmethod
    def _type(cls, v: str) -> str:
        if not _EVENT_TYPE_RE.match(v):
            raise ValueError(
                "eventType must match ^[a-z]+\\.[a-z_]+\\.[a-z_]+\\.v[0-9]+$ (past-tense, versioned)"
            )
        return v

    @field_validator("payload")
    @classmethod
    def _payload(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(v).encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError("payload exceeds 16KB limit")

        def scan(o: Any, path: str = "payload") -> None:
            if isinstance(o, dict):
                for k, sub in o.items():
                    if _FORBIDDEN.search(k):
                        raise ValueError(f"forbidden credential-shaped key in {path}.{k}")
                    scan(sub, f"{path}.{k}")

        scan(v)
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.classification == "restricted":
            offending = [k for k in self.payload if not _RESTRICTED_REF.match(k)]
            if offending:
                raise ValueError(
                    f"restricted classification requires reference-only payload; offending keys: {', '.join(offending)}"
                )


def validate_envelope(raw: dict) -> Envelope:
    return Envelope.model_validate(raw)
