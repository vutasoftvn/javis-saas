import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { db, schema } from "../../models/db";
import { eq, and } from "drizzle-orm";
import {
  buildCycleReviewSchedule,
  listCycleReviewsService,
  getCycleReviewService,
  startCycleReviewService,
  createCustomMidCycleReviewService,
  updateCycleReviewService,
  closeCycleReviewService,
} from "../services/cycle-review.service";
import {
  createCycleService,
  updateCycleService,
} from "../../services/twelve-week-year.service";
import {
  updateWorkspaceStrategySettings,
} from "../services/workspace-strategy-settings.service";
import {
  createStrategicObjective,
} from "../services/strategic-objective.service";
import {
  createInitiativeService,
} from "../../services/initiative.service";
import {
  getLocalDateFromInstant,
  resolveExecutionWeek,
} from "../../services/execution-calendar";

const { cycleReviews, cycleRevisions, pestelSignals, decisionRecords } = schema;

function createMockTenantContext(
  overrides: Partial<TenantContext> & {
    workspaceId: string;
    userId: string;
    membershipRole: string;
    actorKind?: string;
    isAgent?: boolean;
  }
): TenantContext {
  return {
    permissions: [],
    correlationId: "test-corr-id",
    ...overrides,
  } as any;
}

describe("Cycle Reviews Governance & Lifecycle (Task 8)", () => {
  describe("buildCycleReviewSchedule (Deterministic schedule calculation)", () => {
    it("builds 1-week schedule: WEEKLY + END_CYCLE only (no mid-cycle)", () => {
      const schedule = buildCycleReviewSchedule(1, "AUTO");
      expect(schedule).toHaveLength(2);
      expect(schedule[0]).toEqual({ kind: "WEEKLY", scheduledWeekNo: 1 });
      expect(schedule[1]).toEqual({ kind: "END_CYCLE", scheduledWeekNo: 1 });
    });

    it("builds 3-week schedule: WEEKLY(1..3) + END_CYCLE(3), no mid-cycle", () => {
      const schedule = buildCycleReviewSchedule(3, "AUTO");
      expect(schedule).toHaveLength(4);
      expect(schedule.filter((s) => s.kind === "WEEKLY")).toHaveLength(3);
      expect(schedule.filter((s) => s.kind === "MID_CYCLE")).toHaveLength(0);
      expect(schedule.find((s) => s.kind === "END_CYCLE")).toEqual({
        kind: "END_CYCLE",
        scheduledWeekNo: 3,
      });
    });

    it("builds 4-week schedule with AUTO policy: MID_CYCLE at week 2", () => {
      const schedule = buildCycleReviewSchedule(4, "AUTO");
      expect(schedule).toHaveLength(6);
      expect(schedule.find((s) => s.kind === "MID_CYCLE")).toEqual({
        kind: "MID_CYCLE",
        scheduledWeekNo: 2, // Math.ceil(4/2) = 2
      });
      expect(schedule.find((s) => s.kind === "END_CYCLE")).toEqual({
        kind: "END_CYCLE",
        scheduledWeekNo: 4,
      });
    });

    it("builds 8-week schedule with AUTO policy: MID_CYCLE at week 4", () => {
      const schedule = buildCycleReviewSchedule(8, "AUTO");
      expect(schedule).toHaveLength(10);
      expect(schedule.find((s) => s.kind === "MID_CYCLE")).toEqual({
        kind: "MID_CYCLE",
        scheduledWeekNo: 4, // Math.ceil(8/2) = 4
      });
      expect(schedule.find((s) => s.kind === "END_CYCLE")).toEqual({
        kind: "END_CYCLE",
        scheduledWeekNo: 8,
      });
    });

    it("builds 10-week schedule with AUTO policy: MID_CYCLE at week 5", () => {
      const schedule = buildCycleReviewSchedule(10, "AUTO");
      expect(schedule).toHaveLength(12);
      expect(schedule.find((s) => s.kind === "MID_CYCLE")).toEqual({
        kind: "MID_CYCLE",
        scheduledWeekNo: 5, // Math.ceil(10/2) = 5
      });
      expect(schedule.find((s) => s.kind === "END_CYCLE")).toEqual({
        kind: "END_CYCLE",
        scheduledWeekNo: 10,
      });
    });

    it("builds 16-week schedule with AUTO policy: MID_CYCLE at week 8", () => {
      const schedule = buildCycleReviewSchedule(16, "AUTO");
      expect(schedule).toHaveLength(18);
      expect(schedule.find((s) => s.kind === "MID_CYCLE")).toEqual({
        kind: "MID_CYCLE",
        scheduledWeekNo: 8, // Math.ceil(16/2) = 8
      });
      expect(schedule.find((s) => s.kind === "END_CYCLE")).toEqual({
        kind: "END_CYCLE",
        scheduledWeekNo: 16,
      });
    });

    it("builds schedules with CUSTOM or OFF policy: never auto-schedules MID_CYCLE", () => {
      const customSchedule = buildCycleReviewSchedule(10, "CUSTOM");
      expect(customSchedule).toHaveLength(11);
      expect(customSchedule.filter((s) => s.kind === "MID_CYCLE")).toHaveLength(0);

      const offSchedule = buildCycleReviewSchedule(10, "OFF");
      expect(offSchedule).toHaveLength(11);
      expect(offSchedule.filter((s) => s.kind === "MID_CYCLE")).toHaveLength(0);
    });

    it("rejects invalid durationWeeks", () => {
      expect(() => buildCycleReviewSchedule(0, "AUTO")).toThrow();
      expect(() => buildCycleReviewSchedule(-5, "AUTO")).toThrow();
    });
  });

  describe("Cycle creation and timezone-safe review scheduling", () => {
    it("schedules initial reviews on cycle creation with timezone-safe dates", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 10,
        startLocalDate: "2026-09-07",
        timezone: "Asia/Ho_Chi_Minh",
        displayName: "Q4 Execution Cycle",
      });

      const reviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));
      expect(reviews).toHaveLength(12);

      const midReview = reviews.find((r) => r.kind === "MID_CYCLE");
      expect(midReview).toBeDefined();
      expect(midReview!.scheduledWeekNo).toBe(5);
      expect(midReview!.status).toBe("SCHEDULED");

      const endReview = reviews.find((r) => r.kind === "END_CYCLE");
      expect(endReview).toBeDefined();
      expect(endReview!.scheduledWeekNo).toBe(10);
      expect(endReview!.status).toBe("SCHEDULED");

      // Verify timezone-safe dates roundtrip through calendar helper
      for (const r of reviews) {
        expect(r.scheduledAt).not.toBeNull();
        const localDate = getLocalDateFromInstant(new Date(r.scheduledAt!), "Asia/Ho_Chi_Minh");
        const resolvedWeek = resolveExecutionWeek("2026-09-07", 10, localDate);
        expect(resolvedWeek).toBe(r.scheduledWeekNo);
      }
    });
  });

  describe("Cycle resize and rescheduling reviews", () => {
    it("preserves completed reviews, supersedes obsolete slots, and logs schedule in cycle revision", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 10,
        startLocalDate: "2026-09-07",
        timezone: "Asia/Ho_Chi_Minh",
      });

      const initialReviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));
      const week1Review = initialReviews.find((r) => r.kind === "WEEKLY" && r.scheduledWeekNo === 1)!;

      // Start and complete week 1 review
      await startCycleReviewService(ctx, BigInt(week1Review.id));
      const completedW1 = await closeCycleReviewService(ctx, BigInt(week1Review.id), {
        conclusion: "Tuần 1 hoàn thành đúng hạn",
      });
      expect(completedW1.status).toBe("COMPLETED");

      // Resize cycle from 10 to 6 weeks
      const resized = await updateCycleService({
        workspaceId: ws.workspaceId,
        cycleId: cycle.id,
        authorization: ws.bearerToken,
        durationWeeks: 6,
        reason: "Rút ngắn chu kỳ còn 6 tuần",
      });

      expect(resized.durationWeeks).toBe(6);
      expect(resized.revision).toBe(2);

      const updatedReviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));

      // 1. Completed week 1 review is untouched
      const preservedW1 = updatedReviews.find((r) => r.id === week1Review.id);
      expect(preservedW1!.status).toBe("COMPLETED");

      // 2. Old week 5 mid-cycle is superseded
      const oldMidReview = updatedReviews.find(
        (r) => r.kind === "MID_CYCLE" && r.scheduledWeekNo === 5
      );
      expect(oldMidReview!.status).toBe("SUPERSEDED");

      // 3. New week 3 mid-cycle is created (Math.ceil(6/2) = 3)
      const newMidReview = updatedReviews.find(
        (r) => r.kind === "MID_CYCLE" && r.scheduledWeekNo === 3 && r.status === "SCHEDULED"
      );
      expect(newMidReview).toBeDefined();

      // 4. Incomplete reviews for weeks 7..10 are superseded
      const week7Reviews = updatedReviews.filter((r) => r.scheduledWeekNo === 7);
      for (const r of week7Reviews) {
        expect(r.status).toBe("SUPERSEDED");
      }

      // 5. New end cycle review is at week 6
      const newEndReview = updatedReviews.find(
        (r) => r.kind === "END_CYCLE" && r.scheduledWeekNo === 6 && r.status === "SCHEDULED"
      );
      expect(newEndReview).toBeDefined();

      // 6. Revision journal contains before/after review schedules
      const revisions = await db
        .select()
        .from(cycleRevisions)
        .where(eq(cycleRevisions.cycleId, BigInt(cycle.id)));

      expect(revisions).toHaveLength(1);
      expect((revisions[0].beforeState as any).reviewSchedule).toBeDefined();
      expect((revisions[0].afterState as any).reviewSchedule).toBeDefined();
    });
  });

  describe("Review snapshots immutability", () => {
    it("captures visible PESTEL signals and active initiatives at start without being rewritten by later edits", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      // Seed Strategic Objective & Initiative
      const obj = await createStrategicObjective(ctx, {
        workspaceId: ws.workspaceId,
        title: "Tăng trưởng thị phần",
      });
      const init = await createInitiativeService(
        {
          workspaceId: ws.workspaceId,
          title: "Mở rộng kênh bán hàng",
          strategicObjectiveId: obj.id,
        },
        ws.bearerToken
      );

      // Seed PESTEL signal linked to objective
      const pestelId = generateSnowflake();
      await db.insert(pestelSignals).values({
        id: pestelId,
        workspaceId: BigInt(ws.workspaceId),
        strategicObjectiveId: BigInt(obj.id),
        dimension: "ECONOMIC",
        statement: "Lãi suất cho vay giảm 1%",
        impact: "HIGH",
        certainty: "HIGH",
      });

      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 4,
        startLocalDate: "2026-09-07",
      });

      const reviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));
      const reviewToStart = reviews[0];

      // Start review: captures snapshots
      const started = await startCycleReviewService(ctx, BigInt(reviewToStart.id));
      expect(started.status).toBe("IN_PROGRESS");
      expect(started.pestelSnapshots).toHaveLength(1);
      expect(started.pestelSnapshots[0].statement).toBe("Lãi suất cho vay giảm 1%");
      expect(started.initiativeSnapshots).toHaveLength(1);
      expect(started.initiativeSnapshots[0].title).toBe("Mở rộng kênh bán hàng");

      // Add another PESTEL signal after review started
      const secondPestelId = generateSnowflake();
      await db.insert(pestelSignals).values({
        id: secondPestelId,
        workspaceId: BigInt(ws.workspaceId),
        strategicObjectiveId: BigInt(obj.id),
        dimension: "TECHNOLOGICAL",
        statement: "Tự động hóa bằng AI",
        impact: "MEDIUM",
        certainty: "HIGH",
      });

      // Fetch review again: historical snapshots remain immutable
      const rechecked = await getCycleReviewService(BigInt(ws.workspaceId), BigInt(reviewToStart.id));
      expect(rechecked.pestelSnapshots).toHaveLength(1);
      expect(rechecked.pestelSnapshots[0].statement).toBe("Lãi suất cho vay giảm 1%");

      // Starting review again is idempotent and does not overwrite snapshots
      const reStarted = await startCycleReviewService(ctx, BigInt(reviewToStart.id));
      expect(reStarted.pestelSnapshots).toHaveLength(1);
    });
  });

  describe("Governance authority for review closure", () => {
    it("rejects AI agents from closing cycle reviews", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 4,
        startLocalDate: "2026-09-07",
      });

      const reviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));
      const agentCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: "agent-123",
        membershipRole: "agent",
        actorKind: "AI_AGENT" as any,
      });

      await expect(
        closeCycleReviewService(agentCtx, BigInt(reviews[0].id), {
          conclusion: "Agent closing review",
        })
      ).rejects.toThrow("Agents cannot close cycle reviews");
    });

    it("closing END_CYCLE review requires strategy governance authority and records decision record", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const member = await createTestWorkspaceWithMember({ role: "member" }); // regular member in same or another WS

      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 4,
        startLocalDate: "2026-09-07",
      });

      const reviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));
      const endCycleReview = reviews.find((r) => r.kind === "END_CYCLE")!;

      // Member without governance authority is rejected
      const unauthCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: member.userId,
        membershipRole: "member",
        permissions: [],
      });

      await expect(
        closeCycleReviewService(unauthCtx, BigInt(endCycleReview.id), {
          conclusion: "Member trying to close",
        })
      ).rejects.toThrow();

      // Founder with authority succeeds and creates decision record
      const founderCtx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      const closed = await closeCycleReviewService(founderCtx, BigInt(endCycleReview.id), {
        conclusion: "Hoàn tất chu kỳ 4 tuần thành công",
      });

      expect(closed.status).toBe("COMPLETED");
      expect(closed.decisionId).not.toBeNull();
      expect(closed.conclusion).toBe("Hoàn tất chu kỳ 4 tuần thành công");

      // Verify decision record exists in strategy.decision_records
      const [dr] = await db
        .select()
        .from(decisionRecords)
        .where(eq(decisionRecords.id, BigInt(closed.decisionId!)));

      expect(dr).toBeDefined();
      expect(dr.decision).toBe("END_CYCLE_REVIEW_CLOSED");
      expect(dr.decisionType).toBe("CYCLE_REVIEW_CLOSURE");
    });
  });

  describe("Custom Mid-Cycle reviews and policy gating", () => {
    it("allows creating custom mid-cycle review under CUSTOM policy", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      await updateWorkspaceStrategySettings(ctx, {
        workspaceId: ws.workspaceId,
        midCycleReviewPolicy: "CUSTOM",
      });

      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 8,
        startLocalDate: "2026-09-07",
      });

      // No mid-cycle automatically scheduled
      const initialReviews = await listCycleReviewsService(BigInt(ws.workspaceId), BigInt(cycle.id));
      expect(initialReviews.filter((r) => r.kind === "MID_CYCLE")).toHaveLength(0);

      // Create custom mid-cycle review for week 4
      const customReview = await createCustomMidCycleReviewService(ctx, BigInt(cycle.id), 4);
      expect(customReview.kind).toBe("MID_CYCLE");
      expect(customReview.scheduledWeekNo).toBe(4);
      expect(customReview.status).toBe("SCHEDULED");
    });

    it("rejects custom mid-cycle review under OFF policy", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const ctx = createMockTenantContext({
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: ["*"],
      });

      await updateWorkspaceStrategySettings(ctx, {
        workspaceId: ws.workspaceId,
        midCycleReviewPolicy: "OFF",
      });

      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 8,
        startLocalDate: "2026-09-07",
      });

      await expect(
        createCustomMidCycleReviewService(ctx, BigInt(cycle.id), 4)
      ).rejects.toThrow("Mid-cycle reviews are disabled by workspace strategy settings policy 'OFF'");
    });
  });

  describe("Cross-workspace rejection", () => {
    it("rejects querying or mutating reviews across workspaces", async () => {
      const wsA = await createTestWorkspaceWithMember({ role: "founder" });
      const wsB = await createTestWorkspaceWithMember({ role: "founder" });

      const cycleA = await createCycleService({
        workspaceId: wsA.workspaceId,
        authorization: wsA.bearerToken,
        durationWeeks: 4,
        startLocalDate: "2026-09-07",
      });

      const reviewsA = await listCycleReviewsService(BigInt(wsA.workspaceId), BigInt(cycleA.id));
      const targetReview = reviewsA[0];

      // Querying with workspace B
      await expect(
        getCycleReviewService(BigInt(wsB.workspaceId), BigInt(targetReview.id))
      ).rejects.toThrow("not found");

      // Mutating with workspace B ctx
      const ctxB = createMockTenantContext({
        workspaceId: wsB.workspaceId,
        userId: wsB.userId,
        membershipRole: "founder",
      });

      await expect(
        startCycleReviewService(ctxB, BigInt(targetReview.id))
      ).rejects.toThrow("not found");

      await expect(
        closeCycleReviewService(ctxB, BigInt(targetReview.id), { conclusion: "cross-ws" })
      ).rejects.toThrow("not found");
    });
  });
});
