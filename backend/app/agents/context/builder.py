"""Context Builder for assembling structured, provenance-aware agent contexts."""

from datetime import datetime, timezone
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.modules.finance.finance_tools import get_financial_summary
from app.modules.sales.sales_tools import get_pipeline_summary
from app.modules.strategy.tools import list_okrs, list_projects

logger = logging.getLogger(__name__)


class ContextSection(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    source: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "success"
    error: Optional[str] = None


class AgentContext(BaseModel):
    workspace_id: str
    company_id: Optional[str] = None
    agent_key: Optional[str] = None
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sections: dict[str, ContextSection] = Field(default_factory=dict)


def _safe_fetch_section(source_name: str, fetcher_fn, **kwargs) -> ContextSection:
    now = datetime.now(timezone.utc)
    try:
        res = fetcher_fn(**kwargs)
        if isinstance(res, dict) and res.get("status") in ("error", "failed"):
            return ContextSection(
                data={},
                source=source_name,
                fetched_at=now,
                status="error",
                error=res.get("message") or res.get("error", "Unknown tool error"),
            )
        return ContextSection(
            data=res if isinstance(res, dict) else {"result": res},
            source=source_name,
            fetched_at=now,
            status=res.get("status", "success") if isinstance(res, dict) else "success",
        )
    except Exception as exc:
        logger.warning(f"[ContextBuilder] Failed to fetch section from {source_name}: {exc}")
        return ContextSection(
            data={},
            source=source_name,
            fetched_at=now,
            status="error",
            error=str(exc),
        )


def build_agent_context(
    db: Session,
    workspace_id: int,
    company_id: Optional[int] = None,
    agent_key: Optional[str] = None,
    user_id: Optional[int] = None,
) -> AgentContext:
    """Build unified multi-domain context for agents with freshness and graceful degradation."""
    sections: dict[str, ContextSection] = {}

    # 1. Sales Pipeline
    sections["sales"] = _safe_fetch_section(
        "sales_tools.get_pipeline_summary",
        get_pipeline_summary,
        db=db,
        workspace_id=workspace_id,
    )

    # 2. Financial Management
    sections["finance"] = _safe_fetch_section(
        "finance_tools.get_financial_summary",
        get_financial_summary,
        db=db,
        workspace_id=workspace_id,
    )

    # 3. Strategy OKRs
    sections["okrs"] = _safe_fetch_section(
        "strategy.tools.list_okrs",
        list_okrs,
        db=db,
        workspace_id=workspace_id,
    )

    # 4. Strategy Projects
    sections["projects"] = _safe_fetch_section(
        "strategy.tools.list_projects",
        list_projects,
        db=db,
        workspace_id=workspace_id,
    )

    return AgentContext(
        workspace_id=str(workspace_id),
        company_id=str(company_id) if company_id else None,
        agent_key=agent_key,
        built_at=datetime.now(timezone.utc),
        sections=sections,
    )
