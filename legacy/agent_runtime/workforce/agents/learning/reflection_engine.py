"""Reflection & Learning Engine (Nightly & Weekly Meditation Loop).

Implements the self-reflection and operational learning flow from MODOROClaw-Setup:
- Scans failed executions and logs to `learnings/ERRORS.md`
- Distills completed work products and decisions to `learnings/LEARNINGS.md`
- Synchronizes key strategic insights with Database Decision Records
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

from founder_os.workspace.manager import workspace_manager

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """Processes operational telemetry and generates immutable learnings."""

    @classmethod
    def record_error(
        cls,
        company_id: str | int,
        error_message: str,
        provider: str = "native",
        action: str = "general",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Appends a new error entry into learnings/ERRORS.md."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        line = f"| {now_str} | `{action}`: {error_message[:100]} | `{provider}` | Logged for review |\n"

        existing = workspace_manager.read_file(company_id, "learnings/ERRORS.md")
        if not existing:
            existing = "# Operational Errors Log\n\n| Date | Error | Provider | Resolution |\n|---|---|---|---|\n"

        updated = existing + line
        workspace_manager.write_file(company_id, "learnings/ERRORS.md", updated)
        logger.info(f"[ReflectionEngine] Logged error for company {company_id}: {error_message[:50]}")

    @classmethod
    def record_learning(
        cls,
        company_id: str | int,
        topic: str,
        insight: str,
        source_run_id: Optional[str] = None,
    ) -> None:
        """Appends a distilled insight into learnings/LEARNINGS.md."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = (
            f"\n### [{now_str}] {topic}\n"
            f"- **Insight**: {insight}\n"
            f"- **Source Run**: `{source_run_id or 'manual'}`\n"
        )

        existing = workspace_manager.read_file(company_id, "learnings/LEARNINGS.md")
        if not existing:
            existing = "# Operational & Strategic Learnings\n"

        updated = existing + entry
        workspace_manager.write_file(company_id, "learnings/LEARNINGS.md", updated)
        logger.info(f"[ReflectionEngine] Logged learning for company {company_id}: {topic}")

    @classmethod
    def run_nightly_reflection(
        cls,
        company_id: str | int,
        recent_runs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Summarizes daily performance and promotes insights."""
        errors_count = 0
        success_count = 0

        for r in recent_runs:
            if not r.get("ok", True):
                errors_count += 1
                cls.record_error(
                    company_id=company_id,
                    error_message=r.get("error", "Unknown error"),
                    provider=r.get("provider", "native"),
                    action=r.get("action", "run"),
                )
            else:
                success_count += 1

        summary = {
            "company_id": str(company_id),
            "date": datetime.now(timezone.utc).isoformat(),
            "total_runs": len(recent_runs),
            "success_count": success_count,
            "errors_count": errors_count,
        }
        logger.info(f"[ReflectionEngine] Completed nightly reflection for company {company_id}: {summary}")
        return summary
