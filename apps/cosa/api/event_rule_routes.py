"""Admin endpoint tạo/enable EventTriggerRule.

Enable được gác bởi `can_enable_trigger` (P1 Task 8): artifact-only rule bật
tự do; proposal/write đòi eval/promotion evidence khớp fingerprint; write rule
thêm human approval. Rule LUÔN tạo với `enabled=false`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity
from apps.cosa.events.trigger_promotion import can_enable_trigger

__all__ = ["create_event_rule_router"]


class AgentSpecPin(BaseModel):
    id: str
    version: str
    definitionHash: str


class CreateRuleRequest(BaseModel):
    workspaceId: str
    eventType: str
    agentSpec: AgentSpecPin
    mode: str = Field(pattern="^(artifact_only|proposal|write)$")
    maxRunsPerAggregatePerDay: int = 1
    requiredCapabilities: list[str] = Field(default_factory=list)
    aggregateFilter: dict | None = None
    evalEvidenceRef: str | None = None
    eventSchemaVersion: int = 1


class EnableRuleRequest(BaseModel):
    workspaceId: str
    approvedBy: str | None = None


def _deps(request: Request):
    plane = getattr(request.app.state, "plane", None)
    deps = getattr(plane, "event_intake_deps", None) if plane else None
    if deps is None or getattr(deps, "rule_store", None) is None:
        raise HTTPException(status_code=503, detail="event intake dependencies not configured")
    return deps


def create_event_rule_router() -> APIRouter:
    router = APIRouter(prefix="/agent/events/rules", tags=["event-rules"])

    @router.post("", status_code=201)
    async def create_rule(body: CreateRuleRequest, request: Request):
        deps = _deps(request)
        rule = EventTriggerRule(
            rule_id=f"evt-rule-{uuid.uuid4().hex[:12]}",
            workspace_id=body.workspaceId,
            event_type=body.eventType,
            agent_spec=PinnedSpecIdentity(
                id=body.agentSpec.id,
                version=body.agentSpec.version,
                definition_hash=body.agentSpec.definitionHash,
            ),
            mode=body.mode,  # type: ignore[arg-type]
            max_runs_per_aggregate_per_day=body.maxRunsPerAggregatePerDay,
            required_capabilities=tuple(body.requiredCapabilities),
            aggregate_filter=body.aggregateFilter,
            enabled=False,  # LUÔN false lúc tạo
            eval_evidence_ref=body.evalEvidenceRef,
            event_schema_version=body.eventSchemaVersion,
        )
        await deps.rule_store.upsert(rule)
        return {"ruleId": rule.rule_id, "enabled": False}

    @router.get("")
    async def list_rules(workspaceId: str, request: Request):
        deps = _deps(request)
        rules = await deps.rule_store.list_by_workspace(workspaceId)
        return {
            "items": [
                {
                    "ruleId": r.rule_id,
                    "eventType": r.event_type,
                    "mode": r.mode,
                    "enabled": r.enabled,
                    "evalEvidenceRef": r.eval_evidence_ref,
                }
                for r in rules
            ]
        }

    @router.post("/{rule_id}/enable")
    async def enable_rule(rule_id: str, body: EnableRuleRequest, request: Request):
        deps = _deps(request)
        rule = await deps.rule_store.get(rule_id)
        if rule is None or rule.workspace_id != body.workspaceId:
            raise HTTPException(status_code=404, detail="rule not found in workspace")

        if rule.mode == "artifact_only":
            await deps.rule_store.set_enabled(rule_id, True)
            return {"status": "enabled"}

        evidence = None
        if rule.eval_evidence_ref and deps.evidence_store is not None:
            getter = getattr(deps.evidence_store, "get", None) or deps.evidence_store.load
            evidence = await getter(rule.eval_evidence_ref)
        fingerprints = await deps.fingerprint_provider.current(rule)
        policy_version = getattr(deps.trigger_policy, "policy_version", "p1")
        gate = can_enable_trigger(rule, evidence, fingerprints, policy_version=policy_version)

        if not gate.allowed:
            raise HTTPException(status_code=422, detail={"status": "denied", "reason": gate.reason})
        if gate.requires_human_approval and not body.approvedBy:
            return {"status": "pending_human_approval"}

        await deps.rule_store.set_enabled(rule_id, True)
        result = {"status": "enabled"}
        if body.approvedBy:
            result["approvedBy"] = body.approvedBy
        return result

    return router
