from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent.knowledge.snapshot_repository import KnowledgeSnapshotRepository

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.knowledge_read")

__all__ = [
    "KNOWLEDGE_PROFILE_READ_SPEC",
    "create_knowledge_profile_read_handler",
]

KNOWLEDGE_PROFILE_READ_SPEC = CapabilitySpec(
    id="knowledge.profile.read",
    description="Đọc profile/summary tri thức doanh nghiệp và đối thủ cạnh tranh với kiểm soát sensitivity và provenance.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "properties": {
            "profile_type": {
                "type": "string",
                "description": "Loại profile (competitor, product, market_summary)",
            },
            "profile_id": {
                "type": "string",
                "description": "ID định danh của profile",
            },
            "version": {
                "type": "string",
                "default": "1.0.0",
                "description": "Phiên bản snapshot của profile",
            },
            "include_untrusted": {
                "type": "boolean",
                "default": False,
                "description": "Cho phép lấy các insight chưa được verify",
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string"},
            "profile_id": {"type": "string"},
            "profile_type": {"type": "string"},
            "status": {"type": "string"},
            "sections": {"type": "array"},
            "sensitivity": {"type": "string"},
            "untrusted": {"type": "boolean"},
            "missing_sources": {"type": "array"},
        },
    },
)


def create_knowledge_profile_read_handler(
    snapshot_repo: KnowledgeSnapshotRepository | None = None,
    client: CompanyServiceClient | None = None,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo handler đọc knowledge profile từ KnowledgeSnapshotRepository thực tế đã inject,
    trả sections kèm sourceId/version/publishedAt/freshUntil/trust và kiểm tra provenance chặt chẽ.
    """

    async def handle_knowledge_profile_read(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id: str | None = None
        if isinstance(ctx, dict):
            workspace_id = ctx.get("workspace_id")
        elif hasattr(ctx, "workspace_id"):
            workspace_id = ctx.workspace_id

        if not workspace_id and "workspace_id" in args:
            workspace_id = str(args["workspace_id"])

        if not workspace_id:
            raise ValueError("Không thể thực hiện knowledge.profile.read: thiếu workspace_id")

        profile_type = str(args.get("profile_type", "competitor"))
        profile_id = str(args.get("profile_id", "default"))
        version = str(args.get("version", "1.0.0"))
        include_untrusted = bool(args.get("include_untrusted", False))

        if snapshot_repo is None:
            logger.warning("KnowledgeSnapshotRepository chưa được inject cho knowledge.profile.read")
            return {
                "workspace_id": workspace_id,
                "profile_id": profile_id,
                "profile_type": profile_type,
                "status": "UNAVAILABLE",
                "message": "Knowledge repository unavailable",
                "missing_sources": [profile_id],
                "sections": [],
            }

        # 1. Tìm snapshot theo ID hoặc composite ID
        snapshot = await snapshot_repo.get(profile_id, version)
        if snapshot is None:
            composite_id = f"knowledge.profile.{profile_type}.{profile_id}"
            snapshot = await snapshot_repo.get(composite_id, version)

        # 2. Không tìm thấy snapshot -> UNAVAILABLE
        if snapshot is None:
            return {
                "workspace_id": workspace_id,
                "profile_id": profile_id,
                "profile_type": profile_type,
                "status": "UNAVAILABLE",
                "message": f"Knowledge profile '{profile_id}' not found",
                "missing_sources": [profile_id],
                "sections": [],
            }

        # 3. Cross-workspace check: phải kiểm workspace trên nguồn bên dưới
        if snapshot.workspace_id != workspace_id:
            logger.warning(
                "Cross-workspace knowledge access attempt: request ws=%s, snapshot ws=%s",
                workspace_id,
                snapshot.workspace_id,
            )
            return {
                "workspace_id": workspace_id,
                "profile_id": profile_id,
                "profile_type": profile_type,
                "status": "UNAVAILABLE",
                "message": "Cross-workspace knowledge access rejected",
                "missing_sources": [profile_id],
                "sections": [],
            }

        # 4. Published check: kiểm tra trạng thái publish của nguồn bên dưới
        metadata = snapshot.metadata or {}
        if metadata.get("status") == "unpublished" or metadata.get("published") is False:
            return {
                "workspace_id": workspace_id,
                "profile_id": profile_id,
                "profile_type": profile_type,
                "status": "UNAVAILABLE",
                "message": "Knowledge profile is not published",
                "missing_sources": [profile_id],
                "sections": [],
            }

        # 5. Expiration check
        if metadata.get("status") == "expired" or metadata.get("expired") is True:
            return {
                "workspace_id": workspace_id,
                "profile_id": profile_id,
                "profile_type": profile_type,
                "status": "UNAVAILABLE",
                "message": "Knowledge profile has expired",
                "missing_sources": [profile_id],
                "sections": [],
            }

        # 6. Parse sections từ source_refs
        # Invariant: không đổi untrusted=false vì include_untrusted=true
        sections: list[dict[str, Any]] = []
        for ref in snapshot.source_refs:
            s_id = str(ref.get("source_id") or ref.get("sourceId") or "")
            s_ver = str(ref.get("version", "1.0.0"))
            s_pub = ref.get("published_at") or ref.get("publishedAt")
            s_fresh = ref.get("fresh_until") or ref.get("freshUntil")
            s_trust = str(ref.get("trust", "T0"))
            is_untrusted = bool(ref.get("untrusted", False)) or s_trust in ("untrusted", "T_UNTRUSTED")

            # Nếu untrusted và caller KHÔNG cho phép include_untrusted -> bỏ qua
            if is_untrusted and not include_untrusted:
                continue

            sections.append({
                "sourceId": s_id,
                "version": s_ver,
                "publishedAt": s_pub,
                "freshUntil": s_fresh,
                "trust": s_trust,
                "untrusted": is_untrusted,  # Giữ nguyên giá trị untrusted thật
                "content": ref.get("content", {}),
            })

        # 7. Nếu không có sections nào -> EMPTY
        if not sections:
            return {
                "workspace_id": workspace_id,
                "profile_id": profile_id,
                "profile_type": profile_type,
                "status": "EMPTY",
                "message": "No verified knowledge sources available",
                "missing_sources": [profile_id],
                "sections": [],
            }

        return {
            "workspace_id": workspace_id,
            "profile_id": profile_id,
            "profile_type": profile_type,
            "status": "AVAILABLE",
            "sensitivity": str(metadata.get("sensitivity", "internal")),
            "untrusted": any(s["untrusted"] for s in sections),
            "sections": sections,
            "missing_sources": [],
            "profile": metadata.get("profile", {}),
        }

    return handle_knowledge_profile_read
