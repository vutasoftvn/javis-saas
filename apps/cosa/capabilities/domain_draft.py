"""Capability soạn NHÁP theo domain cho các agent chỉ-đọc (review 2026-09-27, G-5).

Trước đây 10 agent chuyên môn (sales, product, legal, people…) chỉ có capability
đọc, nên task WGA giao cho chúng hoặc bị chặn `capability_not_in_profile`, hoặc
agent chỉ trả lời văn bản tự do. Mỗi capability ở đây cho agent tạo một bản nháp
CÓ CẤU TRÚC (tiêu đề, nội dung, căn cứ, giả định, bước tiếp theo) để founder duyệt.

Bất biến an toàn (quy tắc 1 và 8):
- KHÔNG side-effect: không gọi company, không gửi tin, không ghi business DB.
  Kết quả là output của run (hiện trong timeline/evidence task), trạng thái
  `pending_founder_review`;
- mọi cờ kiểu `send`/`publish`/`apply` bị từ chối thẳng;
- id kết thúc `.draft` + risk LOW để company autonomy-classifier xếp AUTO được,
  nhưng biến nháp thành hành động thật vẫn phải qua capability ghi riêng có approval.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

__all__ = [
    "DOMAIN_DRAFTS",
    "DOMAIN_DRAFT_SPECS",
    "DomainDraft",
    "create_domain_draft_handler",
    "draft_capability_for_profile",
]

_MAX_TITLE = 200
_MAX_BODY = 8000
_MAX_ITEMS = 20
_FORBIDDEN_FLAGS = ("send", "send_now", "deliver", "auto_send", "publish", "apply", "execute")


@dataclass(frozen=True)
class DomainDraft:
    capability_id: str
    profile_key: str
    artifact_kind: str
    description: str


# Mỗi profile đúng 1 capability nháp. Tiền tố id phải route về đúng profile ở
# company `routeOwnerProfile` (autonomy-classifier.ts) — test chéo trong
# tests/apps/cosa/wga/test_owner_agent_profiles.py chặn lệch.
DOMAIN_DRAFTS: tuple[DomainDraft, ...] = (
    DomainDraft(
        "project.crm.lead.draft",
        "sales",
        "sales_lead_plan_draft",
        "Soạn nháp kế hoạch tiếp cận lead/cơ hội bán hàng (nhu cầu, bước tiếp theo, "
        "thông điệp đề xuất). KHÔNG ghi CRM, KHÔNG gửi tin.",
    ),
    DomainDraft(
        "strategy.plan.draft",
        "strategy",
        "strategy_plan_draft",
        "Soạn nháp kế hoạch/đề xuất chiến lược (mục tiêu, lựa chọn, đánh đổi, chỉ số). "
        "KHÔNG tạo initiative hay đổi mục tiêu.",
    ),
    DomainDraft(
        "research.intelligence.brief.draft",
        "research_intelligence",
        "research_brief_draft",
        "Soạn nháp bản tóm tắt nghiên cứu thị trường/đối thủ kèm nguồn. "
        "KHÔNG ghi evidence vào hệ thống.",
    ),
    DomainDraft(
        "engineering.plan.draft",
        "coding",
        "engineering_plan_draft",
        "Soạn nháp kế hoạch kỹ thuật (phạm vi, kiến trúc, rủi ro, ước lượng). "
        "KHÔNG chạy lệnh, KHÔNG deploy, KHÔNG sửa code.",
    ),
    DomainDraft(
        "product.decision.draft",
        "product",
        "product_decision_draft",
        "Soạn nháp đề xuất quyết định sản phẩm/PRD (vấn đề, chỉ số thành công, "
        "phương án, đánh đổi). KHÔNG tạo hay xác nhận Product Decision Dossier.",
    ),
    DomainDraft(
        "people.plan.draft",
        "people",
        "people_plan_draft",
        "Soạn nháp kế hoạch nhân sự (vai trò cần tuyển, năng lực, rủi ro, rubric). "
        "KHÔNG xếp hạng ứng viên, KHÔNG đổi WorkforceMember, KHÔNG liên hệ ai.",
    ),
    DomainDraft(
        "security.remediation.draft",
        "security",
        "security_remediation_draft",
        "Soạn nháp kế hoạch khắc phục rủi ro bảo mật/control gap. "
        "KHÔNG scan, KHÔNG rotate secret, KHÔNG patch/deploy.",
    ),
    DomainDraft(
        "legal.issue.draft",
        "legal",
        "legal_issue_draft",
        "Soạn nháp ghi chú vấn đề pháp lý cần làm rõ và câu hỏi cho luật sư. "
        "Không phải tư vấn pháp lý; KHÔNG ký/duyệt/nộp hồ sơ.",
    ),
    DomainDraft(
        "data.quality.draft",
        "data",
        "data_quality_draft",
        "Soạn nháp kế hoạch cải thiện chất lượng/phân loại dữ liệu. "
        "KHÔNG đổi classification/ACL/retention, KHÔNG xoá dữ liệu.",
    ),
)

_BY_ID: dict[str, DomainDraft] = {d.capability_id: d for d in DOMAIN_DRAFTS}
_BY_PROFILE: dict[str, DomainDraft] = {d.profile_key: d for d in DOMAIN_DRAFTS}

_STR_LIST = {"type": "array", "items": {"type": "string"}, "maxItems": _MAX_ITEMS}


def _spec(d: DomainDraft) -> CapabilitySpec:
    return CapabilitySpec(
        id=d.capability_id,
        description=d.description + " Bản nháp chờ founder duyệt, không có side-effect.",
        risk=CapabilityRisk.LOW,
        approval_policy=ApprovalPolicy.NEVER,
        idempotency_semantics="payload_deterministic",
        metadata={"action_class": "A", "artifact_kind": d.artifact_kind},
        input_schema={
            "type": "object",
            "required": ["title", "body"],
            "properties": {
                "title": {"type": "string", "minLength": 3, "maxLength": _MAX_TITLE},
                "body": {"type": "string", "minLength": 10, "maxLength": _MAX_BODY},
                "evidence_refs": {**_STR_LIST, "description": "Căn cứ đã đọc được"},
                "assumptions": {**_STR_LIST, "description": "Giả định chưa kiểm chứng"},
                "next_steps": {**_STR_LIST, "description": "Bước founder nên làm tiếp"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "artifact_kind": {"type": "string"},
                "status": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "evidence_refs": {"type": "array"},
                "assumptions": {"type": "array"},
                "next_steps": {"type": "array"},
                "delivery": {"type": "string"},
            },
        },
    )


DOMAIN_DRAFT_SPECS: tuple[CapabilitySpec, ...] = tuple(_spec(d) for d in DOMAIN_DRAFTS)


def draft_capability_for_profile(profile_key: str) -> str | None:
    d = _BY_PROFILE.get(profile_key)
    return d.capability_id if d else None


def _str_list(value: Any, field: str, cap_id: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{cap_id}: {field} must be a list of strings")
    out = [str(v).strip() for v in value if str(v).strip()]
    return out[:_MAX_ITEMS]


def create_domain_draft_handler(
    capability_id: str,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    d = _BY_ID[capability_id]

    async def handle(args: dict[str, Any], context: Any = None) -> dict[str, Any]:
        if any(args.get(flag) is True for flag in _FORBIDDEN_FLAGS):
            raise ValueError(f"{capability_id} only creates drafts; external actions are refused")
        title = str(args.get("title") or "").strip()
        body = str(args.get("body") or "").strip()
        if len(title) < 3:
            raise ValueError(f"{capability_id}: title is required")
        if len(body) < 10:
            raise ValueError(f"{capability_id}: body is required")
        return {
            "artifact_kind": d.artifact_kind,
            "status": "pending_founder_review",
            "title": title[:_MAX_TITLE],
            "body": body[:_MAX_BODY],
            "evidence_refs": _str_list(args.get("evidence_refs"), "evidence_refs", capability_id),
            "assumptions": _str_list(args.get("assumptions"), "assumptions", capability_id),
            "next_steps": _str_list(args.get("next_steps"), "next_steps", capability_id),
            "delivery": "none",
        }

    return handle
