import { describe, it, expect, beforeEach } from "vitest";
import * as childSvc from "../services/child-scheduler.service";
import { db, schema } from "../models/db";

const { scheduledTasks } = schema;

beforeEach(async () => {
  await db.delete(scheduledTasks);
});

function child(parent: string, id: string, deps: string[] = []) {
  return {
    parentTaskId: parent,
    childId: id,
    targetSpecId: "cosa.agent",
    inputPayload: { kind: "event_trigger", child_id: id },
    dependsOn: deps,
    joinPolicy: "all" as const,
  };
}

describe("child-scheduler (P1 Task 7 durable supervisor)", () => {
  it("schedules independent children as 'scheduled'", async () => {
    const p = "sup_1";
    await childSvc.scheduleChildTask(child(p, "c0"));
    await childSvc.scheduleChildTask(child(p, "c1"));
    const rows = await childSvc.listChildren(p);
    expect(rows.map((r) => r.status).sort()).toEqual(["scheduled", "scheduled"]);
  });

  it("creates a child with unmet depends_on as 'blocked', unblocks on parent completion", async () => {
    const p = "sup_2";
    await childSvc.scheduleChildTask(child(p, "a"));
    await childSvc.scheduleChildTask(child(p, "b", ["a"]));
    expect((await childSvc.listChildren(p)).find((r) => r.childId === "b")!.status).toBe("blocked");

    await childSvc.completeChild({ parentTaskId: p, childId: "a", result: { ok: 1 }, idempotencyKey: "ka" });
    expect((await childSvc.listChildren(p)).find((r) => r.childId === "b")!.status).toBe("scheduled");
  });

  it("completeChild is idempotent on the same idempotencyKey (no re-apply)", async () => {
    const p = "sup_3";
    await childSvc.scheduleChildTask(child(p, "c0"));
    const first = await childSvc.completeChild({ parentTaskId: p, childId: "c0", result: { n: 1 }, idempotencyKey: "k0" });
    const second = await childSvc.completeChild({ parentTaskId: p, childId: "c0", result: { n: 2 }, idempotencyKey: "k0" });
    expect(first).toEqual({ ok: true, deduped: false });
    expect(second).toEqual({ ok: true, deduped: true });
    expect((await childSvc.listChildren(p)).find((r) => r.childId === "c0")!.result).toEqual({ n: 1 });
  });

  it("resolveJoin('all') satisfied only when every child completed", async () => {
    const p = "sup_4";
    for (const id of ["c0", "c1", "c2"]) await childSvc.scheduleChildTask(child(p, id));
    await childSvc.completeChild({ parentTaskId: p, childId: "c0", result: {}, idempotencyKey: "k0" });
    expect((await childSvc.resolveJoin(p)).satisfied).toBe(false);
    await childSvc.completeChild({ parentTaskId: p, childId: "c1", result: {}, idempotencyKey: "k1" });
    await childSvc.completeChild({ parentTaskId: p, childId: "c2", result: {}, idempotencyKey: "k2" });
    const j = await childSvc.resolveJoin(p);
    expect(j.satisfied).toBe(true);
    expect(j.completed.sort()).toEqual(["c0", "c1", "c2"]);
  });

  it("resolveJoin('quorum', 2) satisfied at 2 of 3", async () => {
    const p = "sup_5";
    for (const id of ["c0", "c1", "c2"]) {
      await childSvc.scheduleChildTask({ ...child(p, id), joinPolicy: "quorum", joinQuorum: 2 });
    }
    await childSvc.completeChild({ parentTaskId: p, childId: "c0", result: {}, idempotencyKey: "k0" });
    expect((await childSvc.resolveJoin(p)).satisfied).toBe(false);
    await childSvc.completeChild({ parentTaskId: p, childId: "c1", result: {}, idempotencyKey: "k1" });
    expect((await childSvc.resolveJoin(p)).satisfied).toBe(true);
  });

  it("schedule is idempotent on (parent_task_id, child_id)", async () => {
    const p = "sup_6";
    const a = await childSvc.scheduleChildTask(child(p, "c0"));
    const b = await childSvc.scheduleChildTask(child(p, "c0"));
    expect(a.scheduledTaskId).toBe(b.scheduledTaskId);
    expect((await childSvc.listChildren(p)).length).toBe(1);
  });
});
