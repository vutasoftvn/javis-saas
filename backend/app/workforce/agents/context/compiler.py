"""Progressive Context Compiler with Budget Guard (L0 - L5).

Prevents dumping entire workspace into prompt. Loads context progressively based on intent:
- L0: Session & Founder Preferences
- L1: Company / Founder Index
- L2: Project Context (only if intent is project-related)
- L3: Domain Context (Marketing, Sales, Finance, Dev)
- L4: Selected Skill Context (from skill YAML / Markdown)
- L5: Relevant Artifacts & Evidence Chunks
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import logging

from app.founder_os.workspace.manager import workspace_manager
from app.workforce.routing.deterministic import Intent

logger = logging.getLogger(__name__)


@dataclass
class ContextBudget:
    max_total_tokens: int = 16000
    l0_session_max: int = 2000
    l1_company_max: int = 1500
    l2_project_max: int = 3000
    l3_domain_max: int = 3000
    l4_skill_max: int = 2500
    l5_artifacts_max: int = 4000


@dataclass
class CompiledContext:
    intent: str
    layers: Dict[str, str] = field(default_factory=dict)
    total_estimated_tokens: int = 0
    trimmed: bool = False

    def to_system_prompt_addition(self) -> str:
        parts = []
        for layer_name in ["L0_Session", "L1_Company", "L2_Project", "L3_Domain", "L4_Skill", "L5_Artifacts"]:
            if layer_name in self.layers and self.layers[layer_name].strip():
                parts.append(f"=== [{layer_name}] ===\n{self.layers[layer_name].strip()}")
        return "\n\n".join(parts)


class ProgressiveContextCompiler:
    """Compiles prompt context progressively according to intent and token budget."""

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Rough estimation of token count (~4 chars per token)."""
        return max(1, len(text) // 4)

    @classmethod
    def truncate_to_budget(cls, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... [Context truncated to fit budget]"

    @classmethod
    def compile(
        cls,
        company_id: str | int,
        intent: Intent,
        session_history: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[str] = None,
        skill_contents: Optional[List[str]] = None,
        domain_payload: Optional[Dict[str, Any]] = None,
        budget: Optional[ContextBudget] = None,
    ) -> CompiledContext:
        budget = budget or ContextBudget()
        layers: Dict[str, str] = {}
        total_tokens = 0
        is_trimmed = False

        # L0 — Session
        l0_parts = []
        founder_pref = workspace_manager.read_file(company_id, "founder/profile.md") or ""
        if founder_pref:
            l0_parts.append(founder_pref)
        if session_history:
            recent = session_history[-4:]
            hist_str = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent)
            l0_parts.append("Recent Session:\n" + hist_str)
        l0_raw = "\n\n".join(l0_parts)
        layers["L0_Session"] = cls.truncate_to_budget(l0_raw, budget.l0_session_max)
        total_tokens += cls.estimate_tokens(layers["L0_Session"])

        # Early exit for pure social greetings: L0 is enough!
        if intent == Intent.GENERAL_CHAT:
            return CompiledContext(intent=intent.value, layers=layers, total_estimated_tokens=total_tokens)

        # L1 — Company Index
        l1_identity = workspace_manager.read_file(company_id, "company/identity.md") or ""
        l1_soul = workspace_manager.read_file(company_id, "company/soul.md") or ""
        l1_raw = f"{l1_identity}\n\n{l1_soul}".strip()
        layers["L1_Company"] = cls.truncate_to_budget(l1_raw, budget.l1_company_max)
        total_tokens += cls.estimate_tokens(layers["L1_Company"])

        # L2 — Project Context (only if project-related or explicitly targeted)
        if (intent in (Intent.PROJECT_QUERY, Intent.TASK_MANAGEMENT) or project_id) and project_id:
            proj_spec = workspace_manager.read_file(company_id, f"projects/{project_id}/spec.md") or ""
            proj_decisions = workspace_manager.read_file(company_id, f"projects/{project_id}/decisions.md") or ""
            l2_raw = f"Project ID: {project_id}\n{proj_spec}\n{proj_decisions}".strip()
            layers["L2_Project"] = cls.truncate_to_budget(l2_raw, budget.l2_project_max)
            total_tokens += cls.estimate_tokens(layers["L2_Project"])

        # L3 — Domain Context
        if domain_payload:
            l3_raw = "\n".join(f"{k}: {v}" for k, v in domain_payload.items())
            layers["L3_Domain"] = cls.truncate_to_budget(l3_raw, budget.l3_domain_max)
            total_tokens += cls.estimate_tokens(layers["L3_Domain"])

        # L4 — Skill Context
        if skill_contents:
            l4_raw = "\n\n---\n\n".join(skill_contents)
            layers["L4_Skill"] = cls.truncate_to_budget(l4_raw, budget.l4_skill_max)
            total_tokens += cls.estimate_tokens(layers["L4_Skill"])

        if total_tokens > budget.max_total_tokens:
            is_trimmed = True

        return CompiledContext(
            intent=intent.value,
            layers=layers,
            total_estimated_tokens=total_tokens,
            trimmed=is_trimmed,
        )
