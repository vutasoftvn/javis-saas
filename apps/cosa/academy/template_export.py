"""
Academy Template Export

One-way, human-confirmed export from Academy simulation to a live workspace artifact.

INVARIANTS:
1. Output artifact kind is always 'academy_template_draft'
2. Output is never an Evidence candidate, source ingestion record, gate input,
   metric snapshot, or task.
3. Requires explicit human confirmation (confirmed_by_account_id).
4. Body is stripped of simulation scores, model feedback, and synthetic claims
   EXCEPT for a permanent provenance/disclaimer block.
5. The exported artifact includes academy_source_ref starting with 'academy-artifact://'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.cosa.academy.simulation.contracts import ACADEMY_ARTIFACT_SCHEME

ACADEMY_TEMPLATE_DRAFT_KIND = "academy_template_draft"

TEMPLATE_EXPORT_DISCLAIMER = (
    "Mẫu này được xuất từ COSA Academy (học tập/mô phỏng). "
    "ĐÂY LÀ TEMPLATE — KHÔNG phải evidence sản xuất. "
    "Cần con người thay thế nguồn tham chiếu bằng dữ liệu thực tế trước khi sử dụng làm evidence."
)

# Fields to strip from simulation body before exporting (scores, feedback, synthetic claims)
_STRIP_FIELDS = frozenset(
    [
        "score",
        "rubric_score",
        "feedback",
        "simulation_score",
        "synthetic_claim",
        "model_feedback",
        "advisory_score",
    ]
)


@dataclass(frozen=True)
class AcademyTemplateExport:
    """
    Exported template from an Academy simulation.

    kind is always 'academy_template_draft'.
    academy_source_ref always starts with 'academy-artifact://'.
    """

    id: str
    workspace_id: str
    confirmed_by_account_id: str
    template_kind: str
    body: dict[str, Any]
    academy_source_ref: str
    disclaimer: str = TEMPLATE_EXPORT_DISCLAIMER

    # Always 'academy_template_draft' — ineligible for Evidence
    kind: str = ACADEMY_TEMPLATE_DRAFT_KIND

    def __post_init__(self) -> None:
        if not self.academy_source_ref.startswith(ACADEMY_ARTIFACT_SCHEME):
            raise ValueError(
                f"AcademyTemplateExport.academy_source_ref must start with 'academy-artifact://', "
                f"got: {self.academy_source_ref!r}"
            )
        if self.kind != ACADEMY_TEMPLATE_DRAFT_KIND:
            raise ValueError(
                f"AcademyTemplateExport.kind must be '{ACADEMY_TEMPLATE_DRAFT_KIND}', "
                f"got: {self.kind!r}"
            )
        if not self.confirmed_by_account_id:
            raise ValueError(
                "AcademyTemplateExport requires confirmed_by_account_id (human confirmation)"
            )


def _strip_synthetic_fields(body: dict[str, Any]) -> dict[str, Any]:
    """Remove simulation score and feedback fields from body; keep content structure only."""
    return {k: v for k, v in body.items() if k not in _STRIP_FIELDS}


def export_template(
    simulation_artifact_ref: str,
    body: dict[str, Any],
    template_kind: str,
    workspace_id: str,
    confirmed_by_account_id: str,
) -> AcademyTemplateExport:
    """
    Export a template from an Academy simulation.

    Args:
        simulation_artifact_ref: Must start with 'academy-artifact://'
        body: Simulation output body (scores/feedback will be stripped)
        template_kind: Category of template (e.g. 'interview_guide', 'hypothesis_canvas')
        workspace_id: Target workspace (receives a draft artifact, not evidence)
        confirmed_by_account_id: Human who clicked the export confirmation

    Returns:
        AcademyTemplateExport with cleaned body and permanent disclaimer
    """
    if not simulation_artifact_ref.startswith(ACADEMY_ARTIFACT_SCHEME):
        raise ValueError(
            f"simulation_artifact_ref must start with 'academy-artifact://', "
            f"got: {simulation_artifact_ref!r}"
        )
    if not confirmed_by_account_id:
        raise ValueError("Template export requires human confirmation (confirmed_by_account_id)")

    # Strip simulation scores and synthetic feedback
    clean_body = _strip_synthetic_fields(body)
    # Add permanent provenance block (cannot be removed)
    clean_body["_academy_provenance"] = {
        "source": simulation_artifact_ref,
        "disclaimer": TEMPLATE_EXPORT_DISCLAIMER,
        "ineligible_for_evidence": True,
        "requires_human_source_replacement": True,
    }

    import uuid

    export_id = f"tmpl_{uuid.uuid4().hex[:12]}"

    return AcademyTemplateExport(
        id=export_id,
        workspace_id=workspace_id,
        confirmed_by_account_id=confirmed_by_account_id,
        template_kind=template_kind,
        body=clean_body,
        academy_source_ref=simulation_artifact_ref,
        kind=ACADEMY_TEMPLATE_DRAFT_KIND,
    )
