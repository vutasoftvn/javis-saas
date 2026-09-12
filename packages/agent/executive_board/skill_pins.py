from __future__ import annotations

from agent.contracts.identity import PinnedSkillRef
from agent.executive_board.models import ExecutiveBoardInputError
from agent.registry.repository import SpecRegistryRepository

__all__ = ["parse_skill_pin_ref", "resolve_role_pin_skills"]

_PREFIX = "skillpack:"


def parse_skill_pin_ref(ref: str) -> tuple[str, str]:
    """Chuyển 'skillpack:executive/cfo-advisor@1.0.0' -> ('executive.cfo-advisor', '1.0.0').

    Catalog role dùng dấu '/' cho path skillpack trên đĩa, nhưng registry publish
    skill dùng skill_id dạng dấu chấm lấy từ manifest.yaml metadata.id
    (apps/cosa/api/skillpack_mapper.py:58) — 2 quy ước khác nhau, cần convert.
    """
    if not ref.startswith(_PREFIX):
        raise ExecutiveBoardInputError(f"UNSUPPORTED_SKILL_PIN_FORMAT: {ref}")
    body = ref[len(_PREFIX):]
    path, sep, version = body.partition("@")
    if not sep or not path or not version:
        raise ExecutiveBoardInputError(f"UNSUPPORTED_SKILL_PIN_FORMAT: {ref}")
    return path.replace("/", "."), version


async def resolve_role_pin_skills(
    skill_pins: tuple[str, ...],
    spec_registry: SpecRegistryRepository,
) -> list[PinnedSkillRef]:
    """Resolve từng skill_pins string thành PinnedSkillRef có definition_hash thật
    (đọc từ registry, không tự đoán/không dùng 'bản mới nhất')."""
    refs: list[PinnedSkillRef] = []
    for raw in skill_pins:
        skill_id, version = parse_skill_pin_ref(raw)
        record = await spec_registry.get(spec_kind="skill", spec_id=skill_id, version=version)
        if record is None:
            raise ExecutiveBoardInputError(
                f"SKILL_PIN_NOT_PUBLISHED: '{skill_id}@{version}' not found in spec registry"
            )
        refs.append(
            PinnedSkillRef(skill_id=skill_id, version=version, definition_hash=record.definition_hash)
        )
    return refs
