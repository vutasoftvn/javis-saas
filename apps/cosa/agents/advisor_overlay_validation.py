"""Kiểm tra advisor overlay không vượt quyền của profile được Project deploy.

Overlay chỉ cung cấp instruction/schema/skill cho phân tích advisory; quyền thực thi
vẫn thuộc profile được deploy (Company sở hữu). Vì vậy overlay không được:
- có capability ngoài `capability_refs` của profile;
- có autonomy cao hơn L1 (advisory);
- thêm model-input capability ngoài kênh câu hỏi deliberation mặc định hoặc kênh của profile;
- pin skill mà manifest không tồn tại, hoặc skill cần tool ngoài `capability_refs` của overlay.
"""

from __future__ import annotations

from typing import Any

from agent.contracts.spec import AgentSpec
from agent.governance.contracts import AutonomyLevel

from apps.cosa.agents.capability_readiness import get_skill_required_capabilities

__all__ = ["ADVISOR_DEFAULT_MODEL_INPUT_REF", "validate_advisor_overlay"]

# Kênh duy nhất runner advisor dùng: câu hỏi deliberation + evidence dạng text.
ADVISOR_DEFAULT_MODEL_INPUT_REF = "model.input.direct-user-message"


def validate_advisor_overlay(
    overlay: AgentSpec,
    profile: AgentSpec,
    skill_manifests: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """Trả về danh sách vi phạm (rỗng = hợp lệ). `skill_manifests` None = bỏ qua
    kiểm tra manifest (caller không có manifest); dict = kiểm tra bắt buộc."""
    violations: list[str] = []

    if overlay.autonomy_level != AutonomyLevel.L1_PROPOSE:
        violations.append(f"autonomy_exceeds_advisory:{overlay.autonomy_level}")

    extra = sorted(set(overlay.capability_refs) - set(profile.capability_refs))
    if extra:
        violations.append(f"capabilities_outside_profile:{','.join(extra)}")

    ref = overlay.model_input_capability_ref
    if ref is not None and ref not in (
        ADVISOR_DEFAULT_MODEL_INPUT_REF,
        profile.model_input_capability_ref,
    ):
        violations.append(f"model_input_added:{ref}")

    if skill_manifests is not None:
        for pinned in overlay.pinned_skills:
            manifest = skill_manifests.get(pinned.skill_id)
            if manifest is None:
                violations.append(f"skill_manifest_missing:{pinned.skill_id}")
                continue
            outside = sorted(
                get_skill_required_capabilities(manifest) - set(overlay.capability_refs)
            )
            if outside:
                violations.append(
                    f"skill_tools_outside_overlay:{pinned.skill_id}:{','.join(outside)}"
                )

    return violations
