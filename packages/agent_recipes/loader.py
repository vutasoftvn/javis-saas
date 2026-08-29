from __future__ import annotations

from pathlib import Path

import yaml
from agent.contracts.identity import PinnedSkillRef
from pydantic import BaseModel, Field

__all__ = [
    "RecipeSkillRequirement",
    "RecipeSpec",
    "RecipeWorkflowStep",
    "load_all_recipes",
    "load_recipe",
]


class RecipeSkillRequirement(BaseModel):
    """Yêu cầu skill trong Recipe bắt buộc phải pin definition_hash bất biến."""

    ref: PinnedSkillRef
    reason: str | None = None


class RecipeWorkflowStep(BaseModel):
    id: str
    description: str = ""
    deterministic: bool = False


class RecipeSpec(BaseModel):
    """Đặc tả Recipe (multi-step workflow pattern) của Agent Platform."""

    id: str
    name: str
    domain: str
    version: str = "1.0.0"
    description: str = ""
    pattern: str = ""
    steps: list[RecipeWorkflowStep] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    required_skills: list[RecipeSkillRequirement] = Field(default_factory=list)
    artifact_kind: str = "report"
    format: str = "markdown"
    side_effect_class: str = "read-only"
    approval_required: bool = False


def load_recipe(file_path: Path | str) -> RecipeSpec:
    """Nạp và kiểm tra tính hợp lệ của 1 file recipe.yaml.
    
    Quy tắc an toàn:
    - BẮT BUỘC dùng PinnedSkillRef ({skill_id, version, definition_hash}).
    - Nghiêm cấm floating ref dạng string path (`skillpacks/...`).
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Recipe file không tồn tại: {path}")

    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    metadata = content.get("metadata", {})
    workflow = content.get("workflow", {})
    requires = content.get("requires", {})
    outputs = content.get("outputs", {})
    governance = content.get("governance", {})

    # Parse workflow steps
    steps: list[RecipeWorkflowStep] = []
    for s in workflow.get("steps", []):
        steps.append(RecipeWorkflowStep(
            id=s.get("id", ""),
            description=s.get("description", ""),
            deterministic=bool(s.get("deterministic", False)),
        ))

    # Parse required skills with strict hash pinning check
    parsed_skills: list[RecipeSkillRequirement] = []
    for sk in requires.get("skills", []):
        ref_raw = sk.get("ref")
        if isinstance(ref_raw, str):
            raise ValueError(
                f"Floating skill reference '{ref_raw}' is prohibited in recipe '{metadata.get('id')}'. "
                f"Must use PinnedSkillRef with explicit skill_id, version, and definition_hash."
            )
        if not isinstance(ref_raw, dict):
            raise ValueError(
                f"Invalid skill ref in recipe '{metadata.get('id')}': expected dict with skill_id, version, definition_hash"
            )

        skill_id = ref_raw.get("skill_id")
        version = ref_raw.get("version")
        definition_hash = ref_raw.get("definition_hash")

        if not skill_id or not version or not definition_hash:
            raise ValueError(
                f"Incomplete PinnedSkillRef in recipe '{metadata.get('id')}': "
                f"skill_id={skill_id}, version={version}, definition_hash={definition_hash}"
            )

        pinned = PinnedSkillRef(
            skill_id=str(skill_id),
            version=str(version),
            definition_hash=str(definition_hash),
        )
        parsed_skills.append(RecipeSkillRequirement(ref=pinned, reason=sk.get("reason")))

    return RecipeSpec(
        id=metadata.get("id", path.stem),
        name=metadata.get("name", ""),
        domain=metadata.get("domain", "general"),
        version=metadata.get("version", "1.0.0"),
        description=metadata.get("description", "").strip(),
        pattern=workflow.get("pattern", ""),
        steps=steps,
        required_capabilities=requires.get("capabilities", []),
        required_skills=parsed_skills,
        artifact_kind=outputs.get("artifact_kind", "report"),
        format=outputs.get("format", "markdown"),
        side_effect_class=governance.get("side_effect_class", "read-only"),
        approval_required=bool(governance.get("approval_required", False)),
    )


def load_all_recipes(root_dir: Path | str) -> list[RecipeSpec]:
    """Quét và nạp toàn bộ recipe.yaml trong cây thư mục."""
    root = Path(root_dir)
    recipes: list[RecipeSpec] = []
    for p in root.rglob("recipe.yaml"):
        recipes.append(load_recipe(p))
    return recipes
