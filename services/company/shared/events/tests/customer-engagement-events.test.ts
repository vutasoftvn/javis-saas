import { describe, expect, it } from "vitest";
import {
  buildThreadOpenedEvent, buildMessageReceivedEvent, buildThreadStatusChangedEvent,
  buildMessageSentEvent, buildDecisionRequestSubmittedEvent,
} from "../customer-engagement-events";

const actor = { kind: "user" as const, id: "wm-1" };

describe("customer-engagement-events", () => {
  it("thread.opened.v1 uses company.commercial producer + confidential", () => {
    const e = buildThreadOpenedEvent(
      { id: "10", workspaceId: "1", inboxId: "5", correlationId: "c1" }, actor);
    expect(e.eventType).toBe("engagement.thread.opened.v1");
    expect(e.producer.service).toBe("company.commercial");
    expect(e.classification).toBe("confidential");
    expect(e.aggregateId).toBe("10");
  });

  it("message.received.v1 is restricted with reference-only payload", () => {
    const e = buildMessageReceivedEvent(
      { threadId: "10", workspaceId: "1", messageId: "77", correlationId: "c1" }, actor);
    expect(e.classification).toBe("restricted");
    // validateEnvelope trong makeBusinessEvent sẽ throw nếu payload có key không phải *_id/ref/hash/count
    expect(Object.keys(e.payload).every((k) => /^[a-z0-9_]*(id|ref|hash|count)$/.test(k))).toBe(true);
  });

  it("thread.status_changed.v1 carries previous + current", () => {
    const e = buildThreadStatusChangedEvent(
      { threadId: "10", workspaceId: "1", previousState: "open", currentState: "resolved", correlationId: "c1" }, actor);
    expect(e.payload).toMatchObject({ previous_state: "open", current_state: "resolved" });
  });

  it("message.sent.v1 is restricted with reference-only payload", () => {
    const e = buildMessageSentEvent(
      { threadId: "10", workspaceId: "1", messageId: "77", correlationId: "c1" }, actor);
    expect(e.eventType).toBe("engagement.message.sent.v1");
    expect(e.classification).toBe("restricted");
    expect(Object.keys(e.payload).every((k) => /^[a-z0-9_]*(id|ref|hash|count)$/.test(k))).toBe(true);
  });

  it("decision_request.submitted.v1 is confidential with correct aggregate type", () => {
    const decisionRequestId = "dr-42";
    const e = buildDecisionRequestSubmittedEvent(
      { decisionRequestId, workspaceId: "1", requestType: "approval", correlationId: "c1" }, actor);
    expect(e.eventType).toBe("engagement.decision_request.submitted.v1");
    expect(e.aggregateType).toBe("engagement_decision_request");
    expect(e.producer.service).toBe("company.commercial");
    expect(e.classification).toBe("confidential");
    expect(e.aggregateId).toBe(decisionRequestId);
  });
});
