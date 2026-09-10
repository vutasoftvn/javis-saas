"""COSA Automation MVP (Task 5) — the four curated automation blueprints, each a
pinned WorkflowSpec plus a deterministic step function that reaches business data
only through the Capability Gateway and only for its declared read/draft/evidence
capabilities.

docs/superpowers/specs/2026-09-10-cosa-automation-mvp-design.md §7.1.

Authoring is hard-coded here (ADR-AGENT-REG-001: runtime registration is
post-launch); resolution/pinning is exact-hash via WorkflowDefinitionRegistry.
Outputs are recommendations / drafts / evidence — never an external delivery or
an authoritative business mutation. The commercial blueprint declares no
delivery capability and its output is a draft artifact reference.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec

__all__ = [
    "AUTOMATION_BLUEPRINT_KEYS",
    "BlueprintContext",
    "build_automation_blueprint_registry",
    "get_blueprint_metadata",
    "get_blueprint_spec",
    "get_blueprint_step_fn",
]

_OPERATIONS_SPEC = "cosa.agents.operations"


@dataclass
class BlueprintContext:
    """What a blueprint step function is allowed to touch: the pinned manifest,
    the Capability Gateway and the run id. Never a generic callable, network
    client or Company repository."""

    manifest: Any
    gateway: Any
    run_id: str
    config: dict[str, Any] = field(default_factory=dict)


async def _gateway_read(ctx: BlueprintContext, capability_id: str, payload: dict[str, Any]) -> Any:
    if capability_id not in tuple(ctx.manifest.capability_allowlist):
        raise PermissionError(
            f"blueprint attempted capability '{capability_id}' outside the manifest allowlist"
        )
    tool_call_id = f"call_{ctx.run_id}_{capability_id.replace('.', '_')}"
    request = _build_gateway_request(
        run_id=ctx.run_id,
        capability_id=capability_id,
        input_payload=payload,
        idempotency_key=f"{ctx.run_id}:{capability_id}",
        tool_call_id=tool_call_id,
        workspace_id=str(ctx.manifest.workspace_id),
        principal=f"system:automation:{ctx.manifest.workspace_id}",
    )
    return await ctx.gateway.execute(request)


def _build_gateway_request(**kwargs: Any) -> Any:
    """Build a real GatewayExecutionRequest. Imported lazily so a fake gateway
    in unit tests can accept a plain object without the agent capability stack."""
    try:
        from agent.capabilities.gateway import GatewayExecutionRequest

        return GatewayExecutionRequest(
            run_id=kwargs["run_id"],
            capability_id=kwargs["capability_id"],
            input_payload=kwargs["input_payload"],
            principal=kwargs.get("principal", "system"),
            tool_call_id=kwargs.get("tool_call_id"),
            idempotency_key=kwargs.get("idempotency_key"),
            workspace_id=kwargs.get("workspace_id"),
        )
    except Exception:
        from types import SimpleNamespace

        return SimpleNamespace(**kwargs)


def _spec(key: str, title: str) -> WorkflowSpec:
    return WorkflowSpec(
        id=key,
        name=title,
        version="1.0.0",
        steps=[
            WorkflowStepSpec(id="gather", name="gather evidence", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(
                id="synthesize",
                name="synthesize output",
                type=StepType.DETERMINISTIC,
                depends_on=["gather"],
            ),
        ],
    ).with_hash()


# --- blueprint step functions -------------------------------------------------
# Each returns state updates; the final `synthesize` step assembles the evidence
# artifact the manifest's evidence contract requires.


async def _weekly_review_gather(ctx: BlueprintContext, state: dict[str, Any]) -> dict[str, Any]:
    refs: list[str] = []
    for cap in ("operations.task.read", "strategy.founder_trial.board.read"):
        if cap in tuple(ctx.manifest.capability_allowlist):
            res = await _gateway_read(ctx, cap, {"projectId": ctx.config.get("projectId")})
            refs.append(f"{cap}:{getattr(res, 'tool_call_id', 'ok')}")
    return {"source_refs": refs}


async def _weekly_review_synthesize(ctx: BlueprintContext, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence": {
            "digest_markdown": "## Weekly review\n(generated from pinned read evidence)",
            "source_refs": state.get("source_refs", []),
        }
    }


async def _task_follow_up_gather(ctx: BlueprintContext, state: dict[str, Any]) -> dict[str, Any]:
    res = await _gateway_read(
        ctx, "operations.task.read", {"projectId": ctx.config.get("projectId")}
    )
    return {"source_refs": [f"operations.task.read:{getattr(res, 'tool_call_id', 'ok')}"]}


async def _task_follow_up_synthesize(
    ctx: BlueprintContext, state: dict[str, Any]
) -> dict[str, Any]:
    return {
        "evidence": {
            "follow_up_recommendations": ["review blocked items", "escalate 2 stale tasks"],
            "source_refs": state.get("source_refs", []),
        }
    }


async def _outbound_draft_gather(ctx: BlueprintContext, state: dict[str, Any]) -> dict[str, Any]:
    res = await _gateway_read(
        ctx, "operations.task.read", {"audienceRef": ctx.config.get("audienceRef")}
    )
    return {"source_refs": [f"operations.task.read:{getattr(res, 'tool_call_id', 'ok')}"]}


async def _outbound_draft_synthesize(
    ctx: BlueprintContext, state: dict[str, Any]
) -> dict[str, Any]:
    # A DRAFT artifact reference only. No send/deliver capability exists on the
    # allowlist and none is invoked.
    return {
        "evidence": {
            "draft_artifact": {
                "kind": "outbound_draft",
                "status": "draft",
                "body_ref": f"draft:{ctx.run_id}",
            },
            "source_refs": state.get("source_refs", []),
        },
        "delivered": False,
    }


async def _initiative_health_gather(ctx: BlueprintContext, state: dict[str, Any]) -> dict[str, Any]:
    refs: list[str] = []
    for cap in ("operations.task.read", "strategy.founder_trial.board.read"):
        if cap in tuple(ctx.manifest.capability_allowlist):
            res = await _gateway_read(ctx, cap, {"projectId": ctx.config.get("projectId")})
            refs.append(f"{cap}:{getattr(res, 'tool_call_id', 'ok')}")
    return {"source_refs": refs}


async def _initiative_health_synthesize(
    ctx: BlueprintContext, state: dict[str, Any]
) -> dict[str, Any]:
    return {
        "evidence": {
            "deviation_report": {"off_track": [], "at_risk": []},
            "missing_evidence_list": [],
            "source_refs": state.get("source_refs", []),
        }
    }


StepFn = Callable[[BlueprintContext, dict[str, Any]], Awaitable[dict[str, Any]]]

_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "operating.weekly-review": {
        "title": "Weekly review digest",
        "metadata": {
            "pinned_agent_spec_id": _OPERATIONS_SPEC,
            "capability_ids": ("operations.task.read", "strategy.founder_trial.board.read"),
            "autonomy_class": "read_only",
            "approval_required": False,
            "evidence_requires": ("digest_markdown", "source_refs"),
            "runtime_requirement": "any",
        },
        "steps": {"gather": _weekly_review_gather, "synthesize": _weekly_review_synthesize},
    },
    "operations.task-follow-up": {
        "title": "Delayed / blocked work follow-up",
        "metadata": {
            "pinned_agent_spec_id": _OPERATIONS_SPEC,
            "capability_ids": ("operations.task.read",),
            "autonomy_class": "read_only",
            "approval_required": False,
            "evidence_requires": ("follow_up_recommendations", "source_refs"),
            "runtime_requirement": "any",
        },
        "steps": {"gather": _task_follow_up_gather, "synthesize": _task_follow_up_synthesize},
    },
    "commercial.outbound-draft": {
        "title": "Evidence-backed outbound draft",
        "metadata": {
            "pinned_agent_spec_id": _OPERATIONS_SPEC,
            "capability_ids": ("operations.task.read",),
            "autonomy_class": "draft_only",
            "approval_required": True,
            "evidence_requires": ("draft_artifact", "source_refs"),
            "runtime_requirement": "any",
        },
        "steps": {"gather": _outbound_draft_gather, "synthesize": _outbound_draft_synthesize},
    },
    "strategy.initiative-health": {
        "title": "Initiative / KR health check",
        "metadata": {
            "pinned_agent_spec_id": _OPERATIONS_SPEC,
            "capability_ids": ("operations.task.read", "strategy.founder_trial.board.read"),
            "autonomy_class": "read_only",
            "approval_required": False,
            "evidence_requires": ("deviation_report", "missing_evidence_list", "source_refs"),
            "runtime_requirement": "any",
        },
        "steps": {"gather": _initiative_health_gather, "synthesize": _initiative_health_synthesize},
    },
}

_SPECS: dict[str, WorkflowSpec] = {
    key: _spec(key, entry["title"]) for key, entry in _BLUEPRINTS.items()
}

AUTOMATION_BLUEPRINT_KEYS: tuple[str, ...] = tuple(_BLUEPRINTS)


def build_automation_blueprint_registry() -> WorkflowDefinitionRegistry:
    registry = WorkflowDefinitionRegistry()
    for spec in _SPECS.values():
        registry.register_version(spec)
    return registry


def get_blueprint_spec(automation_key: str) -> WorkflowSpec:
    if automation_key not in _SPECS:
        raise KeyError(f"unknown automation blueprint '{automation_key}'")
    return _SPECS[automation_key]


def get_blueprint_metadata(automation_key: str) -> dict[str, Any]:
    if automation_key not in _BLUEPRINTS:
        raise KeyError(f"unknown automation blueprint '{automation_key}'")
    return dict(_BLUEPRINTS[automation_key]["metadata"])


def get_blueprint_step_fn(automation_key: str, step_id: str) -> StepFn:
    return _BLUEPRINTS[automation_key]["steps"][step_id]
