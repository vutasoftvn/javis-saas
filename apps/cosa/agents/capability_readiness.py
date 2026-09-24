from __future__ import annotations

from typing import Any

from agent.contracts.spec import AgentSpec

__all__ = [
    "check_agent_spec_readiness",
    "check_capability_readiness",
    "check_permission_readiness",
    "get_skill_required_capabilities",
]


def check_capability_readiness(required: set[str], available: set[str]) -> list[str]:
    """Kiểm tra danh sách capability còn thiếu giữa tập required và available.
    Trả về danh sách đã được sắp xếp tăng dần.
    """
    return sorted(required - available)


def check_permission_readiness(required: set[str], granted: set[str]) -> list[str]:
    """Kiểm tra quyền hạn còn thiếu giữa required permissions và granted permissions.
    Tách biệt hoàn toàn với capability readiness (tools có sẵn vs quyền được cấp).
    """
    return sorted(required - granted)


def get_skill_required_capabilities(skill_manifest: dict[str, Any]) -> set[str]:
    """Trích xuất danh sách required tools/capabilities từ một skill manifest."""
    runtime = skill_manifest.get("runtime", {})
    tools = runtime.get("tools", [])
    if isinstance(tools, list):
        return {str(t) for t in tools if t}
    return set()


def check_agent_spec_readiness(
    spec: AgentSpec,
    available_capabilities: set[str],
    skill_manifests: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """Kiểm tra tính sẵn sàng của một AgentSpec trước khi activate:
    1. Toàn bộ capability_refs của agent spec phải có trong available_capabilities.
    2. Toàn bộ runtime.tools yêu cầu bởi các pinned_skills phải có trong available_capabilities
       VÀ có trong spec.capability_refs của agent.
    """
    needed: set[str] = set(spec.capability_refs)
    missing_from_spec: set[str] = set()

    if skill_manifests:
        for pinned in spec.pinned_skills:
            manifest = skill_manifests.get(pinned.skill_id)
            if manifest:
                skill_tools = get_skill_required_capabilities(manifest)
                needed.update(skill_tools)
                # Tool của skill phải nằm trong capability_refs của chính AgentSpec —
                # nếu không, skill sẽ dùng tool mà spec chưa được cấp quyền khai báo.
                outside = skill_tools - set(spec.capability_refs)
                missing_from_spec.update(outside)

    return sorted(
        set(check_capability_readiness(needed, available_capabilities)) | missing_from_spec
    )
