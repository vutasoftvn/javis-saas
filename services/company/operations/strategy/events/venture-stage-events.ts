import { randomUUID } from "node:crypto";
import { makeBusinessEvent, BusinessEventEnvelope } from "../../../shared/events/envelope";
import { VENTURE_STAGE_CHANGED, PROJECT_PHASE_CHANGED } from "../../../shared/events";

export interface VentureStageChangedPayload {
  workspaceId: string;
  fromStage: string;
  toStage: string;
  reason: string;
  overrideFlag: boolean;
  actorMemberId: string | null;
  timestamp: string;
}

export function buildVentureStageChangedEvent(input: {
  workspaceId: string;
  fromStage: string;
  toStage: string;
  reason: string;
  overrideFlag: boolean;
  actorMemberId: string | null;
}): BusinessEventEnvelope<VentureStageChangedPayload> {
  return makeBusinessEvent({
    eventType: VENTURE_STAGE_CHANGED,
    workspaceId: input.workspaceId,
    aggregateType: "venture_workspace",
    aggregateId: input.workspaceId,
    correlationId: randomUUID(),
    actor: {
      kind: input.actorMemberId ? "user" : "system",
      id: input.actorMemberId ?? "strategy.lifecycle",
    },
    classification: "internal",
    payload: {
      workspaceId: input.workspaceId,
      fromStage: input.fromStage,
      toStage: input.toStage,
      reason: input.reason,
      overrideFlag: input.overrideFlag,
      actorMemberId: input.actorMemberId,
      timestamp: new Date().toISOString(),
    },
  });
}

export interface ProjectPhaseChangedPayload {
  projectId: string;
  workspaceId: string;
  fromPhase: string;
  toPhase: string;
  actorMemberId?: string | null;
  timestamp: string;
}

export function buildProjectPhaseChangedEvent(input: {
  projectId: string;
  workspaceId: string;
  fromPhase: string;
  toPhase: string;
  actorMemberId?: string | null;
}): BusinessEventEnvelope<ProjectPhaseChangedPayload> {
  return makeBusinessEvent({
    eventType: PROJECT_PHASE_CHANGED,
    workspaceId: input.workspaceId,
    aggregateType: "project",
    aggregateId: input.projectId,
    correlationId: randomUUID(),
    actor: {
      kind: input.actorMemberId ? "user" : "system",
      id: input.actorMemberId ?? "strategy.gate_evaluator",
    },
    classification: "internal",
    payload: {
      projectId: input.projectId,
      workspaceId: input.workspaceId,
      fromPhase: input.fromPhase,
      toPhase: input.toPhase,
      actorMemberId: input.actorMemberId,
      timestamp: new Date().toISOString(),
    },
  });
}
