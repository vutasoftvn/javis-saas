import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { createOkrCycle, createObjective, addKeyResult, checkin, getObjectiveProgress, getObjective, publishObjective, updateObjective, updateKeyResult, deleteKeyResult, listKeyResults } from "../handlers/okr.handler";
import { createProject } from "../handlers/project.handler";
import { countOutbox } from "./helpers/outbox";

async function makeCycle() {
  const user = await createTestSession({
    email: `okr-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "OKR Test",
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  // Startup Core: createTestSession seed sẵn một project (id === workspaceId).
  const workspace = { id: user.workspaceId, projectId: user.projectId };
  const cycle = await createOkrCycle({ workspaceId: workspace.id, name: "Q1", authorization });
  return { workspace, cycle, authorization };
}

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  const authorization = `Bearer ${user.accessToken}`;
  // Startup Core: createTestSession seed sẵn một project (id === workspaceId).
  return { workspaceId: user.workspaceId, userId: user.userId, authorization, projectId: user.projectId };
}

describe("createOkrCycle", () => {
  it("creates a cycle with the default draft status", async () => {
    const { cycle } = await makeCycle();
    expect(cycle.id).toBeTruthy();
    expect(typeof cycle.id).toBe("string");
    expect(cycle.status).toBe("draft");
  });

  it("rejects a cycle for a workspace that doesn't exist", async () => {
    await expect(createOkrCycle({ workspaceId: "999999999", name: "Bad" })).rejects.toThrow();
  });

  it("M1 §4: rejects cycle creation without authorization", async () => {
    const { workspaceId } = await makeAuthedWorkspace("OKR No Auth");
    await expect(createOkrCycle({ workspaceId, name: "Q1" })).rejects.toThrow();
  });

  it("M1 §4: rejects cycle creation by a non-member of the workspace", async () => {
    const victim = await makeAuthedWorkspace("OKR Victim");
    const attacker = await makeAuthedWorkspace("OKR Attacker");
    await expect(
      createOkrCycle({ workspaceId: victim.workspaceId, name: "Q1", authorization: attacker.authorization }),
    ).rejects.toThrow();
  });
});

describe("createObjective", () => {
  it("creates an objective under a cycle", async () => {
    const { workspace, cycle, authorization } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue", authorization });
    expect(objective.id).toBeTruthy();
    expect(typeof objective.id).toBe("string");
    // Startup Core: Objective gắn project qua `okr_objectives.project_id`. cycleId
    // được validate lúc tạo nhưng không lưu trên objective (không có cột cycle_id).
    expect(objective.projectId).toBeTruthy();
    expect(typeof objective.projectId).toBe("string");
  });

  it("rejects an objective under a cycle that doesn't exist (real DB FK)", async () => {
    const { workspace, authorization } = await makeCycle();
    await expect(
      createObjective({ workspaceId: workspace.id, cycleId: "999999999", title: "Orphan", authorization })
    ).rejects.toThrow();
  });
});

describe("addKeyResult + checkin + getObjectiveProgress", () => {
  it("updates and soft-deletes a key result only within the caller workspace", async () => {
    const owner = await makeAuthedWorkspace("OKR Edit Owner");
    const outsider = await makeAuthedWorkspace("OKR Edit Outsider");
    const cycle = await createOkrCycle({ workspaceId: owner.workspaceId, name: "Q1", authorization: owner.authorization });
    const objective = await createObjective({
      workspaceId: owner.workspaceId,
      cycleId: cycle.id,
      title: "Retain customers",
      authorization: owner.authorization,
    });
    const keyResult = await addKeyResult({
      objectiveId: objective.id,
      title: "Monthly churn",
      targetValue: 5,
      baselineValue: 10,
      authorization: owner.authorization,
    });

    const renamed = await updateObjective({
      id: objective.id,
      title: "Retain more customers",
      authorization: owner.authorization,
    });
    expect(renamed.title).toBe("Retain more customers");

    const updated = await updateKeyResult({
      id: keyResult.id,
      currentValue: 7.5,
      targetValue: 4.5,
      authorization: owner.authorization,
    });
    expect(updated.currentValue).toBe(7.5);
    expect(updated.targetValue).toBe(4.5);

    const listed = await listKeyResults({
      workspaceId: owner.workspaceId,
      authorization: owner.authorization,
    });
    expect(listed.data.map((keyResult) => keyResult.id)).toContain(keyResult.id);

    await expect(
      updateKeyResult({ id: keyResult.id, currentValue: 6, authorization: outsider.authorization }),
    ).rejects.toThrow();

    await deleteKeyResult({ id: keyResult.id, authorization: owner.authorization });
    await expect(checkin({ id: keyResult.id, value: 4, authorization: owner.authorization })).rejects.toThrow();
  });

  it("does not allow a fourth KR to be added after an objective is published", async () => {
    const { workspace, cycle, authorization } = await makeCycle();
    const objective = await createObjective({
      workspaceId: workspace.id,
      cycleId: cycle.id,
      title: "Keep published OKR measurable",
      authorization,
    });

    for (let index = 1; index <= 3; index += 1) {
      await addKeyResult({
        objectiveId: objective.id,
        title: `KR ${index}`,
        targetValue: index * 10,
        baselineValue: 0,
        authorization,
      });
    }

    await publishObjective({
      id: objective.id,
      workspaceId: workspace.id,
      authorization,
    });

    await expect(
      addKeyResult({
        objectiveId: objective.id,
        title: "KR 4 must be rejected",
        targetValue: 40,
        authorization,
      })
    ).rejects.toThrow("Objective already has the maximum of 3 Key Results");
  });

  it("scores an objective from its key results after check-ins", async () => {
    const { workspace, cycle, authorization } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Grow revenue", authorization });
    const kr1 = await addKeyResult({ objectiveId: objective.id, title: "Sign 10 customers", targetValue: 10, authorization });
    const kr2 = await addKeyResult({ objectiveId: objective.id, title: "Reach $10k MRR", targetValue: 10000, authorization });

    await checkin({ id: kr1.id, value: 5, authorization });
    await checkin({ id: kr2.id, value: 10000, authorization });

    const progress = await getObjectiveProgress({ id: objective.id, authorization, workspaceId: workspace.id });
    expect(progress.score).toBeCloseTo(0.75);
    expect(progress.keyResults).toHaveLength(2);
  });

  it("scores a LINEAR_DECREASE key result by progress toward baseline, not the raw current/target ratio (IA22)", async () => {
    const { workspace, cycle, authorization } = await makeCycle();
    const objective = await createObjective({ workspaceId: workspace.id, cycleId: cycle.id, title: "Reduce churn", authorization });

    // Mục tiêu GIẢM churn từ 10 xuống 5. Hiện tại 8 -> tiến bộ thật = (10-8)/(10-5) = 0.4.
    // Công thức cũ (current/target = 8/5, clamp 1) sẽ cho điểm 1 (sai — coi như đã đạt mục tiêu).
    const kr = await addKeyResult({
      objectiveId: objective.id,
      title: "Monthly churn rate",
      targetValue: 5,
      baselineValue: 10,
      scoringType: "LINEAR_DECREASE",
      authorization,
    });
    expect(kr.baselineValue).toBe(10);
    expect(kr.scoringType).toBe("LINEAR_DECREASE");

    await checkin({ id: kr.id, value: 8, authorization });

    const progress = await getObjectiveProgress({ id: objective.id, authorization, workspaceId: workspace.id });
    expect(progress.keyResults).toHaveLength(1);
    expect(progress.keyResults[0]!.score).toBeCloseTo(0.4);
    expect(progress.score).toBeCloseTo(0.4);
  });

  it("getObjectiveProgress is a pure read — emits zero events", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("OKR Read Purity Inc");
    const cycle = await createOkrCycle({ workspaceId, name: "Q1", authorization });
    const objective = await createObjective({ workspaceId, cycleId: cycle.id, title: "Pure read objective", authorization });
    await addKeyResult({ objectiveId: objective.id, title: "KR 1", targetValue: 10, authorization });

    const before = await countOutbox(workspaceId);
    await getObjectiveProgress({ id: objective.id, authorization, workspaceId });
    const after = await countOutbox(workspaceId);
    expect(after).toBe(before);
  });
});

describe("getObjective", () => {
  it("member fetches their objective and projectId is populated from the direct column", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Get Objective Test");
    const cycle = await createOkrCycle({ workspaceId, name: "Q1", authorization });
    const project = await createProject({ workspaceId, title: "Linked Project", authorization });
    // Startup Core: objective thuộc đúng một project qua `okr_objectives.project_id`.
    const objective = await createObjective({
      workspaceId,
      cycleId: cycle.id,
      projectId: project.id,
      title: "Objective with project",
      authorization,
    });

    const fetched = await getObjective({ id: objective.id, authorization });
    expect(fetched.id).toBe(objective.id);
    expect(fetched.projectId).toBe(project.id);
    expect(fetched.projectIds).toEqual([project.id]);
  });

  it("non-member is rejected when fetching an objective from another workspace", async () => {
    const workspace1 = await makeAuthedWorkspace("Get Objective W1");
    const workspace2 = await makeAuthedWorkspace("Get Objective W2");

    const cycle = await createOkrCycle({ workspaceId: workspace1.workspaceId, name: "Q1", authorization: workspace1.authorization });
    const objective = await createObjective({
      workspaceId: workspace1.workspaceId,
      cycleId: cycle.id,
      title: "Private Objective",
      authorization: workspace1.authorization,
    });

    // Try to fetch objective from W1 using W2 member credentials
    await expect(getObjective({ id: objective.id, authorization: workspace2.authorization })).rejects.toThrow();
  });
});
