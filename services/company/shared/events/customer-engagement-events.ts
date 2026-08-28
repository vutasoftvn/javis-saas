import { makeBusinessEvent, type BusinessEventEnvelope } from "./envelope";

export type Actor = { kind: "user" | "agent" | "system"; id: string };
const PRODUCER = { service: "company.commercial", version: process.env.COMPANY_SERVICE_VERSION || "0.0.0-dev" };

function thread<T extends Record<string, unknown>>(
  eventType: string, workspaceId: string, threadId: string, correlationId: string,
  classification: "confidential" | "restricted", actor: Actor, payload: T,
): BusinessEventEnvelope<T> {
  return makeBusinessEvent({
    eventType, workspaceId, aggregateType: "engagement_thread", aggregateId: threadId,
    correlationId, actor, classification, producer: PRODUCER, payload,
  });
}

export function buildThreadOpenedEvent(
  t: { id: string; workspaceId: string; inboxId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.opened.v1", t.workspaceId, t.id, t.correlationId, "confidential", actor, {
    thread_id: t.id, inbox_id: t.inboxId,
  });
}

export function buildThreadAssignedEvent(
  a: { threadId: string; workspaceId: string; assignmentId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.assigned.v1", a.workspaceId, a.threadId, a.correlationId, "confidential", actor, {
    thread_id: a.threadId, assignment_id: a.assignmentId,
  });
}

export function buildThreadTakenOverEvent(
  a: { threadId: string; workspaceId: string; newOwnerMemberId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.taken_over.v1", a.workspaceId, a.threadId, a.correlationId, "confidential", actor, {
    thread_id: a.threadId, new_owner_member_id: a.newOwnerMemberId,
  });
}

export function buildMessageReceivedEvent(
  m: { threadId: string; workspaceId: string; messageId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.message.received.v1", m.workspaceId, m.threadId, m.correlationId, "restricted", actor, {
    thread_id: m.threadId, message_id: m.messageId,
  });
}

export function buildMessageSentEvent(
  m: { threadId: string; workspaceId: string; messageId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.message.sent.v1", m.workspaceId, m.threadId, m.correlationId, "restricted", actor, {
    thread_id: m.threadId, message_id: m.messageId,
  });
}

export function buildThreadStatusChangedEvent(
  s: { threadId: string; workspaceId: string; previousState: string; currentState: string; correlationId: string },
  actor: Actor,
) {
  return thread("engagement.thread.status_changed.v1", s.workspaceId, s.threadId, s.correlationId, "confidential", actor, {
    thread_id: s.threadId, previous_state: s.previousState, current_state: s.currentState,
  });
}

export function buildThreadResolvedEvent(
  s: { threadId: string; workspaceId: string; resolutionCode: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.resolved.v1", s.workspaceId, s.threadId, s.correlationId, "confidential", actor, {
    thread_id: s.threadId, resolution_code: s.resolutionCode,
  });
}

export function buildDecisionRequestSubmittedEvent(
  d: { decisionRequestId: string; workspaceId: string; requestType: string; correlationId: string }, actor: Actor,
) {
  return makeBusinessEvent({
    eventType: "engagement.decision_request.submitted.v1", workspaceId: d.workspaceId,
    aggregateType: "engagement_decision_request", aggregateId: d.decisionRequestId,
    correlationId: d.correlationId, actor, classification: "confidential", producer: PRODUCER,
    payload: { decision_request_id: d.decisionRequestId, request_type: d.requestType },
  });
}

export function buildDecisionRequestDecidedEvent(
  d: { decisionRequestId: string; workspaceId: string; decision: string; correlationId: string }, actor: Actor,
) {
  return makeBusinessEvent({
    eventType: "engagement.decision_request.decided.v1", workspaceId: d.workspaceId,
    aggregateType: "engagement_decision_request", aggregateId: d.decisionRequestId,
    correlationId: d.correlationId, actor, classification: "confidential", producer: PRODUCER,
    payload: { decision_request_id: d.decisionRequestId, decision: d.decision },
  });
}
