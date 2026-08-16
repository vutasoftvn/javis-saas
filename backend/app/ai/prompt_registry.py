"""Centralized Prompt Registry for COSA AI Operating System (§b1, §P0.3).

Provides versioned, domain-scoped prompt templates with checksum integrity,
variable rendering, and execution trace metadata for ai_runs.
"""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class PromptTemplate:
    domain: str
    name: str
    version: str
    content: str
    sha256: str
    variables: list[str]


class PromptRegistry:
    """Manages prompt template loading, caching, versioning and rendering."""

    _instance: Optional["PromptRegistry"] = None
    _templates: Dict[str, PromptTemplate] = {}

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            # Default to backend/app/prompts
            base_dir = Path(__file__).parent.parent / "prompts"
        self.base_dir = base_dir
        self.reload()

    @classmethod
    def get_instance(cls) -> "PromptRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self) -> None:
        """Scan base_dir and reload all markdown prompt templates."""
        self._templates.clear()
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
            return

        for md_file in self.base_dir.glob("**/*.md"):
            rel_path = md_file.relative_to(self.base_dir)
            parts = rel_path.parts
            if len(parts) >= 2:
                domain = parts[0]
                name = parts[-1].replace(".md", "")
            else:
                domain = "general"
                name = parts[0].replace(".md", "")

            try:
                content = md_file.read_text(encoding="utf-8")
                sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
                var_names = list(set(re.findall(r"\$\{([a-zA-Z0-9_]+)\}", content)))
                version = f"{domain}.{name}.{sha256[:8]}"

                template = PromptTemplate(
                    domain=domain,
                    name=name,
                    version=version,
                    content=content,
                    sha256=sha256,
                    variables=var_names,
                )
                key = f"{domain}/{name}"
                self._templates[key] = template
            except Exception:
                continue

    def get(self, domain: str, name: str) -> Optional[PromptTemplate]:
        """Retrieve a loaded prompt template by domain and name."""
        key = f"{domain}/{name}"
        return self._templates.get(key)

    def render(self, domain: str, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Render a template with variables, raising KeyError if missing."""
        template = self.get(domain, name)
        if not template:
            raise KeyError(f"Prompt template '{domain}/{name}' not found in registry")

        rendered = template.content
        if variables:
            for k, v in variables.items():
                rendered = rendered.replace(f"${{{k}}}", str(v))
        return rendered

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available templates and their metadata."""
        return {
            key: {
                "domain": t.domain,
                "name": t.name,
                "version": t.version,
                "sha256": t.sha256,
                "variables": t.variables,
            }
            for key, t in self._templates.items()
        }
