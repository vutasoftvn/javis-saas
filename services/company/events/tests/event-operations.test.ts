import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { db } from "../../operations/db";
import { makeAuthedWorkspace } from "../../operations/tests/helpers/workspace";
import { readOutbox } from "../../operations/tests/helpers/outbox";
import { pruneDeliveredOutbox } from "../../shared/events/outbox.repository";
import { listOutbox, retryOutbox, lastAudit } from "../services/event-operations.service";

async function seedDeadLetter(workspaceId: string, aggregateId: string) {
  const eventId = randomUUID();
  await db.execute(sql`
    INSERT INTO integration.event_outbox (
      event_id, workspace_id, aggregate_type, aggregate_id,
      event_type, schema_version, occurred_at, envelope,
      payload_hash, classification, status, attempt_count,
      max_attempts, dead_letter_reason
    ) VALUES (
      ${eventId}::uuid, ${workspaceId}, 'task', ${aggregateId},
      'operations.task.created.v1', 1, now(), '{"dummy": true}'::jsonb,
      'dummyhash', 'internal', 'dead', 8,
      8, 'Exceeded maximum attempts'
    );
  `);
  return { eventId };
}

async function seedDelivered(workspaceId: string, aggregateId: string, opts: { ageDays: number }) {
  const eventId = randomUUID();
  await db.execute(sql`
    INSERT INTO integration.event_outbox (
      event_id, workspace_id, aggregate_type, aggregate_id,
      event_type, schema_version, occurred_at, envelope,
      payload_hash, classification, status, attempt_count,
      max_attempts, delivered_at
    ) VALUES (
      ${eventId}::uuid, ${workspaceId}, 'task', ${aggregateId},
      'operations.task.created.v1', 1, now() - (${opts.ageDays} || ' days')::interval, '{"dummy": true}'::jsonb,
      'dummyhash', 'internal', 'delivered', 1,
      8, now() - (${opts.ageDays} || ' days')::interval
    );
  `);
  return { eventId };
}

async function readOutboxByEventId(eventId: string) {
  const res = await db.execute(sql`
    SELECT
      event_id as "eventId",
      workspace_id as "workspaceId",
      status,
      attempt_count as "attemptCount",
      last_error as "lastError",
      dead_letter_reason as "deadLetterReason"
    FROM integration.event_outbox
    WHERE event_id = ${eventId}::uuid;
  `);
  return (res as any).rows as any[];
}

describe("event operations API", () => {
  it("hides DLQ from a non-member of the workspace", async () => {
    const a = await makeAuthedWorkspace("Ops A");
    const b = await makeAuthedWorkspace("Ops B");
    await seedDeadLetter(a.workspaceId, "t_x");
    await expect(listOutbox({ workspaceId: a.workspaceId, status: "dead", authorization: b.authorization }))
      .rejects.toThrow(/không thuộc workspace|not found|forbidden|permission denied|unauthorized/i);
  });

  it("does not let workspace B retry a workspace A event", async () => {
    const a = await makeAuthedWorkspace("Ops A2");
    const b = await makeAuthedWorkspace("Ops B2");
    const { eventId } = await seedDeadLetter(a.workspaceId, "t_y");
    await expect(retryOutbox({ eventId, workspaceId: b.workspaceId, authorization: b.authorization }))
      .rejects.toThrow(/không thuộc workspace|not found|forbidden|permission denied|unauthorized/i);
  });

  it("summarises a dead-letter row without envelope or payload", async () => {
    const a = await makeAuthedWorkspace("Ops A3");
    const { eventId } = await seedDeadLetter(a.workspaceId, "t_z");
    const { items } = await listOutbox({ workspaceId: a.workspaceId, status: "dead", authorization: a.authorization });
    const row = items.find((i) => i.eventId === eventId)!;
    expect(row).toBeDefined();
    expect(row).not.toHaveProperty("envelope");
    expect(row).not.toHaveProperty("payload");
    expect(row.deadLetterReason).toBeTruthy();
  });

  it("requeues a dead-letter event and writes a typed audit record", async () => {
    const a = await makeAuthedWorkspace("Ops A4");
    const { eventId } = await seedDeadLetter(a.workspaceId, "t_w");
    await retryOutbox({ eventId, workspaceId: a.workspaceId, authorization: a.authorization });
    const [row] = await readOutboxByEventId(eventId);
    expect(row.status).toBe("pending");
    expect(await lastAudit(a.workspaceId, "event.outbox.retry")).toMatchObject({ eventId });
  });

  it("prune removes delivered rows older than 30d, never dead rows", async () => {
    const a = await makeAuthedWorkspace("Ops A5");
    await seedDelivered(a.workspaceId, "t_old", { ageDays: 40 });
    await seedDeadLetter(a.workspaceId, "t_keep");
    const removed = await pruneDeliveredOutbox(30);
    expect(removed).toBeGreaterThanOrEqual(1);
    expect((await readOutbox(a.workspaceId, "task", "t_keep"))[0].status).toBe("dead");
  });
});
