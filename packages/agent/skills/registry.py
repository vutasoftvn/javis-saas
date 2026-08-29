"""Skill Registry with Immutable Versioning & Progressive Disclosure."""

from __future__ import annotations

from agent.skills.contracts import SkillIndexEntry, SkillSpec, SkillStatus

__all__ = ["SkillRegistry"]


class SkillRegistry:
    """Registry quản lý SkillSpec bất biến, chỉ cho phép publish version mới, cấm mutate version cũ."""

    def __init__(self) -> None:
        # Key: (skill_id, version) -> SkillSpec
        self._skills: dict[tuple[str, str], SkillSpec] = {}

    def publish(self, spec: SkillSpec) -> str:
        """Publish một version skill mới. Nếu version đã tồn tại -> Báo lỗi bất biến."""
        key = (spec.id, spec.version)
        if key in self._skills:
            raise ValueError(
                f"Skill '{spec.id}' version '{spec.version}' already published and is immutable."
            )

        spec_hash = spec.compute_hash()
        spec.definition_hash = spec_hash
        spec.status = SkillStatus.PUBLISHED
        self._skills[key] = spec
        return spec_hash

    def get_index(self) -> list[SkillIndexEntry]:
        """HL-04: L0 Progressive disclosure: Chỉ trả về danh mục tóm tắt."""
        return [spec.to_index_entry() for spec in self._skills.values()]

    def get_version(self, skill_id: str, version: str) -> SkillSpec | None:
        """HL-04 / HL-05: L1 Progressive disclosure: Nạp đầy đủ chỉ dẫn của đúng version cụ thể."""
        return self._skills.get((skill_id, version))
