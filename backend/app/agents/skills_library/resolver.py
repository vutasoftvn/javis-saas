"""Domain Knowledge Skill Resolver for COSA Agents."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import yaml


@dataclass(frozen=True)
class SkillManifest:
    name: str
    domain: str
    description: str
    required_context: list[str]
    tool_permissions: list[str]
    instructions: str
    filepath: str


class SkillResolver:
    """Discovers and parses domain knowledge SKILL.md manifests."""

    _LIBRARY_DIR = Path(__file__).parent

    @classmethod
    def _parse_skill_file(cls, path: Path) -> Optional[SkillManifest]:
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter_str = parts[1].strip()
        body = parts[2].strip()

        try:
            meta = yaml.safe_load(frontmatter_str) or {}
            return SkillManifest(
                name=meta.get("name", path.parent.name),
                domain=meta.get("domain", path.parent.name),
                description=meta.get("description", ""),
                required_context=meta.get("required_context", []),
                tool_permissions=meta.get("tool_permissions", []),
                instructions=body,
                filepath=str(path.resolve()),
            )
        except Exception:
            return None

    @classmethod
    def list_available(cls) -> list[SkillManifest]:
        skills = []
        for skill_md in cls._LIBRARY_DIR.rglob("SKILL.md"):
            manifest = cls._parse_skill_file(skill_md)
            if manifest:
                skills.append(manifest)
        return skills

    @classmethod
    def resolve(cls, job_type: str, domain: Optional[str] = None) -> Optional[SkillManifest]:
        for skill in cls.list_available():
            if skill.name == job_type or (domain and skill.domain == domain):
                return skill
        return None
