"""Toolset Resolver (G1 §4 primitive 3 / G3 Phase 1C).

Single choke-point deciding which ToolSpecs get OFFERED to an LLM, before
any schema is built. Filters, in order: workspace feature flag (existing
`available_tools`), static per-tool agent allowlist (`allowed_agent_keys`),
workspace stage (`available_stages`), then `availability_check` -
fail-closed: an exception or a False return excludes the tool rather than
risking a false-positive grant, matching this codebase's default-deny
posture elsewhere (see CapabilityGateway's default deny for the same
reasoning).

This is NOT a replacement for PolicyEngine/GovernanceKernel
(app/workforce/agents/governance/policy_engine.py, kernel.py) - that gate
runs AFTER the LLM has already picked one specific tool call, auditing and
allow/deny/require-approval on that single call. This resolver runs BEFORE
that, deciding the candidate list the LLM is even shown. Skipping this
layer was the actual gap: neither of the two real call sites that build
tool schemas for an LLM (chat's `company_tools.py::tool_specs()` and the
agent runtime's `deepseek_harness.py` tool loop) consulted PolicyEngine at
schema-build time, so a tool PolicyEngine would later deny could still be
offered - this module is where that offer-time filtering now lives.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.tool_registry import ToolSpec, available_tools

logger = logging.getLogger(__name__)


def get_workspace_company_stage(db: Session, workspace_id: int) -> Optional[str]:
    """Best-effort read of `Workspace.company_stage` for callers that want to
    pass real stage data into `resolve_toolset()`. Not called automatically by
    `resolve_toolset()` itself - callers that already have the stage on hand
    (e.g. from a `WorkspaceContext`) should pass it directly instead of
    triggering a second query here.
    """
    from app.platform.auth.models import Workspace

    try:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        return workspace.company_stage if workspace is not None else None
    except Exception:
        logger.exception("Failed to resolve company_stage for workspace %s", workspace_id)
        return None


@dataclass(frozen=True)
class ToolsetContext:
    """Everything a ToolSpec.availability_check might need. Add fields here
    as new gating dimensions are needed, rather than changing every
    availability_check call site's signature."""
    agent_key: Optional[str]
    workspace_id: int
    company_stage: Optional[str] = None


def resolve_toolset(
    db: Session,
    workspace_id: int,
    agent_key: Optional[str] = None,
    company_stage: Optional[str] = None,
    require_chat_schema: bool = False,
) -> list[ToolSpec]:
    """Returns the ToolSpecs that should be offered right now.

    `agent_key=None` skips the `allowed_agent_keys` check entirely rather
    than filtering against a fabricated pseudo-key - this matches
    `company_tools.py`'s general chat surface, which has never had a
    single-agent identity and must keep seeing every workspace-enabled tool
    it already shows today (adding an agent_key filter there would be a
    behavior change, not a resolver mechanism).

    `require_chat_schema=True` additionally requires `chat_schema` to be
    set and `mutating` to be False - the same two checks `chat_tools()`
    already applied, folded in here so callers that need both filters make
    one pass instead of stacking two.
    """
    context = ToolsetContext(agent_key=agent_key, workspace_id=workspace_id, company_stage=company_stage)
    resolved: list[ToolSpec] = []

    for spec in available_tools(db, workspace_id):
        if require_chat_schema and (not spec.chat_schema or spec.mutating):
            continue
        if agent_key is not None and spec.allowed_agent_keys and agent_key not in spec.allowed_agent_keys:
            continue
        if spec.available_stages is not None and company_stage not in spec.available_stages:
            continue
        if spec.availability_check is not None:
            try:
                if not spec.availability_check(context):
                    continue
            except Exception:
                logger.exception(
                    "Toolset resolver: availability_check raised for %s - excluding (fail-closed)",
                    spec.qualified_name,
                )
                continue
        resolved.append(spec)

    return resolved
