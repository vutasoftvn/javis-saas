import { randomUUID } from "node:crypto";
import { makeBusinessEvent, BusinessEventEnvelope } from "../../shared/events/envelope";
import {
  OPERATIONS_TASK_CREATED_V1,
  OPERATIONS_TASK_COMPLETED_V1,
  OPERATIONS_WORK_PACKAGE_CREATED_V1,
  OPERATIONS_DECISION_RECORDED_V1,
  OPERATIONS_EVIDENCE_LINKED_V1,
  OPERATIONS_RISK_RAISED_V1,
  OPERATIONS_RISK_RESOLVED_V1,
  TaskCreatedPayloadV1,
  TaskCompletedPayloadV1,
  WorkPackageCreatedPayloadV1,
  DecisionRecordedPayloadV1,
  EvidenceLinkedPayloadV1,
  RiskRaisedPayloadV1,
  RiskResolvedPayloadV1,
} from "../../shared/events/event-types";
import type { Task } from "../handlers/task.handler";

export interface EventContext {
  correlationId?: string;
  causationId?: string;
  actor?: { kind: "user" | "agent" | "system"; id: string };
}

export function buildTaskCreatedEvent(
  task: Task,
  ctx?: EventContext
): BusinessEventEnvelope<TaskCreatedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1,
    workspaceId: task.workspaceId,
    projectId: task.projectId,
    aggregateType: "task",
    aggregateId: task.id,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      taskId: task.id,
      workspaceId: task.workspaceId,
      project_id: task.projectId,
      title: task.title,
      status: task.status,
    },
  });
}

export function buildTaskCompletedEvent(
  task: Task,
  ctx?: EventContext
): BusinessEventEnvelope<TaskCompletedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_COMPLETED_V1,
    workspaceId: task.workspaceId,
    projectId: task.projectId,
    aggregateType: "task",
    aggregateId: task.id,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      taskId: task.id,
      workspaceId: task.workspaceId,
      project_id: task.projectId,
      completedAt: new Date().toISOString(),
    },
  });
}

export interface WorkPackageEventData {
  workPackageId: string;
  taskId: string;
  projectId: string;
  workspaceId: string;
  status: string;
}

export function buildWorkPackageCreatedEvent(
  wp: WorkPackageEventData,
  ctx?: EventContext
): BusinessEventEnvelope<WorkPackageCreatedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_WORK_PACKAGE_CREATED_V1,
    workspaceId: wp.workspaceId,
    projectId: wp.projectId,
    aggregateType: "work_package",
    aggregateId: wp.workPackageId,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      workPackageId: wp.workPackageId,
      taskId: wp.taskId,
      project_id: wp.projectId,
      status: wp.status,
    },
  });
}

export interface DecisionRecordView {
  decisionId: string;
  projectId: string;
  workspaceId: string;
  decision: string;
}

export function buildDecisionRecordedEvent(
  decision: DecisionRecordView,
  ctx?: EventContext
): BusinessEventEnvelope<DecisionRecordedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_DECISION_RECORDED_V1,
    workspaceId: decision.workspaceId,
    projectId: decision.projectId,
    aggregateType: "decision",
    aggregateId: decision.decisionId,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      decision_id: decision.decisionId,
      project_id: decision.projectId,
      decision: decision.decision,
      status: "recorded",
    },
  });
}

export interface EvidenceView {
  evidenceId: string;
  projectId: string;
  workspaceId: string;
  sourceType: string;
}

export function buildEvidenceLinkedEvent(
  evidence: EvidenceView,
  ctx?: EventContext
): BusinessEventEnvelope<EvidenceLinkedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_EVIDENCE_LINKED_V1,
    workspaceId: evidence.workspaceId,
    projectId: evidence.projectId,
    aggregateType: "evidence",
    aggregateId: evidence.evidenceId,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      evidence_ref: evidence.evidenceId,
      project_id: evidence.projectId,
      sourceType: evidence.sourceType,
      status: "linked",
    },
  });
}

export interface RiskView {
  riskId: string;
  projectId: string;
  workspaceId: string;
  title?: string;
}

export function buildRiskRaisedEvent(
  risk: RiskView,
  ctx?: EventContext
): BusinessEventEnvelope<RiskRaisedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_RISK_RAISED_V1,
    workspaceId: risk.workspaceId,
    projectId: risk.projectId,
    aggregateType: "risk",
    aggregateId: risk.riskId,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      risk_id: risk.riskId,
      project_id: risk.projectId,
      title: risk.title || "Risk",
      status: "raised",
    },
  });
}

export function buildRiskResolvedEvent(
  risk: RiskView,
  ctx?: EventContext
): BusinessEventEnvelope<RiskResolvedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_RISK_RESOLVED_V1,
    workspaceId: risk.workspaceId,
    projectId: risk.projectId,
    aggregateType: "risk",
    aggregateId: risk.riskId,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      risk_id: risk.riskId,
      project_id: risk.projectId,
      title: risk.title || "Risk",
      status: "resolved",
    },
  });
}
