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
    raw_app = manifest_data.get("applicability") or {}
    raw_stages = raw_app.get("project_stages") or ["P0_DISCOVERY"]
    project_stages = []
    for s in raw_stages:
        try:
            project_stages.append(ProjectLifecycleStage(s))
        except ValueError:
            project_stages.append(ProjectLifecycleStage.P0_DISCOVERY)

    applicability = LifecycleApplicability(
        project_stages=project_stages or [ProjectLifecycleStage.P0_DISCOVERY],
        gates=raw_app.get("gates", []),
        required_context=raw_app.get("required_context", []),
        outputs=raw_app.get("outputs", []),
    )

    # Autonomy
    raw_autonomy = manifest_data.get("autonomy") or {}
    autonomy = AutonomyPolicy(
        ceiling=raw_autonomy.get("ceiling", "L0_OBSERVE"),
        side_effect_class=raw_autonomy.get("side_effect_class", "R"),
    )

    # Evidence requirement
    raw_evidence = manifest_data.get("evidence") or {}
    evidence_req = EvidenceRequirement(
        min_source_refs=raw_evidence.get("min_source_refs", 0),
        freshness_days=raw_evidence.get("freshness_days"),
        self_validation_forbidden=raw_evidence.get("self_validation_forbidden", True),
    )

    # Quality spec
    raw_quality = manifest_data.get("quality")
    quality = None
    if raw_quality and isinstance(raw_quality, dict) and raw_quality.get("eval_suite"):
        quality = SkillQualitySpec(
            eval_suite=raw_quality["eval_suite"],
            required_negative_cases=raw_quality.get(
                "required_negative_cases", ["default-negative"]
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
