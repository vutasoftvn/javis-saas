import { describe, expect, it, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../../shared/events/event-types";
import { readOutbox } from "./helpers/outbox";
import { runRelayOnce, AI_INITIATIVE_PROMOTED_EVENT_TYPE } from "../../events/outbox-relay.service";
import { runAiInitiativeRelayOnce } from "../services/ai-initiative-relay.service";
import { setCustomPromotionPublisher } from "../services/ai-initiative-cosa.client";

function aiPromotedEvent(workspaceId: string, initiativeId: string) {
  return makeBusinessEvent({
    eventType: AI_INITIATIVE_PROMOTED_EVENT_TYPE,
    workspaceId,
    projectId: "proj_relay_ai",
    aggregateType: "ai_initiative",
    aggregateId: initiativeId,
    correlationId: "corr_relay_ai",
    actor: { kind: "system", id: "test" },
    classification: "internal",
    payload: {
      initiative_id: initiativeId,
      project_id: "proj_relay_ai",
      from_state: "VALIDATE",
      to_state: "SCALE_CANDIDATE",
      revision: 3,
      decision_id: "dec_relay_ai",
      snapshot: {
        initiativeId,
        initiativeRevision: 3,
        workspaceId,
        projectId: "proj_relay_ai",
        lifecycleState: "SCALE_CANDIDATE",
        riskTier: "LOW",
        autonomyTier: "A1",
        decisionId: "dec_relay_ai",
        decisionHash: "hash_relay_ai",
        pins: {},
      },
    },
  });
}

function taskEvent(workspaceId: string, aggregateId: string) {
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1,
    workspaceId,
    projectId: "proj_relay_ai",
    aggregateType: "task",
    aggregateId,
    correlationId: "corr_relay_ai_task",
    actor: { kind: "system", id: "test" },
    classification: "internal",
    payload: { taskId: aggregateId, workspaceId, project_id: "proj_relay_ai", title: "Relay Test", status: "todo" },
  });
}

describe("ai initiative outbox relay", () => {
  beforeEach(async () => {
    await db.execute(sql`DELETE FROM integration.event_outbox;`);
    setCustomPromotionPublisher(null);
  });

  it("delivers ai.initiative.promoted.v1 via publishPromotionSnapshotToCosa and marks it delivered", async () => {
    let received: string | null = null;
    setCustomPromotionPublisher(async (snapshot) => {
      received = snapshot.initiativeId;
      return { accepted: true, status: "accepted", decisionId: snapshot.decisionId };
    });

    await db.transaction((tx) => appendOutboxEvent(tx, aiPromotedEvent("ws_relay_ai", "init_relay_1")));
    await runAiInitiativeRelayOnce({ batchLimit: 10 });

    expect(received).toBe("init_relay_1");
    const [row] = await readOutbox("ws_relay_ai", "ai_initiative", "init_relay_1");
    expect(row.status).toBe("delivered");
  });

  it("treats a COSA rejection (403) as terminal, not retried", async () => {
    setCustomPromotionPublisher(async () => {
      const { APIError } = await import("encore.dev/api");
      throw APIError.permissionDenied("COSA rejected snapshot: foreign project or hash drift");
    });

    await db.transaction((tx) => appendOutboxEvent(tx, aiPromotedEvent("ws_relay_ai", "init_relay_2")));
    await runAiInitiativeRelayOnce({ batchLimit: 10 });

    const [row] = await readOutbox("ws_relay_ai", "ai_initiative", "init_relay_2");
    expect(row.status).toBe("delivered");
  });

  it("the generic relay never claims or misroutes ai.initiative.promoted.v1 events", async () => {
    let genericPostCount = 0;
    const post = async (_url: string, _body: string, _headers: Record<string, string>) => {
      genericPostCount++;
      return { status: 200, body: { outcome: "accepted" } };
    };

    await db.transaction((tx) => appendOutboxEvent(tx, aiPromotedEvent("ws_relay_ai", "init_relay_3")));
    await db.transaction((tx) => appendOutboxEvent(tx, taskEvent("ws_relay_ai", "t_relay_ai_1")));

    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });

    // Only the task event went through the generic relay.
    expect(genericPostCount).toBe(1);
    const [taskRow] = await readOutbox("ws_relay_ai", "task", "t_relay_ai_1");
    expect(taskRow.status).toBe("delivered");

    // The ai-initiative event is untouched (still pending) until its own relay runs.
    const [aiRow] = await readOutbox("ws_relay_ai", "ai_initiative", "init_relay_3");
    expect(aiRow.status).toBe("pending");
  });
});
