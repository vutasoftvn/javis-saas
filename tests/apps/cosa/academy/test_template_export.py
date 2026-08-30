from __future__ import annotations

import pytest

from apps.cosa.academy.template_export import (
    ACADEMY_TEMPLATE_DRAFT_KIND,
    AcademyTemplateExport,
    export_template,
)


def test_export_template_produces_academy_draft_kind():
    """export_template returns an artifact of kind 'academy_template_draft'."""
    result = export_template(
        simulation_artifact_ref="academy-artifact://p0_discovery_v1/sim_abc123",
        body={"content": "Interview guide template", "score": 0.85, "feedback": "Good reasoning"},
        template_kind="interview_guide",
        workspace_id="ws-live-001",
        confirmed_by_account_id="acc-founder-001",
    )

    assert result.kind == ACADEMY_TEMPLATE_DRAFT_KIND
    assert result.academy_source_ref.startswith("academy-artifact://")
    assert "content" in result.body
    assert "Interview guide template" in result.body["content"]


def test_export_template_strips_simulation_scores():
    """export_template removes score, feedback, and synthetic_claim from body."""
    result = export_template(
        simulation_artifact_ref="academy-artifact://p0_discovery_v1/sim_abc123",
        body={
            "content": "Useful template content",
            "score": 0.9,
            "feedback": "Excellent",
            "rubric_score": 0.88,
            "advisory_score": 0.75,
            "simulation_score": 5,
        },
        template_kind="hypothesis_canvas",
        workspace_id="ws-001",
        confirmed_by_account_id="acc-001",
    )

    # Scores and feedback must be stripped
    assert "score" not in result.body
    assert "feedback" not in result.body
    assert "rubric_score" not in result.body
    assert "advisory_score" not in result.body
    assert "simulation_score" not in result.body

    # Content must remain
    assert result.body["content"] == "Useful template content"


def test_export_template_adds_provenance_block():
    """export_template adds _academy_provenance block that cannot be removed."""
    result = export_template(
        simulation_artifact_ref="academy-artifact://p3_pilot_v1/sim_xyz999",
        body={"template": "pilot review"},
        template_kind="pilot_review",
        workspace_id="ws-001",
        confirmed_by_account_id="acc-001",
    )

    assert "_academy_provenance" in result.body
    provenance = result.body["_academy_provenance"]
    assert provenance["ineligible_for_evidence"] is True
    assert provenance["requires_human_source_replacement"] is True
    assert "academy-artifact://" in provenance["source"]


def test_export_requires_human_confirmation():
    """export_template raises without confirmed_by_account_id."""
    with pytest.raises(ValueError, match=r"confirmation|confirmed_by"):
        export_template(
            simulation_artifact_ref="academy-artifact://p0/sim_001",
            body={"content": "template"},
            template_kind="guide",
            workspace_id="ws-001",
            confirmed_by_account_id="",
        )


def test_export_rejects_non_academy_artifact_ref():
    """export_template rejects refs that don't start with 'academy-artifact://'."""
    with pytest.raises(ValueError, match=r"academy-artifact://"):
        export_template(
            simulation_artifact_ref="artifact://live-workspace/data.pdf",
            body={"content": "template"},
            template_kind="guide",
            workspace_id="ws-001",
            confirmed_by_account_id="acc-001",
        )


def test_academy_template_export_dataclass_rejects_wrong_kind():
    """AcademyTemplateExport cannot be created with a non-draft kind."""
    with pytest.raises(ValueError, match=r"academy_template_draft"):
        AcademyTemplateExport(
            id="tmpl_001",
            workspace_id="ws-001",
            confirmed_by_account_id="acc-001",
            template_kind="guide",
            body={"content": "test"},
            academy_source_ref="academy-artifact://lesson/1",
            kind="evidence_candidate",  # WRONG — must not be allowed
        )
