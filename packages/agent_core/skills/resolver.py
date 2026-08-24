from __future__ import annotations

from typing import Optional

from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.identity import PinnedSkillRef
from agent_core.registry.repository import SpecRegistryRepository
from agent_core.skills.contracts import SkillSpec

__all__ = ["SkillResolver"]


class SkillResolver:
    """Resolve `AgentSpec.pinned_skills` thành `SkillSpec` đầy đủ, verify
    `definition_hash` khớp tuyệt đối — invariant chống floating runtime reference
    mà ADR-SKILL-IDENTITY lo ngại (§4, kích hoạt 2026-08-24). Không bao giờ tự ý
    dùng version/hash khác version đã pin, kể cả khi có version mới hơn."""

    def __init__(self, repository: SpecRegistryRepository) -> None:
        self._repo = repository

    async def resolve(self, pinned_skills: list[PinnedSkillRef]) -> list[SkillSpec]:
        resolved: list[SkillSpec] = []
        for ref in pinned_skills:
            record = await self._repo.get("skill", ref.skill_id, ref.version)
            if record is None:
                raise AgentRuntimeError(
                    RuntimeErrorCode.SKILL_RESOLUTION_ERROR,
                    f"Pinned skill '{ref.skill_id}@{ref.version}' không tồn tại trong registry — "
                    f"chưa publish hoặc đã bị retire.",
                    details={"skill_id": ref.skill_id, "version": ref.version},
                )
            if record.definition_hash != ref.definition_hash:
                raise AgentRuntimeError(
                    RuntimeErrorCode.SKILL_RESOLUTION_ERROR,
                    f"Pinned skill '{ref.skill_id}@{ref.version}' có definition_hash không khớp "
                    f"(pin={ref.definition_hash}, registry={record.definition_hash}) — "
                    f"nội dung skill đã đổi mà version không tăng, hoặc dữ liệu pin sai. "
                    f"Từ chối resolve để tránh floating reference.",
                    details={
                        "skill_id": ref.skill_id,
                        "version": ref.version,
                        "pinned_hash": ref.definition_hash,
                        "registry_hash": record.definition_hash,
                    },
                )
            resolved.append(SkillSpec(**record.content))
        return resolved
