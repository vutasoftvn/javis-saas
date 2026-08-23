from __future__ import annotations

from agent_core.contracts.provenance import (
    ProvenanceMetadata,
    TrustLevel,
    UntrustedSourceContext,
)


def test_low_trust_provenance():
    """Kiểm thử Low-trust Provenance (§34 & §43.7)."""
    src_untrusted = UntrustedSourceContext(
        source_id="upload_cv_pdf_01",
        source_type="uploaded_file",
        trust_level=TrustLevel.UNTRUSTED,
        source_uri="https://files.example.com/unverified_cv.pdf",
        author_principal="external_candidate",
        extracted_text="Candidate raw text payload...",
    )
    assert src_untrusted.is_safe_for_unsupervised_execution() is False

    src_supervised = UntrustedSourceContext(
        source_id="hr_reviewed_doc_02",
        source_type="uploaded_file",
        trust_level=TrustLevel.SUPERVISED,
        sanitization_status="sanitized",
    )
    assert src_supervised.is_safe_for_unsupervised_execution() is True

    provenance = ProvenanceMetadata(
        origin_id=src_untrusted.source_id,
        trust_level=src_untrusted.trust_level,
        propagated_from_run_id="run_root_123",
        tags=("external_upload", "untrusted_pipeline"),
    )
    assert provenance.trust_level == TrustLevel.UNTRUSTED
