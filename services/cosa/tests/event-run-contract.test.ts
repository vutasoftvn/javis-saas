import { describe, it, expect, beforeEach } from "vitest";
import { scheduleTask } from "../services/control-plane-scheduler.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

const { scheduledTasks } = schema;

beforeEach(async () => {
  await db.delete(scheduledTasks);
});

describe("Event Run Contract & Coalescing (control-plane-scheduler)", () => {
  it("coalesces duplicate event + same rule and preserves original run_id", async () => {
    const key = "evt:ws_test:evt_100:rule_01";
    const initialPayload = {
      schema_version: 1,
      task_type: "run",
      run_id: "run_deterministic_001",
      workspace_id: "ws_test",
      event_id: "evt_100",
      trigger_rule_id: "rule_01",
      agent_profile: "customer_support_autopilot",
    };

    const first = await scheduleTask({
      targetSpecId: "cosa.agents.customer_support_autopilot",
      coalescingKey: key,
      inputPayload: initialPayload,
    });

    const second = await scheduleTask({
      targetSpecId: "cosa.agents.customer_support_autopilot",
      coalescingKey: key,
      inputPayload: {
        ...initialPayload,
        run_id: "run_attempt_002_should_not_override",
        extra_flag: true,
      },
    });

    // Must be the same task ID
    expect(second.id).toBe(first.id);

    // Exactly 1 row in DB
    const all = await db.select().from(scheduledTasks);
    expect(all.length).toBe(1);

    // run_id preserved
    const payload = all[0].inputPayload as Record<string, unknown>;
    expect(payload.run_id).toBe("run_deterministic_001");
    expect(payload.extra_flag).toBe(true);
  });

  it("schedules two distinct tasks when same event triggers two different rules", async () => {
    const keyRule1 = "evt:ws_test:evt_100:rule_copilot";
    const keyRule2 = "evt:ws_test:evt_100:rule_autopilot";

    const task1 = await scheduleTask({
      targetSpecId: "cosa.agents.customer_support",
      coalescingKey: keyRule1,
      inputPayload: {
        schema_version: 1,
        task_type: "run",
        run_id: "run_copilot_1",
        trigger_rule_id: "rule_copilot",
      },
    });

    const task2 = await scheduleTask({
      targetSpecId: "cosa.agents.customer_support_autopilot",
      coalescingKey: keyRule2,
      inputPayload: {
        schema_version: 1,
        task_type: "run",
        run_id: "run_autopilot_1",
        trigger_rule_id: "rule_autopilot",
      },
    });

    expect(task1.id).not.toBe(task2.id);

    const all = await db.select().from(scheduledTasks);
    expect(all.length).toBe(2);
    const keys = all.map((t) => t.coalescingKey);
    expect(keys).toContain(keyRule1);
    expect(keys).toContain(keyRule2);
  });

  it("does not create a duplicate task if event trigger is already processing or completed", async () => {
    const key = "evt:ws_test:evt_200:rule_01";
    const initialPayload = {
      schema_version: 1,
      task_type: "run",
      run_id: "run_initial_200",
      workspace_id: "ws_test",
      event_id: "evt_200",
      trigger_rule_id: "rule_01",
    };

    const first = await scheduleTask({
      targetSpecId: "cosa.agents.customer_support_autopilot",
      coalescingKey: key,
      inputPayload: initialPayload,
    });

    // Advance first task to completed
    await db
      .update(scheduledTasks)
      .set({ status: "completed", completedAt: new Date() })
      .where(eq(scheduledTasks.id, first.id));

    // Duplicate replay arrives
    const replay = await scheduleTask({
      targetSpecId: "cosa.agents.customer_support_autopilot",
      coalescingKey: key,
      inputPayload: {
        ...initialPayload,
        run_id: "run_replay_200",
      },
    });

    // Returns the existing completed task without inserting a new one
    expect(replay.id).toBe(first.id);
    expect(replay.status).toBe("completed");

    const all = await db.select().from(scheduledTasks);
    expect(all.length).toBe(1);
  });
});
