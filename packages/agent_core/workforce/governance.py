"""Workforce governance — M7 §5: title KHÔNG cấp quyền.

- `execution_capabilities()` trả capability của AgentSpec, KHÔNG bao giờ suy từ
  `role_title`/persona.
- `assert_within_capability_boundary()` — capability_refs phải nằm trong ranh giới
  của functional key ⇒ không silent-widen.
- `capability_change_requires_new_spec()` — mọi thay đổi tập capability phải tạo
  spec/version/hash mới (không sửa spec đã publish tại chỗ).
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_core.contracts.spec import AgentSpec
from agent_core.workforce.catalog import FUNCTIONAL_AGENT_CATALOG

__all__ = [
    "CapabilityBoundaryError",
    "WorkforceAssignment",
    "assert_within_capability_boundary",
    "capability_change_requires_new_spec",
    "execution_capabilities",
]


class CapabilityBoundaryError(Exception):
    """capability_refs vượt ranh giới cho phép của functional key."""


@dataclass(frozen=True)
class WorkforceAssignment:
    """Overlay ở workspace level — CHỈ presentation/organization metadata."""

    workspace_id: str
    member_id: str
    functional_key: str
    agent_spec_id: str
    agent_spec_version: str
    definition_hash: str
    role_title: str = ""  # "CFO", "Finance Copilot" — KHÔNG cấp quyền
    persona: str = ""
    department: str = ""
    manager_member_id: str | None = None


def assert_within_capability_boundary(
    functional_key: str, capability_refs: list[str] | tuple[str, ...]
) -> None:
    entry = FUNCTIONAL_AGENT_CATALOG.get(functional_key)
    if entry is None:
        raise CapabilityBoundaryError(f"functional_key '{functional_key}' không trong catalog")
    allowed = entry.allowed_capability_prefixes
    for ref in capability_refs:
        if not any(ref == p or ref.startswith(p) for p in allowed):
            raise CapabilityBoundaryError(
                f"capability '{ref}' ngoài ranh giới của '{functional_key}' "
                f"(cho phép: {list(allowed)})"
            )


def execution_capabilities(assignment: WorkforceAssignment, spec: AgentSpec) -> list[str]:
    """Capability THỰC THI = của AgentSpec. `role_title`/persona của assignment
    KHÔNG được cộng thêm bất cứ capability nào."""
    if spec.id != assignment.agent_spec_id or spec.version != assignment.agent_spec_version:
        raise CapabilityBoundaryError("assignment trỏ tới agent_spec khác với spec được truyền vào")
    return list(spec.capability_refs)


def capability_change_requires_new_spec(
    current_spec: AgentSpec, new_capability_refs: list[str] | tuple[str, ...]
) -> bool:
    """True khi tập capability đổi ⇒ PHẢI publish spec/version/hash mới (không
    silent-widen bằng cách sửa role hay sửa spec đã publish)."""
    return set(current_spec.capability_refs) != set(new_capability_refs)
