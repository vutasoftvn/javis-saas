from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["TrustLevel", "UntrustedSourceContext", "ProvenanceMetadata"]


class TrustLevel(str, enum.Enum):
    """Mức độ tin cậy của nguồn dữ liệu theo Master Guide §34."""
    UNTRUSTED = "untrusted"  # Web scraping, third-party webhook, untrusted uploaded file, external ticket
    INTERNAL = "internal"    # Internal system data, database query
    VERIFIED = "verified"    # Cryptographically signed, audited connector payload
    SUPERVISED = "supervised"# Human-reviewed data


class UntrustedSourceContext(BaseModel):
    """Bao bọc ngữ cảnh cho các dữ liệu có mức tin cậy thấp hoặc chưa xác minh."""

    source_id: str
    source_type: str  # "uploaded_file", "web_search", "external_ticket", "connector_webhook"
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    sanitization_status: str = "raw"  # "raw", "sanitized", "quarantined"
    source_uri: Optional[str] = None
    author_principal: Optional[str] = None
    checksum: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_safe_for_unsupervised_execution(self) -> bool:
        return self.trust_level in (TrustLevel.VERIFIED, TrustLevel.SUPERVISED)


class ProvenanceMetadata(BaseModel):
    """Metadata truy xuất nguồn gốc dữ liệu phục vụ kiểm toán an ninh."""

    origin_id: str
    trust_level: TrustLevel
    propagated_from_run_id: Optional[str] = None
    tags: tuple[str, ...] = Field(default_factory=tuple)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
