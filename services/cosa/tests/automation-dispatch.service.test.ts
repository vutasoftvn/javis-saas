import { describe, it, expect, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import * as autoDispatch from "../services/automation-dispatch.service";
import * as schedulerSvc from "../services/control-plane-scheduler.service";
import { db, schema } from "../models/db";

const { scheduledTasks } = schema;

function envelope(over: Partial<autoDispatch.AutomationDispatchEnvelope> = {}): autoDispatch.AutomationDispatchEnvelope {
  return {
    schema_version: 1,
    invocation_id: `inv_${Math.random().toString(36).slice(2)}`,
    workspace_id: "ws_1",
    automation_key: "operating.weekly-review",
    revision: 1,
    revision_hash: "a".repeat(64),
    trigger_kind: "manual",
    trigger_identity: "req-1",
    correlation_id: "corr_1",
    requested_at: new Date().toISOString(),
    ...over,
  };
}

beforeEach(async () => {
  await db.delete(scheduledTasks);
  await db.execute(sql`DELETE FROM control_plane.automation_dispatches`);
});

describe("automation dispatch — opaque projection + fenced completion", () => {
  it("records one dispatch row and one automation_run task", async () => {
    const env = envelope();
    const row = await autoDispatch.scheduleAutomationDispatch(env);
    expect(row.state).toBe("scheduled");
    expect(row.taskId).toBeTruthy();

    const [task] = await db.select().from(scheduledTasks);
    expect((task.inputPayload as any).task_type).toBe("automation_run");
    expect((task.inputPayload as any).invocation_id).toBe(env.invocation_id);
    expect(task.coalescingKey).toBe(`evt:automation:${env.invocation_id}`);
    // payload carries no business content
    for (const k of ["prompt", "input_payload", "credential"]) {
      expect((task.inputPayload as any)[k]).toBeUndefined();
    }
  });

  it("is idempotent on invocation_id — a re-delivery returns the same task", async () => {
    const env = envelope();
    const a = await autoDispatch.scheduleAutomationDispatch(env);
    const b = await autoDispatch.scheduleAutomationDispatch(env);
    expect(b.taskId).toBe(a.taskId);
    const tasks = await db.select().from(scheduledTasks);
    expect(tasks).toHaveLength(1);
  });

  it("rejects an envelope carrying a forbidden key", async () => {
    await expect(
      autoDispatch.recordAutomationDispatch({ ...envelope(), prompt: "x" } as any)
    ).rejects.toThrow(/must not carry 'prompt'/);
  });

  it("completeAutomationDispatch is fenced on (taskId, claimToken)", async () => {
    const env = envelope();
    const row = await autoDispatch.scheduleAutomationDispatch(env);
    const [claimed] = await schedulerSvc.pollDueTasks({ workerId: "worker_A", visibilityTimeoutSec: 30 });
    await autoDispatch.markAutomationDispatchClaimed(env.invocation_id, claimed.id, claimed.claimToken!);

    // wrong claim token -> rejected, no terminal mutation
    const stale = await autoDispatch.completeAutomationDispatch({
      invocationId: env.invocation_id,
      taskId: claimed.id,
      claimToken: "claim_wrong",
      success: true,
    });
    expect(stale.ok).toBe(false);
    expect((await autoDispatch.getAutomationDispatch(env.invocation_id))!.state).toBe("claimed");

    // correct token -> one terminal transition
    const ok = await autoDispatch.completeAutomationDispatch({
      invocationId: env.invocation_id,
      taskId: claimed.id,
      claimToken: claimed.claimToken!,
      success: true,
    });
    expect(ok.ok).toBe(true);
    expect((await autoDispatch.getAutomationDispatch(env.invocation_id))!.state).toBe("completed");

    // a second completion cannot flip it again
    const again = await autoDispatch.completeAutomationDispatch({
      invocationId: env.invocation_id,
      taskId: claimed.id,
      claimToken: claimed.claimToken!,
      success: false,
      error: "late",
    });
    expect(again.ok).toBe(false);
    expect((await autoDispatch.getAutomationDispatch(env.invocation_id))!.state).toBe("completed");
  });
});
