import { describe, it, expect } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  configureAutomationDefinition,
  publishAutomationRevision,
} from "../services/automation-definition.service";
import {
  createAutomationInvocation,
  getAutomationInvocation,
  cancelAutomationInvocation,
} from "../services/automation-invocation.service";

const KEY = "operating.weekly-review";

async function publishedDefinition(role = "founder") {
  const w = await createTestWorkspaceWithMember({ role });
  const c = await configureAutomationDefinition({
    workspaceId: w.workspaceId,
    authorization: w.bearerToken,
    automationKey: KEY,
    configuration: { projectId: "p1" },
    triggerContract: { kind: "manual" },
  });
  await publishAutomationRevision({
    workspaceId: w.workspaceId,
    authorization: w.bearerToken,
    definitionId: c.data.id!,
  });
  return { w, definitionId: c.data.id! };
}

async function outboxRowsFor(workspaceId: string, aggregateId: string) {
  return db
    .select()
    .from(schema.eventOutbox)
    .where(
      and(
        eq(schema.eventOutbox.workspaceId, workspaceId),
        eq(schema.eventOutbox.aggregateId, aggregateId)
      )
    );
}

describe("automation invocations — idempotent, outbox-only handoff", () => {
  it("creates one REQUESTED invocation + one signed outbox event", async () => {
    const { w, definitionId } = await publishedDefinition();
    const res = await createAutomationInvocation({
      workspaceId: w.workspaceId,
      authorization: w.bearerToken,
      definitionId,
      command: { triggerKind: "manual", clientRequestId: "req-1" },
    });
    expect(res.data.state).toBe("REQUESTED");
    expect(res.data.deduplicated).toBe(false);

    const rows = await outboxRowsFor(w.workspaceId, res.data.id);
    expect(rows).toHaveLength(1);
    const env = rows[0].envelope as any;
    expect(env.eventType).toBe("automation.invocation.requested.v1");
    // payload is exactly AutomationDispatchEnvelopeV1 — reference-only.
    expect(Object.keys(env.payload).sort()).toEqual(
      [
        "automation_key",
        "correlation_id",
        "invocation_id",
        "requested_at",
        "revision",
        "revision_hash",
        "schema_version",
        "trigger_identity",
        "trigger_kind",
        "workspace_id",
      ].sort()
    );
    for (const k of ["input_payload", "prompt", "credential", "authorization", "secret", "connector_grant"]) {
      expect(env.payload).not.toHaveProperty(k);
    }
  });

  it("a repeated manual request with the same clientRequestId returns the original, one event only", async () => {
    const { w, definitionId } = await publishedDefinition();
    const cmd = { triggerKind: "manual" as const, clientRequestId: "req-dup" };
    const a = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: cmd });
    const b = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: cmd });
    expect(b.data.id).toBe(a.data.id);
    expect(b.data.deduplicated).toBe(true);
    const rows = await outboxRowsFor(w.workspaceId, a.data.id);
    expect(rows).toHaveLength(1);
  });

  it("the same idempotency key with a changed fingerprint is rejected", async () => {
    const { w, definitionId } = await publishedDefinition();
    await createAutomationInvocation({
      workspaceId: w.workspaceId,
      authorization: w.bearerToken,
      definitionId,
      command: { triggerKind: "manual", clientRequestId: "req-x", businessScope: { a: 1 } },
    });
    await expect(
      createAutomationInvocation({
        workspaceId: w.workspaceId,
        authorization: w.bearerToken,
        definitionId,
        command: { triggerKind: "manual", clientRequestId: "req-x", businessScope: { a: 2 } },
      })
    ).rejects.toThrow(/different fingerprint/);
  });

  it("a deliberate rerun uses a new clientRequestId and creates a second invocation", async () => {
    const { w, definitionId } = await publishedDefinition();
    const a = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: { triggerKind: "manual", clientRequestId: "run-a" } });
    const b = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: { triggerKind: "manual", clientRequestId: "run-b" } });
    expect(b.data.id).not.toBe(a.data.id);
  });

  it("a SUSPENDED definition creates no invocation and no event", async () => {
    const { w, definitionId } = await publishedDefinition();
    const { suspendAutomationDefinition } = await import("../services/automation-definition.service");
    await suspendAutomationDefinition({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId });
    await expect(
      createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: { triggerKind: "manual", clientRequestId: "r" } })
    ).rejects.toThrow(/SUSPENDED/);
  });

  it("cancel before dispatch → CANCELLED with an optimistic version bump", async () => {
    const { w, definitionId } = await publishedDefinition();
    const inv = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: { triggerKind: "manual", clientRequestId: "c1" } });
    const cancelled = await cancelAutomationInvocation({
      workspaceId: w.workspaceId,
      authorization: w.bearerToken,
      invocationId: inv.data.id,
      expectedVersion: inv.data.version,
    });
    expect(cancelled.data.state).toBe("CANCELLED");
    expect(cancelled.data.version).toBe(inv.data.version + 1);
  });

  it("cancel with a stale expectedVersion is aborted", async () => {
    const { w, definitionId } = await publishedDefinition();
    const inv = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: { triggerKind: "manual", clientRequestId: "c2" } });
    await expect(
      cancelAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, invocationId: inv.data.id, expectedVersion: 999 })
    ).rejects.toThrow(/version conflict/);
  });

  it("a foreign workspace gets no invocation detail", async () => {
    const { w, definitionId } = await publishedDefinition();
    const other = await createTestWorkspaceWithMember({ role: "founder" });
    const inv = await createAutomationInvocation({ workspaceId: w.workspaceId, authorization: w.bearerToken, definitionId, command: { triggerKind: "manual", clientRequestId: "c3" } });
    await expect(
      getAutomationInvocation({ workspaceId: w.workspaceId, authorization: other.bearerToken, invocationId: inv.data.id })
    ).rejects.toThrow();
  });
});
