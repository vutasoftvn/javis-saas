import { describe, it, expect } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { createTestWorkspaceWithMember } from "./_helpers";
import { configureAutomationDefinition } from "../services/automation-definition.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

// Composite (id, workspace_id) FKs (migration 042): the database itself must reject a
// child row that points at a parent of another workspace, even though the plain id FK
// (migration 041) alone would accept it.
async function definitionIn(w: { workspaceId: string; bearerToken: string }) {
  const c = await configureAutomationDefinition({
    workspaceId: w.workspaceId,
    authorization: w.bearerToken,
    automationKey: "operating.weekly-review",
    configuration: { projectId: "p1" },
    triggerContract: { kind: "manual" },
  });
  return c.data.id!;
}

async function expectFkViolation(p: Promise<unknown>, constraint: string) {
  const err = await p.then(
    () => null,
    (e: unknown) => e as { cause?: { code?: string; constraint?: string }; code?: string; constraint?: string }
  );
  expect(err, "insert must be rejected").not.toBeNull();
  const pg = err!.cause ?? err!;
  expect(pg.code).toBe("23503");
  expect(pg.constraint).toBe(constraint);
}

describe("automation tenancy — composite FKs", () => {
  it("rejects a revision in workspace B that points at a definition of workspace A", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const b = await createTestWorkspaceWithMember({ role: "founder" });
    const defA = await definitionIn(a);
    await expectFkViolation(
      db.execute(sql`
        INSERT INTO operating.automation_revisions
          (id, workspace_id, definition_id, revision_no, revision_hash, created_by)
        VALUES (${generateSnowflake()}, ${BigInt(b.workspaceId)}, ${BigInt(defA)}, 77, 'h', 'test')`),
      "fk_automation_revisions_definition_ws"
    );
  });

  it("accepts the same revision inside the owning workspace", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const defA = await definitionIn(a);
    await db.execute(sql`
      INSERT INTO operating.automation_revisions
        (id, workspace_id, definition_id, revision_no, revision_hash, created_by)
      VALUES (${generateSnowflake()}, ${BigInt(a.workspaceId)}, ${BigInt(defA)}, 78, 'h', 'test')`);
  });

  it("rejects an invocation event whose invocation belongs to another workspace", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const b = await createTestWorkspaceWithMember({ role: "founder" });
    const defA = await definitionIn(a);
    const revId = generateSnowflake();
    const invId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO operating.automation_revisions (id, workspace_id, definition_id, revision_no, revision_hash, created_by)
      VALUES (${revId}, ${BigInt(a.workspaceId)}, ${BigInt(defA)}, 77, 'h', 'test')`);
    await db.execute(sql`
      INSERT INTO operating.automation_invocations
        (id, workspace_id, definition_id, revision_id, automation_key, revision_no, revision_hash, idempotency_key,
         trigger_kind, trigger_identity, caller_principal, source, fingerprint_hash, correlation_id)
      VALUES (${invId}, ${BigInt(a.workspaceId)}, ${BigInt(defA)}, ${revId}, 'k', 77, 'h', 'idem',
              'manual', 't', 'u', 'manual', 'f', 'c')`);
    await expectFkViolation(
      db.execute(sql`
        INSERT INTO operating.automation_invocation_events (id, workspace_id, invocation_id, seq, event_type)
        VALUES (${generateSnowflake()}, ${BigInt(b.workspaceId)}, ${invId}, 1, 'x')`),
      "fk_automation_invocation_events_invocation_ws"
    );
  });
});
