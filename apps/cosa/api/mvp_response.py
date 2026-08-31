"""Agent Platform MVP Response Envelopes and Helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

MvpDataState = Literal["populated", "empty"]
MvpSourceKind = Literal[
    "company_db",
    "agent_db",
    "object_store",
    "control_plane",
    "external_connector",
]


class MvpSourceRef(BaseModel):
    kind: MvpSourceKind
    ref: str
    observed_at: datetime | None = None


class MvpResponseMeta(BaseModel):
    data_state: MvpDataState
    observed_at: datetime
    sources: list[MvpSourceRef] = Field(default_factory=list)


class MvpSuccess(BaseModel, Generic[T]):
    data: T
    meta: MvpResponseMeta


def mvp_list(
    items: list[T],
    sources: list[MvpSourceRef],
    observed_at: datetime | None = None,
) -> MvpSuccess[list[T]]:
    obs = observed_at or datetime.now(timezone.utc)
    return MvpSuccess(
        data=items,
        meta=MvpResponseMeta(
            data_state="populated" if len(items) > 0 else "empty",
            observed_at=obs,
            sources=sources,
        ),
    )


def mvp_item(
    item: T,
    sources: list[MvpSourceRef],
    observed_at: datetime | None = None,
) -> MvpSuccess[T]:
    obs = observed_at or datetime.now(timezone.utc)
    return MvpSuccess(
        data=item,
        meta=MvpResponseMeta(
            data_state="populated",
            observed_at=obs,
            sources=sources,
        ),
    )
