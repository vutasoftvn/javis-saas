"""
Academy Python Boundary Contracts

Python equivalent of services/company/academy/contracts.ts

Used to reject Academy artifact refs from entering production
evidence ingestion, gate evaluation, or capability enablement.
"""
from __future__ import annotations

ACADEMY_ARTIFACT_SCHEME = "academy-artifact://"
ACADEMY_ID_PREFIX = "academy_"
ACADEMY_TEMPLATE_DRAFT_KIND = "academy_template_draft"


def assertNotAcademyReference(ref: str | None, field_name: str = "reference") -> None:
    """
    Asserts that a reference string is NOT an Academy reference.

    Raises ValueError if:
    - ref starts with "academy-artifact://"
    - ref starts with "academy_"
    """
    if not ref:
        return
    if ref.startswith(ACADEMY_ARTIFACT_SCHEME):
        raise ValueError(
            f"Production {field_name} cannot be an Academy artifact reference (academy-artifact://). "
            f"Academy output is synthetic and must not enter the live evidence ledger."
        )
    if ref.startswith(ACADEMY_ID_PREFIX):
        raise ValueError(
            f"Production {field_name} cannot reference an Academy identifier (academy_*). "
            f"Academy data is isolated from live projects, evidence, and gate evaluations."
        )


def assertNotAcademyTemplateDraft(kind: str | None, field_name: str = "artifact kind") -> None:
    """
    Asserts that an artifact kind is NOT 'academy_template_draft'.
    Call before creating Evidence from a workspace artifact.
    """
    if not kind:
        return
    if kind == ACADEMY_TEMPLATE_DRAFT_KIND:
        raise ValueError(
            f"Artifact of kind '{ACADEMY_TEMPLATE_DRAFT_KIND}' is ineligible for production evidence. "
            f"A human must replace Academy template sources with independent real-world sources."
        )


def isAcademyReference(ref: str | None) -> bool:
    """Returns True if ref is an Academy artifact reference or academy_* identifier."""
    if not ref:
        return False
    return ref.startswith(ACADEMY_ARTIFACT_SCHEME) or ref.startswith(ACADEMY_ID_PREFIX)
