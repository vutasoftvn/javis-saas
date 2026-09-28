"""Immutable AI Initiative evaluation suite and drift detection (Task 7, plan 2026-09-28).

An AI Initiative evaluation suite pins:
- AgentSpec ref + definition hash
- Prompt hash
- Model route ref
- Workflow ref + definition hash
- Capability refs list
- Knowledge snapshot ref
- Metric revision

Material pin drift invalidates passing results without guessing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationCategoryStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_REQUIRED = "NOT_REQUIRED"


class EvaluationPinSet(BaseModel):
    agent_spec_ref: str | None = None
    agent_spec_hash: str | None = None
    prompt_hash: str | None = None
    model_route_ref: str | None = None
    workflow_ref: str | None = None
    workflow_hash: str | None = None
    capability_refs: list[str] = Field(default_factory=list)
    knowledge_snapshot_ref: str | None = None
    metric_revision: int | None = None


class AiEvaluationCase(BaseModel):
    case_id: str
    category: str  # structural, functional, groundedness, policy_safety, cost, latency
    description: str
    fixture_ref: str
    expected_output_pattern: str | None = None
    threshold: float | None = None


class AiEvaluationSuite(BaseModel):
    suite_id: str
    workspace_id: str
    project_id: str
    initiative_id: str
    revision: int
    pins: EvaluationPinSet
    cases: list[AiEvaluationCase] = Field(default_factory=list)
    suite_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        suite_id: str,
        workspace_id: str,
        project_id: str,
        initiative_id: str,
        revision: int,
        pins: EvaluationPinSet,
        cases: list[AiEvaluationCase],
    ) -> AiEvaluationSuite:
        hasher = hashlib.sha256()
        payload = json.dumps(
            {
                "pins": pins.model_dump(),
                "cases": [c.model_dump() for c in cases],
            },
            sort_keys=True,
        )
        hasher.update(payload.encode("utf-8"))
        suite_hash = hasher.hexdigest()
        return cls(
            suite_id=suite_id,
            workspace_id=workspace_id,
            project_id=project_id,
            initiative_id=initiative_id,
            revision=revision,
            pins=pins,
            cases=cases,
            suite_hash=suite_hash,
        )


class CategoryEvaluationOutcome(BaseModel):
    category: str
    status: EvaluationCategoryStatus = EvaluationCategoryStatus.NOT_REQUIRED
    score: float | None = None
    details: str | None = None


class InitiativeEvaluationResult(BaseModel):
    result_id: str
    suite_id: str
    suite_hash: str
    workspace_id: str
    project_id: str
    initiative_id: str
    pins: EvaluationPinSet
    passed: bool
    categories: dict[str, CategoryEvaluationOutcome] = Field(default_factory=dict)
    evaluator_version: str = "1.0.0"
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationDriftCheck(BaseModel):
    is_current: bool
    code: str | None = None
    reason: str | None = None
    drifted_fields: list[str] = Field(default_factory=list)


def assert_evaluation_current(
    snapshot: Any,
    result: InitiativeEvaluationResult,
) -> EvaluationDriftCheck:
    """Verifies that the evaluated pins match the current snapshot.
    If any material pin has drifted, returns EvaluationDriftCheck(is_current=False, code='evaluation_pin_drift').
    """
    drifted: list[str] = []

    pins = getattr(snapshot, "pins", None)
    if pins is None and isinstance(snapshot, dict):
        pins = snapshot.get("pins")

    if isinstance(pins, dict):
        snap_spec_ref = pins.get("agent_spec_ref")
        snap_spec_hash = pins.get("agent_spec_hash")
        snap_prompt_hash = pins.get("prompt_hash")
        snap_route = pins.get("model_route_ref")
        snap_wf_ref = pins.get("workflow_ref")
        snap_wf_hash = pins.get("workflow_hash")
        snap_caps = pins.get("capability_refs") or []
        snap_know = pins.get("knowledge_snapshot_ref")
    elif pins is not None:
        snap_spec_ref = getattr(pins, "agent_spec_ref", None)
        snap_spec_hash = getattr(pins, "agent_spec_hash", None)
        snap_prompt_hash = getattr(pins, "prompt_hash", None)
        snap_route = getattr(pins, "model_route_ref", None)
        snap_wf_ref = getattr(pins, "workflow_ref", None)
        snap_wf_hash = getattr(pins, "workflow_hash", None)
        snap_caps = getattr(pins, "capability_refs", [])
        snap_know = getattr(pins, "knowledge_snapshot_ref", None)
    else:
        snap_spec_ref = None
        snap_spec_hash = None
        snap_prompt_hash = None
        snap_route = None
        snap_wf_ref = None
        snap_wf_hash = None
        snap_caps = []
        snap_know = None

    if snap_spec_ref and result.pins.agent_spec_ref and snap_spec_ref != result.pins.agent_spec_ref:
        drifted.append("agent_spec_ref")
    if snap_spec_hash and result.pins.agent_spec_hash and snap_spec_hash != result.pins.agent_spec_hash:
        drifted.append("agent_spec_hash")
    if snap_prompt_hash and result.pins.prompt_hash and snap_prompt_hash != result.pins.prompt_hash:
        drifted.append("prompt_hash")
    if snap_route and result.pins.model_route_ref and snap_route != result.pins.model_route_ref:
        drifted.append("model_route_ref")
    if snap_wf_ref and result.pins.workflow_ref and snap_wf_ref != result.pins.workflow_ref:
        drifted.append("workflow_ref")
    if snap_wf_hash and result.pins.workflow_hash and snap_wf_hash != result.pins.workflow_hash:
        drifted.append("workflow_hash")
    if snap_know and result.pins.knowledge_snapshot_ref and snap_know != result.pins.knowledge_snapshot_ref:
        drifted.append("knowledge_snapshot_ref")
    if snap_caps and result.pins.capability_refs and sorted(snap_caps) != sorted(result.pins.capability_refs):
        drifted.append("capability_refs")

    if drifted:
        return EvaluationDriftCheck(
            is_current=False,
            code="evaluation_pin_drift",
            reason=f"Material pins have drifted: {', '.join(drifted)}",
            drifted_fields=drifted,
        )

    if not result.passed:
        return EvaluationDriftCheck(
            is_current=False,
            code="evaluation_failed",
            reason="Initiative evaluation suite has not passed",
            drifted_fields=[],
        )

    return EvaluationDriftCheck(is_current=True)
