from __future__ import annotations

from pathlib import Path

import yaml
from agent.skills.contracts import (
    AutonomyPolicy,
    EvidenceRequirement,
    LifecycleApplicability,
    ProjectLifecycleStage,
    SkillQualitySpec,
    SkillSpec,
    SkillStatus,
)
from agent.skills.skillpack_contract import _extract_source_attribution_record

__all__ = ["parse_skillpack_spec"]


def _require_mapping(manifest: dict, section: str) -> dict:
    value = manifest.get(section)
    if not isinstance(value, dict):
        raise ValueError(f"Skillpack manifest requires {section} mapping")
    return value


def _require_non_empty_string_list(mapping: dict, field: str, *, section: str) -> list[str]:
    value = mapping.get(field)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"Skillpack manifest requires {section}.{field} non-empty string list")
    return value


def _extract_instructions_body(skillmd_text: str) -> str:
    """Tách phần thân markdown sau YAML frontmatter."""
    if not skillmd_text.startswith("---"):
        return skillmd_text.strip()
    parts = skillmd_text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return skillmd_text.strip()


def parse_skillpack_spec(pack_dir: Path) -> SkillSpec:
    """Đọc manifest.yaml + SKILL.md trong pack_dir và build ra SkillSpec với đầy đủ metadata governance."""
    manifest_path = pack_dir / "manifest.yaml"
    skillmd_path = pack_dir / "SKILL.md"

    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_data = yaml.safe_load(manifest_text) or {}
    skillmd_text = skillmd_path.read_text(encoding="utf-8")

    metadata = manifest_data.get("metadata", {})
    skill_id = metadata.get("id") or pack_dir.name
    version = str(metadata.get("version", "1.0.0"))
    name = metadata.get("name", skill_id)
    description = metadata.get("description", "")
    category = metadata.get("category") or pack_dir.parent.name or "general"

    # Applicability
    raw_app = _require_mapping(manifest_data, "applicability")
    raw_stages = _require_non_empty_string_list(raw_app, "project_stages", section="applicability")
    project_stages = []
    for s in raw_stages:
        try:
            project_stages.append(ProjectLifecycleStage(s))
        except ValueError as exc:
            raise ValueError(f"Invalid applicability.project_stages value: {s!r}") from exc

    applicability = LifecycleApplicability(
        project_stages=project_stages,
        gates=raw_app.get("gates", []),
        required_context=raw_app.get("required_context", []),
        outputs=raw_app.get("outputs", []),
    )

    # Autonomy
    raw_autonomy = _require_mapping(manifest_data, "autonomy")
    if not isinstance(raw_autonomy.get("ceiling"), str):
        raise ValueError("Skillpack manifest requires autonomy.ceiling")
    if not isinstance(raw_autonomy.get("side_effect_class"), str):
        raise ValueError("Skillpack manifest requires autonomy.side_effect_class")
    autonomy = AutonomyPolicy(
        ceiling=raw_autonomy["ceiling"],
        side_effect_class=raw_autonomy["side_effect_class"],
    )

    # Evidence requirement
    raw_evidence = _require_mapping(manifest_data, "evidence")
    min_source_refs = raw_evidence.get("min_source_refs")
    if not isinstance(min_source_refs, int) or isinstance(min_source_refs, bool):
        raise ValueError("Skillpack manifest requires evidence.min_source_refs integer")
    self_validation_forbidden = raw_evidence.get("self_validation_forbidden")
    if not isinstance(self_validation_forbidden, bool):
        raise ValueError("Skillpack manifest requires evidence.self_validation_forbidden boolean")
    evidence_req = EvidenceRequirement(
        min_source_refs=min_source_refs,
        freshness_days=raw_evidence.get("freshness_days"),
        self_validation_forbidden=self_validation_forbidden,
    )

    # Quality spec
    raw_quality = _require_mapping(manifest_data, "quality")
    eval_suite = raw_quality.get("eval_suite")
    if not isinstance(eval_suite, str) or not eval_suite.strip():
        raise ValueError("Skillpack manifest requires quality.eval_suite")
    quality = SkillQualitySpec(
        eval_suite=eval_suite,
        required_negative_cases=_require_non_empty_string_list(
            raw_quality, "required_negative_cases", section="quality"
        ),
    )

    # Capabilities từ manifest.runtime.tools đã lọc
    runtime_config = manifest_data.get("runtime", {})
    raw_tools = runtime_config.get("tools") or manifest_data.get("tools") or []
    required_capabilities = [tool for tool in raw_tools if isinstance(tool, str)]

    # References / Attribution
    source_config = manifest_data.get("source", {})
    upstream_record = _extract_source_attribution_record(skillmd_text) or {}

    references = {
        "source_path": source_config.get("path") or f"skillpacks/{pack_dir.name}",
        "origin": upstream_record.get("upstream") or source_config.get("origin") or "built-in",
        "upstream_commit": upstream_record.get("commit")
        or source_config.get("commit")
        or "adapted",
        "category": category,
    }

    instructions = _extract_instructions_body(skillmd_text)

    spec = SkillSpec(
        id=skill_id,
        version=version,
        name=name,
        description=description,
        instructions=instructions,
        applicability=applicability,
        autonomy=autonomy,
        evidence_requirement=evidence_req,
        quality=quality,
        required_capabilities=required_capabilities,
        references=references,
        status=SkillStatus.PUBLISHED,
        publisher="cosa_built_in",
    )
    spec.definition_hash = spec.compute_hash()
    return spec
