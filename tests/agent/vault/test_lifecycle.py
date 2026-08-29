"""M3 §5 — Document + SOP lifecycle state machine + procedural-context gate."""

from __future__ import annotations

import pytest
from agent.vault import (
    DocumentState,
    LifecycleError,
    SopDefinition,
    SopStatus,
    SopVersion,
    advance_document_state,
    advance_sop_status,
    assert_publishable,
    select_procedural_sops,
)

# --- Document lifecycle -------------------------------------------------


def test_document_happy_path_chain():
    s = DocumentState.QUARANTINED
    for nxt in (
        DocumentState.SCANNED,
        DocumentState.REVIEW_PENDING,
        DocumentState.PUBLISHED,
        DocumentState.ARCHIVED,
        DocumentState.PURGED,
    ):
        s = advance_document_state(s, nxt)
    assert s == DocumentState.PURGED


def test_document_illegal_skip_raises():
    with pytest.raises(LifecycleError, match="không hợp lệ"):
        advance_document_state(DocumentState.QUARANTINED, DocumentState.PUBLISHED)


def test_document_purged_is_terminal():
    with pytest.raises(LifecycleError):
        advance_document_state(DocumentState.PURGED, DocumentState.ARCHIVED)


def test_document_same_state_is_idempotent_noop():
    assert (
        advance_document_state(DocumentState.SCANNED, DocumentState.SCANNED)
        == DocumentState.SCANNED
    )


def test_document_reviewer_can_send_back_to_quarantine():
    assert (
        advance_document_state(DocumentState.REVIEW_PENDING, DocumentState.QUARANTINED)
        == DocumentState.QUARANTINED
    )


def test_assert_publishable_requires_vault_ref_and_scoped_uri():
    with pytest.raises(LifecycleError, match="vault_object_ref"):
        assert_publishable(vault_object_ref=None, source_uri="workspaces/1/x")
    with pytest.raises(LifecycleError, match="workspace/object identity"):
        assert_publishable(vault_object_ref="ref", source_uri="https://example.com/x.pdf")
    assert_publishable(
        vault_object_ref="ref", source_uri="workspaces/1001/documents/d1/versions/v1/blob"
    )  # no raise


# --- SOP lifecycle ---------------------------------------------------


def _sop_with_approved_version() -> SopDefinition:
    v = SopVersion(
        id=9001,
        workspace_id=1001,
        sop_id=5001,
        content_object_ref="workspaces/1001/sops/5001/versions/9001/blob",
        approved_by=42,
    )
    return SopDefinition(
        id=5001,
        workspace_id=1001,
        title="Onboarding",
        owner_member_id=7,
        status=SopStatus.REVIEW,
        current_version_id=9001,
        versions=[v],
    )


def test_sop_activate_requires_approved_current_version():
    sop = _sop_with_approved_version()
    assert advance_sop_status(sop, SopStatus.ACTIVE) == SopStatus.ACTIVE
    assert sop.status == SopStatus.ACTIVE


def test_sop_activate_blocked_when_version_unapproved():
    sop = _sop_with_approved_version()
    sop.versions[0].approved_by = None
    with pytest.raises(LifecycleError, match="chưa được duyệt"):
        advance_sop_status(sop, SopStatus.ACTIVE)


def test_sop_activate_blocked_when_no_current_version():
    sop = _sop_with_approved_version()
    sop.current_version_id = None
    with pytest.raises(LifecycleError, match="current_version_id"):
        advance_sop_status(sop, SopStatus.ACTIVE)


def test_sop_activate_blocked_when_version_other_workspace():
    sop = _sop_with_approved_version()
    sop.versions[0].workspace_id = 2002
    with pytest.raises(LifecycleError, match="khác workspace"):
        advance_sop_status(sop, SopStatus.ACTIVE)


def test_sop_illegal_transition_raises():
    sop = _sop_with_approved_version()
    sop.status = SopStatus.DRAFT
    with pytest.raises(LifecycleError, match="không hợp lệ"):
        advance_sop_status(sop, SopStatus.ACTIVE)


# --- procedural-context gate ---------------------------------------


def test_only_active_sops_enter_procedural_context():
    sops = [
        SopDefinition(
            id=1, workspace_id=1001, title="draft", owner_member_id=1, status=SopStatus.DRAFT
        ),
        SopDefinition(
            id=2, workspace_id=1001, title="review", owner_member_id=1, status=SopStatus.REVIEW
        ),
        SopDefinition(
            id=3, workspace_id=1001, title="active", owner_member_id=1, status=SopStatus.ACTIVE
        ),
        SopDefinition(
            id=4, workspace_id=1001, title="retired", owner_member_id=1, status=SopStatus.RETIRED
        ),
    ]
    selected = select_procedural_sops(sops)
    assert [s.title for s in selected] == ["active"]


def test_procedural_gate_filters_cross_workspace():
    sops = [
        SopDefinition(
            id=3, workspace_id=1001, title="mine", owner_member_id=1, status=SopStatus.ACTIVE
        ),
        SopDefinition(
            id=5, workspace_id=2002, title="theirs", owner_member_id=1, status=SopStatus.ACTIVE
        ),
    ]
    selected = select_procedural_sops(sops, workspace_id=1001)
    assert [s.title for s in selected] == ["mine"]
