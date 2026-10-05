"""Tests for InitiativeEvaluationService (Task 7)."""

from __future__ import annotations

import pytest
from agent.evaluations.initiative_suite import (
    AiEvaluationCase,
    AiEvaluationSuite,
    EvaluationCategoryStatus,
    EvaluationPinSet,
)
from agent.evaluations.repository import (
    InMemoryInitiativeEvaluationRepository,
)

from apps.cosa.assets.initiative_evaluation_service import InitiativeEvaluationService

pytestmark = pytest.mark.asyncio


async def test_evaluate_initiative_success_with_in_memory_repository():
    repo = InMemoryInitiativeEvaluationRepository()
    service = InitiativeEvaluationService(repository=repo)

    pins = EvaluationPinSet(
        agent_spec_ref="cosa.agents.operations",
        agent_spec_hash="hash-abc-123",
        workflow_ref="workflow.reconciliation",
    )
    cases = [
        AiEvaluationCase(
            case_id="c-struct-1",
            category="structural",
            description="Verify no hardcoded secrets",
            fixture_ref="fixtures/struct_1.json",
        ),
        AiEvaluationCase(
            case_id="c-func-1",
            category="functional",
            description="Verify accurate transaction count",
            fixture_ref="fixtures/func_1.json",
        ),
    ]

    suite = AiEvaluationSuite.create(
        suite_id="suite-alpha",
        workspace_id="ws-1",
        project_id="proj-1",
        initiative_id="init-1",
        revision=1,
        pins=pins,
        cases=cases,
    )
    await repo.save_suite(suite)

    result = await service.evaluate_initiative(
        workspace_id="ws-1",
        project_id="proj-1",
        initiative_id="init-1",
        suite=suite,
    )

    assert result.passed is True
    assert result.categories["structural"].status == EvaluationCategoryStatus.PASSED
    assert result.categories["functional"].status == EvaluationCategoryStatus.PASSED
    # Unspecified categories MUST remain NOT_REQUIRED, not pass by default
    assert result.categories["groundedness"].status == EvaluationCategoryStatus.NOT_REQUIRED
    assert result.categories["cost"].status == EvaluationCategoryStatus.NOT_REQUIRED

    # Verify persisted in repository
    latest = await repo.get_latest_result("ws-1", "init-1")
    assert latest is not None
    assert latest.result_id == result.result_id


async def test_production_without_persistent_repo_fails_closed(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    service = InitiativeEvaluationService(repository=None)

    suite = AiEvaluationSuite.create(
        suite_id="suite-prod",
        workspace_id="ws-prod",
        project_id="proj-prod",
        initiative_id="init-prod",
        revision=1,
        pins=EvaluationPinSet(),
        cases=[],
    )

    with pytest.raises(RuntimeError, match="not configured with persistent repository"):
        await service.evaluate_initiative(
            workspace_id="ws-prod",
            project_id="proj-prod",
            initiative_id="init-prod",
            suite=suite,
        )
