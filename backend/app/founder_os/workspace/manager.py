"""Company Workspace Manager for COSA OS.

Manages local filesystem workspace at ~/.cosa/companies/<company_id>/
Enforces the separation of System Defaults vs Company Overrides without data loss upon app updates.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

DEFAULT_IDENTITY_MD = """# Company Identity
- **Name**: COSA Enterprise
- **Tagline**: Autonomous Enterprise Operating System
- **Core Business**: AI-native operating platform for Founders & Enterprises.
- **Tone**: Professional, precise, visionary, execution-focused.
"""

DEFAULT_SOUL_MD = """# Assistant Soul & Operating Philosophy
- **Role**: Executive AI Copilot & Workforce Orchestrator
- **Core Principle 1**: VERIFY-BEFORE-CLAIM (No unverified claims of action completion)
- **Core Principle 2**: Stop on unexpected error -> Describe -> Wait (Do not guess-fix)
- **Core Principle 3**: Execution limits: strictly enforce safety policies and budget guards.
"""

DEFAULT_FOUNDER_PROFILE_MD = """# Founder Profile
- **Title**: Founder & CEO
- **Decision Style**: Data-driven, fast validation, autonomous delegation with safety checkpoints.
- **Communication Preference**: Bullet points, concise, executive summaries with action items.
"""

DEFAULT_POLICIES_BASE_MD = """# Base Operational Policies
1. External writes (send message, email, publish, payment) require explicit approval in Interactive Mode.
2. Read operations and internal drafts are automatically permitted.
3. Protected core configuration files cannot be modified by AI without founder approval.
"""


class CompanyWorkspaceManager:
    """Manages company workspace directories, defaults, and overrides."""

    def __init__(self, base_path: Optional[Path] = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            custom_root = os.environ.get("COSA_WORKSPACE_ROOT")
            if custom_root:
                self.base_path = Path(custom_root)
            else:
                self.base_path = Path.home() / ".cosa" / "companies"

    def get_company_dir(self, company_id: str | int) -> Path:
        return self.base_path / str(company_id)

    def init_company_workspace(self, company_id: str | int) -> Path:
        """Initializes full folder structure for a company workspace."""
        company_dir = self.get_company_dir(company_id)

        subdirs = [
            "company",
            "founder",
            "projects",
            "knowledge/legal",
            "knowledge/marketing",
            "knowledge/finance",
            "knowledge/product",
            "skills",
            "policies",
            "templates",
            "memory/people",
            "memory/projects",
            "memory/decisions",
            "learnings",
            "runtime",
        ]

        for s in subdirs:
            (company_dir / s).mkdir(parents=True, exist_ok=True)

        # Seed default markdown files if not already existing (preserve company overrides)
        self._write_default_if_missing(company_dir / "company" / "identity.md", DEFAULT_IDENTITY_MD)
        self._write_default_if_missing(company_dir / "company" / "soul.md", DEFAULT_SOUL_MD)
        self._write_default_if_missing(company_dir / "founder" / "profile.md", DEFAULT_FOUNDER_PROFILE_MD)
        self._write_default_if_missing(company_dir / "policies" / "base.md", DEFAULT_POLICIES_BASE_MD)
        self._write_default_if_missing(
            company_dir / "learnings" / "ERRORS.md",
            "# Operational Errors Log\n\n| Date | Error | Provider | Resolution |\n|---|---|---|---|\n"
        )
        self._write_default_if_missing(
            company_dir / "memory" / "MEMORY.md",
            "# Hierarchical Memory Index\n- Active Projects:\n- Key People:\n- Recent Decisions:\n"
        )

        logger.info(f"[CompanyWorkspaceManager] Initialized workspace at {company_dir}")
        return company_dir

    def _write_default_if_missing(self, file_path: Path, content: str) -> None:
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.strip() + "\n", encoding="utf-8")

    def read_file(self, company_id: str | int, relative_path: str) -> Optional[str]:
        target = self.get_company_dir(company_id) / relative_path
        if target.exists() and target.is_file():
            return target.read_text(encoding="utf-8")
        return None

    def write_file(self, company_id: str | int, relative_path: str, content: str) -> Path:
        target = self.get_company_dir(company_id) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def reset_file_to_default(self, company_id: str | int, relative_path: str) -> bool:
        """Resets a customized file back to system default."""
        target = self.get_company_dir(company_id) / relative_path
        defaults = {
            "company/identity.md": DEFAULT_IDENTITY_MD,
            "company/soul.md": DEFAULT_SOUL_MD,
            "founder/profile.md": DEFAULT_FOUNDER_PROFILE_MD,
            "policies/base.md": DEFAULT_POLICIES_BASE_MD,
        }
        if relative_path in defaults:
            self.write_file(company_id, relative_path, defaults[relative_path])
            return True
        return False


workspace_manager = CompanyWorkspaceManager()
