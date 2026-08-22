"""Centralized Prompt Registry for COSA AI Operating System (Spec §30, §56–§60, §P5).

Provides versioned, domain-scoped prompt templates with checksum integrity,
variable rendering, candidate evaluation lifecycle, and strict enforcement of the
invariant: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re
from typing import Dict, Any, Optional, List
from core.protected_resources import service as protected_resource_service


@dataclass(frozen=True)
class PromptTemplate:
    domain: str
    name: str
    version: str
    content: str
    sha256: str
    variables: list[str]
    is_active: bool = True
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None


@dataclass
class PromptCandidate:
    candidate_id: str
    domain: str
    name: str
    version: str
    content: str
    sha256: str
    variables: list[str]
    base_version: str
    proposed_by_agent: Optional[str] = None
    status: str = "candidate"  # candidate, evaluated, promoted, rejected
    eval_score: float = 0.0
    eval_metrics: Dict[str, Any] = field(default_factory=dict)
    eval_notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class PromptRegistry:
    """Manages prompt template loading, caching, versioning, rendering, and candidate governance."""

    _instance: Optional["PromptRegistry"] = None
    _templates: Dict[str, PromptTemplate] = {}
    _candidates: Dict[str, PromptCandidate] = {}

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
                var_names = sorted(list(set(re.findall(r"\$\{([a-zA-Z0-9_]+)\}", content))))
                version = f"{domain}.{name}.{sha256[:8]}"

                template = PromptTemplate(
                    domain=domain,
                    name=name,
                    version=version,
                    content=content,
                    sha256=sha256,
                    variables=var_names,
                    is_active=True,
                )
                key = f"{domain}/{name}"
                self._templates[key] = template
            except Exception:
                continue

    def get(self, domain: str, name: str) -> Optional[PromptTemplate]:
        """Retrieve a loaded active prompt template by domain and name."""
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

    def render_effective(
        self,
        db,
        workspace_id: int,
        domain: str,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render a template, preferring the workspace's DB override over the bundled file default."""
        template = self.get(domain, name)
        if not template:
            raise KeyError(f"Prompt template '{domain}/{name}' not found in registry")

        effective = protected_resource_service.get_effective(
            db=db,
            workspace_id=workspace_id,
            resource_type="domain_prompt",
            resource_key=f"{domain}/{name}",
            default_content={"content": template.content},
        )
        rendered = effective.get("content", template.content)
        if variables:
            for k, v in variables.items():
                rendered = rendered.replace(f"${{{k}}}", str(v))
        return rendered

    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available active templates and their metadata."""
        return {
            key: {
                "domain": t.domain,
                "name": t.name,
                "version": t.version,
                "sha256": t.sha256,
                "variables": t.variables,
                "is_active": t.is_active,
                "approved_by": t.approved_by,
                "approved_at": t.approved_at.isoformat() if t.approved_at else None,
            }
            for key, t in self._templates.items()
        }

    # ==========================================
    # Prompt Lifecycle & Candidate Governance
    # ==========================================

    def register_candidate(
        self,
        domain: str,
        name: str,
        content: str,
        base_version: str,
        proposed_by_agent: Optional[str] = None,
    ) -> PromptCandidate:
        """Register a newly generated or optimized candidate prompt."""
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        var_names = sorted(list(set(re.findall(r"\$\{([a-zA-Z0-9_]+)\}", content))))
        candidate_version = f"{domain}.{name}.cand_{sha256[:8]}"
        candidate_id = f"cand_{domain}_{name}_{sha256[:8]}"

        candidate = PromptCandidate(
            candidate_id=candidate_id,
            domain=domain,
            name=name,
            version=candidate_version,
            content=content,
            sha256=sha256,
            variables=var_names,
            base_version=base_version,
            proposed_by_agent=proposed_by_agent,
            status="candidate",
            created_at=datetime.now(timezone.utc),
        )
        self._candidates[candidate_id] = candidate
        return candidate

    def record_candidate_eval(
        self,
        candidate_id: str,
        eval_score: float,
        eval_metrics: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> PromptCandidate:
        """Record evaluation benchmarks for a candidate prompt."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate '{candidate_id}' not found")

        candidate.eval_score = eval_score
        candidate.eval_metrics = eval_metrics or {}
        candidate.eval_notes = notes
        candidate.status = "evaluated"
        return candidate

    def promote_candidate(
        self,
        candidate_id: str,
        approved_by_user_id: Optional[int],
        write_to_disk: bool = False,
    ) -> PromptTemplate:
        """Promote an evaluated candidate prompt to active production status.
        
        INVARIANT ENFORCEMENT:
        NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
        Promotion MUST have an explicit human admin/founder user ID.
        """
        if approved_by_user_id is None:
            raise PermissionError(
                "Invariant Violation: NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS. "
                "Candidate promotion requires explicit human admin/founder approval."
            )

        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate '{candidate_id}' not found")

        now = datetime.now(timezone.utc)
        candidate.status = "promoted"
        candidate.reviewed_by_user_id = approved_by_user_id
        candidate.reviewed_at = now

        prod_version = f"{candidate.domain}.{candidate.name}.{candidate.sha256[:8]}"
        new_template = PromptTemplate(
            domain=candidate.domain,
            name=candidate.name,
            version=prod_version,
            content=candidate.content,
            sha256=candidate.sha256,
            variables=candidate.variables,
            is_active=True,
            approved_by=approved_by_user_id,
            approved_at=now,
        )

        key = f"{candidate.domain}/{candidate.name}"
        self._templates[key] = new_template

        if write_to_disk:
            target_path = self.base_dir / candidate.domain / f"{candidate.name}.md"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(candidate.content, encoding="utf-8")

        return new_template

    def reject_candidate(
        self,
        candidate_id: str,
        rejected_by_user_id: int,
        reason: str,
    ) -> PromptCandidate:
        """Reject a candidate prompt with feedback."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate '{candidate_id}' not found")

        candidate.status = "rejected"
        candidate.reviewed_by_user_id = rejected_by_user_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        candidate.rejection_reason = reason
        return candidate

    def get_candidate(self, candidate_id: str) -> Optional[PromptCandidate]:
        """Retrieve candidate prompt by candidate_id."""
        return self._candidates.get(candidate_id)

    def list_candidates(self, domain: Optional[str] = None) -> List[PromptCandidate]:
        """List all candidate prompts, optionally filtered by domain."""
        if domain:
            return [c for c in self._candidates.values() if c.domain == domain]
        return list(self._candidates.values())
