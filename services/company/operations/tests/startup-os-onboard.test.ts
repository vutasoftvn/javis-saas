import { describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  createOnboardSnapshot,
  getCurrentCompanyContext,
  getOnboardCadenceStatus,
  seedOnboardCadence,
  startOnboardSession,
  updateOnboardDimension,
} from "../handlers/onboard.handler";
import { getGoalTree } from "../handlers/goals.handler";
import {
  ONBOARD_DIMENSION_FIELDS,
  validateOnboardDimensionData,
} from "../services/onboard-dimension-fields";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";

// Startup OS Phase 3 (plan 2026-09-18): dữ liệu chiều onboarding phải khớp đúng
// field Company lưu, trạng thái độ tươi không được báo "tươi" khi chưa có dữ liệu,
// và agent chỉ gọi được qua delegation có đúng capability.

function delegationFor(userId: string, workspaceId: string, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${userId}`,
    workspace_id: workspaceId,
    run_id: "run-startup-os-1",
    capability_ids: capabilityIds,
  })}`;
}

async function startSession(ws: { workspaceId: string; bearerToken: string }): Promise<string> {
  const { sessionId } = await startOnboardSession({
    workspaceId: ws.workspaceId,
    sessionType: "initial",
    authorization: ws.bearerToken,
  });
  return sessionId;
}

describe("onboard dimension field contract", () => {
  it("covers exactly the 7 onboarding dimensions", () => {
    expect(Object.keys(ONBOARD_DIMENSION_FIELDS).sort()).toEqual(
      ["challenges", "founder", "goals_ambition", "identity", "market", "stage_scale", "team_culture"]
    );
  });

  it("rejects keys Company does not store instead of dropping them", () => {
    expect(() =>
      validateOnboardDimensionData("stage_scale", { arr: 150000, burn_rate_weekly: 5000 })
    ).toThrow(/unknown field\(s\) arr, burn_rate_weekly/);
  });

  it("rejects wrong types, out-of-range priorities and unknown enum values", () => {
    expect(() => validateOnboardDimensionData("stage_scale", { headcountFt: "8" })).toThrow(/integer/);
    expect(() => validateOnboardDimensionData("stage_scale", { stage: "growth" })).toThrow(/pre_pmf/);
    expect(() => validateOnboardDimensionData("challenges", { priorityMoney: 9 })).toThrow(/between 1 and 5/);
    expect(() => validateOnboardDimensionData("market", { competitors: [{ whyWinning: "x" }] })).toThrow(
      /name/
    );
  });

  it("requires founderName and at least one captured field", () => {
    expect(() => validateOnboardDimensionData("founder", { superpower: "sales" })).toThrow(/founderName/);
    expect(() => validateOnboardDimensionData("challenges", { notCaptured: ["x"] })).toThrow(
      /at least one field/
    );
    expect(() => validateOnboardDimensionData("unknown_dimension", { a: 1 })).toThrow(/không hợp lệ/);
  });

  it("accepts a well-formed payload", () => {
    const res = validateOnboardDimensionData("stage_scale", {
      headcountFt: 8,
      revenueArr: 150000,
      runwayMonths: 7.5,
      stage: "pre_pmf",
    });
    expect(res.dimension).toBe("stage_scale");
  });
});

describe("onboard dimension update endpoint", () => {
  it("returns invalid_argument for legacy snake_case keys and writes nothing", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const sessionId = await startSession(ws);

    await expect(
      updateOnboardDimension({
        dimension: "stage_scale",
        workspaceId: ws.workspaceId,
        sessionId,
        data: { arr: 150000, runway_weeks: 32 },
        authorization: ws.bearerToken,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    const ctx = await getCurrentCompanyContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    expect(ctx.fullContext.stage_scale).toBeNull();
  });

  it("serialises context with bigint ids and lets a snapshot be captured", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const sessionId = await startSession(ws);

    await updateOnboardDimension({
      dimension: "stage_scale",
      workspaceId: ws.workspaceId,
      sessionId,
      data: { headcountFt: 8, revenueArr: 150000, runwayMonths: 7.5, stage: "pre_pmf" },
      authorization: ws.bearerToken,
    });

    const ctx = await getCurrentCompanyContext({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    // Không ném "Do not know how to serialize a BigInt".
    const serialised = JSON.parse(JSON.stringify(ctx.fullContext));
    expect(serialised.stage_scale.stage).toBe("pre_pmf");
    expect(typeof serialised.stage_scale.id).toBe("string");
    expect(serialised.stage_scale.workspaceId).toBe(ws.workspaceId);

    const snapshot = await createOnboardSnapshot({
      workspaceId: ws.workspaceId,
      sessionId,
      changeReason: "test snapshot",
      changedDimensions: ["stage_scale"],
      authorization: ws.bearerToken,
    });
    expect(snapshot.snapshotId).toMatch(/^\d+$/);
  });
});

describe("onboard cadence status", () => {
  it("reports all 7 dimensions as never reviewed for a fresh workspace, even after seeding", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    const before = await getOnboardCadenceStatus({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    expect(before.cadences).toHaveLength(7);
    for (const c of before.cadences) {
      expect(c.neverReviewed).toBe(true);
      expect(c.daysSinceLastReview).toBeNull();
      expect(c.urgency).toBe("critical");
    }

    await seedOnboardCadence({ workspaceId: ws.workspaceId, authorization: ws.bearerToken });
    const afterSeed = await getOnboardCadenceStatus({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    expect(afterSeed.cadences.every((c) => c.neverReviewed)).toBe(true);
  });

  it("marks an updated dimension as reviewed and keeps its own cadence interval", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const sessionId = await startSession(ws);

    // Chưa seed: trước đây fallback gán 'fast'/14 ngày cho mọi chiều.
    await updateOnboardDimension({
      dimension: "identity",
      workspaceId: ws.workspaceId,
      sessionId,
      data: { whatTheyDo: "Kế toán AI cho SME", values: ["Minh bạch"] },
      authorization: ws.bearerToken,
    });

    const status = await getOnboardCadenceStatus({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    const identity = status.cadences.find((c) => c.dimension === "identity");
    expect(identity).toMatchObject({
      cadence: "slow",
      intervalDays: 180,
      neverReviewed: false,
      daysSinceLastReview: 0,
      urgency: "ok",
    });
    const market = status.cadences.find((c) => c.dimension === "market");
    expect(market?.neverReviewed).toBe(true);
  });
});

describe("startup OS agent delegation", () => {
  it("lets an agent read context and goals with the declared capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, [
      "startup_os.onboard.context_read",
      "startup_os.goal.tree_read",
    ]);

    await expect(
      getCurrentCompanyContext({ workspaceId: ws.workspaceId, authorization: token })
    ).resolves.toMatchObject({ workspaceId: ws.workspaceId });
    await expect(getGoalTree({ workspaceId: ws.workspaceId, authorization: token })).resolves.toBeDefined();
  });

  it("rejects an agent delegation that lacks the endpoint capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = delegationFor(ws.userId, ws.workspaceId, ["operations.task.list"]);

    await expect(
      getCurrentCompanyContext({ workspaceId: ws.workspaceId, authorization: token })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("never lets an agent write onboarding data beyond the delegating user's role", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "auditor" });
    const token = delegationFor(ws.userId, ws.workspaceId, ["startup_os.onboard.session_start"]);

    await expect(
      startOnboardSession({ workspaceId: ws.workspaceId, sessionType: "initial", authorization: token })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
