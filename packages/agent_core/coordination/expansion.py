from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = [
    "ExpansionFingerprint",
    "ExpansionRecord",
    "ExpansionManager",
]


class ExpansionFingerprint(BaseModel):
    """Định danh mở rộng bất biến cho Subagent/Workflow fanout theo Master Guide §22 & §43.5.
    
    Ngăn chặn việc tạo sibling tree thứ hai cho cùng một quyết định uỷ quyền/fanout.
    """

    source_run_id: str
    source_node_or_decision_id: str
    spec_revision: str
    expansion_semantic_key: str

    def compute_hash(self) -> str:
        canonical_str = f"{self.source_run_id}:{self.source_node_or_decision_id}:{self.spec_revision}:{self.expansion_semantic_key}"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class ExpansionRecord(BaseModel):
    fingerprint_hash: str
    fingerprint: ExpansionFingerprint
    child_run_id: str
    status: str = "active"  # "active", "completed", "failed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    output_result: Optional[dict[str, Any]] = None


class ExpansionManager:
    """Quản trị Exact-Once Fanout & Subagent Delegation."""

    def __init__(self) -> None:
        self._expansions: dict[str, ExpansionRecord] = {}  # fingerprint_hash -> ExpansionRecord

    async def get_or_create_expansion(
        self,
        fingerprint: ExpansionFingerprint,
        child_run_id_factory: Any,
    ) -> tuple[ExpansionRecord, bool]:
        """Lấy bản ghi Expansion hiện có hoặc khởi tạo mới (trả về record, is_new)."""
        fp_hash = fingerprint.compute_hash()

        if fp_hash in self._expansions:
            return self._expansions[fp_hash], False

        new_child_run_id = (
            child_run_id_factory()
            if callable(child_run_id_factory)
            else str(child_run_id_factory)
        )
        rec = ExpansionRecord(
            fingerprint_hash=fp_hash,
            fingerprint=fingerprint,
            child_run_id=new_child_run_id,
            status="active",
        )
        self._expansions[fp_hash] = rec
        return rec, True

    async def complete_expansion(
        self,
        fingerprint: ExpansionFingerprint,
        output_result: dict[str, Any],
    ) -> Optional[ExpansionRecord]:
        fp_hash = fingerprint.compute_hash()
        rec = self._expansions.get(fp_hash)
        if not rec:
            return None
        rec.status = "completed"
        rec.output_result = output_result
        return rec
