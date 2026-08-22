from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class ExternalSkillCandidate(BaseModel):
    id: str
    name: str
    description: str
    repository: str
    path: str
    commit: str | None = None
    license: str | None = None


@runtime_checkable
class CatalogSource(Protocol):
    def list_candidates(self) -> list[ExternalSkillCandidate]:
        ...


class StaticCatalogSource:
    """MVP discovery source: an in-memory list standing in for a parsed
    external catalog (e.g. awesome-agent-skills, blueprint §22). A real
    fetcher that parses a live GitHub-hosted catalog is later hardening —
    out of scope here; DISCOVER only needs a source of candidates, not a
    specific transport.
    """

    def __init__(self, candidates: list[ExternalSkillCandidate]) -> None:
        self._candidates = list(candidates)

    def list_candidates(self) -> list[ExternalSkillCandidate]:
        return list(self._candidates)
