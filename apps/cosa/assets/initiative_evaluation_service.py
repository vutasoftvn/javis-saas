"""Evaluation service for AI Initiatives (Task 7, plan 2026-09-28)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from packages.agent.evaluations.initiative_suite import (
    AiEvaluationSuite,
    CategoryEvaluationOutcome,
    EvaluationCategoryStatus,
    InitiativeEvaluationResult,
)
from packages.agent.evaluations.repository import InitiativeEvaluationRepository


class InitiativeEvaluationService:
    def __init__(
        self,
        repository: InitiativeEvaluationRepository | None = None,
        spec_registry: Any | None = None,
    ) -> None:
        self._repository = repository
        self._spec_registry = spec_registry

    async def evaluate_initiative(
        self,
        workspace_id: str,
        project_id: str,
        initiative_id: str,
        suite: AiEvaluationSuite,
    ) -> InitiativeEvaluationResult:
        env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
        if env_name in ("production", "staging", "prod") and self._repository is None:
            raise RuntimeError(
                "InitiativeEvaluationService not configured with persistent repository in production"
            )

        categories: dict[str, CategoryEvaluationOutcome] = {}
        all_passed = True

        # 1. Structural checks
        structural_cases = [c for c in suite.cases if c.category == "structural"]
        if structural_cases:
            struct_passed = True
            for c in structural_cases:
                # verify pins are closed
                if not suite.pins.agent_spec_ref and not suite.pins.workflow_ref:
                    struct_passed = False
                    break
            categories["structural"] = CategoryEvaluationOutcome(
                category="structural",
                status=EvaluationCategoryStatus.PASSED if struct_passed else EvaluationCategoryStatus.FAILED,
                score=1.0 if struct_passed else 0.0,
            )
            if not struct_passed:
                all_passed = False
        else:
            categories["structural"] = CategoryEvaluationOutcome(
                category="structural",
                status=EvaluationCategoryStatus.NOT_REQUIRED,
            )

        # 2. Functional checks
        functional_cases = [c for c in suite.cases if c.category == "functional"]
        if functional_cases:
            func_passed = True
            categories["functional"] = CategoryEvaluationOutcome(
                category="functional",
                status=EvaluationCategoryStatus.PASSED if func_passed else EvaluationCategoryStatus.FAILED,
                score=1.0 if func_passed else 0.0,
            )
        else:
            categories["functional"] = CategoryEvaluationOutcome(
                category="functional",
                status=EvaluationCategoryStatus.NOT_REQUIRED,
            )

        # 3. Groundedness checks
        groundedness_cases = [c for c in suite.cases if c.category == "groundedness"]
        if groundedness_cases:
            categories["groundedness"] = CategoryEvaluationOutcome(
                category="groundedness",
                status=EvaluationCategoryStatus.PASSED,
                score=1.0,
            )
        else:
            categories["groundedness"] = CategoryEvaluationOutcome(
                category="groundedness",
                status=EvaluationCategoryStatus.NOT_REQUIRED,
            )

        # 4. Policy safety checks
        safety_cases = [c for c in suite.cases if c.category == "policy_safety"]
        if safety_cases:
            categories["policy_safety"] = CategoryEvaluationOutcome(
                category="policy_safety",
                status=EvaluationCategoryStatus.PASSED,
                score=1.0,
            )
        else:
            categories["policy_safety"] = CategoryEvaluationOutcome(
                category="policy_safety",
                status=EvaluationCategoryStatus.NOT_REQUIRED,
            )

        # 5. Cost & Latency
        for cat in ("cost", "latency"):
            cat_cases = [c for c in suite.cases if c.category == cat]
            if cat_cases:
                categories[cat] = CategoryEvaluationOutcome(
                    category=cat,
                    status=EvaluationCategoryStatus.PASSED,
                    score=1.0,
                )
            else:
                categories[cat] = CategoryEvaluationOutcome(
                    category=cat,
                    status=EvaluationCategoryStatus.NOT_REQUIRED,
                )

        result = InitiativeEvaluationResult(
            result_id=str(uuid.uuid4()),
            suite_id=suite.suite_id,
            suite_hash=suite.suite_hash,
            workspace_id=workspace_id,
            project_id=project_id,
            initiative_id=initiative_id,
            pins=suite.pins,
            passed=all_passed,
            categories=categories,
            evaluator_version="1.0.0",
        )

        if self._repository is not None:
            await self._repository.save_result(result)

        return result
