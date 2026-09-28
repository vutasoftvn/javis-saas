"""Repository interface for AI Initiative evaluation suites and results (Task 7)."""

from __future__ import annotations

from typing import Protocol

from packages.agent.evaluations.initiative_suite import (
    AiEvaluationSuite,
    InitiativeEvaluationResult,
)


class InitiativeEvaluationRepository(Protocol):
    async def save_suite(self, suite: AiEvaluationSuite) -> AiEvaluationSuite: ...

    async def get_suite(
        self, workspace_id: str, initiative_id: str, revision: int | None = None
    ) -> AiEvaluationSuite | None: ...

    async def save_result(
        self, result: InitiativeEvaluationResult
    ) -> InitiativeEvaluationResult: ...

    async def get_latest_result(
        self, workspace_id: str, initiative_id: str
    ) -> InitiativeEvaluationResult | None: ...


class InMemoryInitiativeEvaluationRepository:
    def __init__(self) -> None:
        self._suites: dict[str, AiEvaluationSuite] = {}
        self._results: dict[str, list[InitiativeEvaluationResult]] = {}

    async def save_suite(self, suite: AiEvaluationSuite) -> AiEvaluationSuite:
        key = f"{suite.workspace_id}:{suite.initiative_id}:{suite.revision}"
        self._suites[key] = suite
        return suite

    async def get_suite(
        self, workspace_id: str, initiative_id: str, revision: int | None = None
    ) -> AiEvaluationSuite | None:
        if revision is not None:
            return self._suites.get(f"{workspace_id}:{initiative_id}:{revision}")
        matches = [
            s
            for s in self._suites.values()
            if s.workspace_id == workspace_id and s.initiative_id == initiative_id
        ]
        if not matches:
            return None
        matches.sort(key=lambda s: s.revision, reverse=True)
        return matches[0]

    async def save_result(
        self, result: InitiativeEvaluationResult
    ) -> InitiativeEvaluationResult:
        key = f"{result.workspace_id}:{result.initiative_id}"
        if key not in self._results:
            self._results[key] = []
        self._results[key].append(result)
        return result

    async def get_latest_result(
        self, workspace_id: str, initiative_id: str
    ) -> InitiativeEvaluationResult | None:
        key = f"{workspace_id}:{initiative_id}"
        res = self._results.get(key)
        if not res:
            return None
        return res[-1]
