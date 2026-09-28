from __future__ import annotations

import pytest

from apps.cosa.knowledge.initiative_readiness import (
    assert_initiative_knowledge_allowed,
    semantic_retrieval_wired,
)
from apps.cosa.models.ai_initiative_snapshot import AiInitiativePromotionSnapshot


def _snapshot(
    lifecycle_state: str = "VALIDATE",
    data_readiness_status: str | None = "READY",
    retrieval_mode: str | None = "lexical",
    workspace_id: str = "ws_1",
    initiative_id: str = "init_1",
) -> AiInitiativePromotionSnapshot:
    return AiInitiativePromotionSnapshot(
        workspace_id=workspace_id,
        project_id="proj_1",
        initiative_id=initiative_id,
        initiative_revision=1,
        decision_id="dec_1",
        decision_hash="hash_1",
        lifecycle_state=lifecycle_state,
        risk_tier="LOW",
        autonomy_tier="A1",
        data_readiness_status=data_readiness_status,
        retrieval_mode=retrieval_mode,
    )


def test_not_ready_assessment_denies_lexical_and_semantic():
    snapshot = _snapshot(data_readiness_status="NOT_READY", retrieval_mode="none")
    lexical = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "lexical"})
    assert lexical.allowed is False
    assert lexical.code == "data_readiness_not_ready"

    semantic = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "semantic"})
    assert semantic.allowed is False
    assert semantic.code == "data_readiness_not_ready"


def test_missing_assessment_denies():
    snapshot = _snapshot(data_readiness_status=None, retrieval_mode=None)
    result = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "lexical"})
    assert result.allowed is False
    assert result.code == "data_readiness_assessment_required"


def test_missing_snapshot_denies():
    result = assert_initiative_knowledge_allowed(None, {"retrieval_mode": "lexical"})
    assert result.allowed is False
    assert result.code == "initiative_snapshot_not_found"


def test_conditional_permits_only_declared_mode_never_higher():
    # CONDITIONAL + declared lexical: lexical allowed, semantic denied — a
    # human being able to see the data elsewhere never raises this ceiling.
    snapshot = _snapshot(data_readiness_status="CONDITIONAL", retrieval_mode="lexical")

    lexical = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "lexical"})
    assert lexical.allowed is True
    assert lexical.effective_retrieval_mode == "lexical"

    semantic = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "semantic"})
    assert semantic.allowed is False
    assert semantic.code == "retrieval_mode_exceeds_assessment"


def test_ready_assessment_does_not_enable_semantic_mode_without_pinned_provider_and_eval():
    # READY + declared semantic is still denied because no production
    # embedding provider is wired (Task 12 is a separate, ADR-gated step).
    snapshot = _snapshot(data_readiness_status="READY", retrieval_mode="semantic")
    result = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "semantic"})
    assert result.allowed is False
    assert result.code == "semantic_retrieval_not_ready"
    assert semantic_retrieval_wired() is False


def test_ready_lexical_allowed():
    snapshot = _snapshot(data_readiness_status="READY", retrieval_mode="lexical")
    result = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "lexical"})
    assert result.allowed is True
    assert result.effective_retrieval_mode == "lexical"


def test_paused_or_retired_initiative_denies_knowledge_access():
    for state in ("PAUSED", "RETIRED"):
        snapshot = _snapshot(lifecycle_state=state, data_readiness_status="READY", retrieval_mode="lexical")
        result = assert_initiative_knowledge_allowed(snapshot, {"retrieval_mode": "lexical"})
        assert result.allowed is False
        assert result.code == f"initiative_lifecycle_{state.lower()}"


def test_request_defaults_to_lexical_when_retrieval_mode_omitted():
    snapshot = _snapshot(data_readiness_status="READY", retrieval_mode="lexical")
    result = assert_initiative_knowledge_allowed(snapshot, {})
    assert result.allowed is True
    assert result.effective_retrieval_mode == "lexical"
