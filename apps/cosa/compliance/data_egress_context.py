from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Các category "cá nhân" bắt buộc phải có subject_reference trước khi rời
# COSA — tên category lấy đúng từ enum thật dùng ở Company
# (services/company/finance-legal/migrations/27_ai_compliance_governance.up.sql,
# cột max_data_category: NON_PERSONAL | PERSONAL | SENSITIVE_PERSONAL |
# BUSINESS_CONFIDENTIAL). Không tự đặt tên mới.
_PERSONAL_CATEGORIES = frozenset({"PERSONAL", "SENSITIVE_PERSONAL"})


class DirectMessageDataAccess(BaseModel):
    """Egress-context boundary cho 1 tin nhắn trực tiếp của người dùng đi vào
    model input (Task 4 — apps/cosa/compliance/data_egress_context.py).

    Đây là input "thô" do caller (Task 5 — chưa làm) khai báo trước khi
    resolver dựng `DataAccessClaim` thật. Model này CHỈ chịu trách nhiệm
    chứng minh nguồn gốc + toàn vẹn nội dung (source_ref/source_hash) và
    validate category — KHÔNG tự quyết định provider/model/purpose/retention;
    những field đó luôn lấy từ `ComplianceSnapshot` đã được Company duyệt
    (xem resolver.py), không bao giờ lấy từ context này.
    """

    model_config = ConfigDict(frozen=True)

    categories: frozenset[str]
    subject_reference: str | None = None
    source_ref: str
    source_hash: str

    @field_validator("categories")
    @classmethod
    def _reject_empty_categories(cls, value: frozenset[str]) -> frozenset[str]:
        if not value:
            raise ValueError("categories must not be empty — an egress claim needs at least one data category")
        return value

    @model_validator(mode="after")
    def _require_subject_reference_for_personal_categories(self) -> DirectMessageDataAccess:
        if (self.categories & _PERSONAL_CATEGORIES) and not self.subject_reference:
            raise ValueError(
                "subject_reference is required when categories include "
                "PERSONAL or SENSITIVE_PERSONAL"
            )
        return self

    @classmethod
    def from_message(
        cls,
        *,
        message_id: str,
        content: str,
        categories: frozenset[str],
        subject_reference: str | None,
    ) -> DirectMessageDataAccess:
        """Dựng context từ 1 tin nhắn hội thoại thật. `source_hash` băm đúng
        nội dung server nhận được (không phải nội dung đã redact) — để audit
        sau này chứng minh được claim khớp với dữ liệu gốc gửi đi."""
        return cls(
            categories=categories,
            subject_reference=subject_reference,
            source_ref=f"conversation_message:{message_id}",
            source_hash=hashlib.sha256(content.encode()).hexdigest(),
        )
