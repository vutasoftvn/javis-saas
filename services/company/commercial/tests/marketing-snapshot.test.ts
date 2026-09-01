import { describe, expect, it, beforeEach } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  getOrCreateContextRow,
  assembleContextDTO,
  recordRevisionSnapshot,
  verifyOptimisticLock,
  getMarketingContextService,
  updateOfferArchitectureService,
  updateTwelveWeekPlanService,
  submitForReviewService,
  approveContextService,
  MarketingContextDTO,
} from "../services/marketing-snapshot.service";
import { db, schema } from "../models/db";
import { eq, and } from "drizzle-orm";
import { APIError } from "encore.dev/api";

const { marketingContexts, marketingContextRevisions } = schema;

describe("marketing-snapshot.service", () => {
  describe("getOrCreateContextRow", () => {
    it("creates a new context row on first call with default values", async () => {
      // Khởi tạo workspace test mới
      const user = await createTestSession({
        displayName: "Test User - getOrCreate",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-001",
      };

      const contextRow = await getOrCreateContextRow(ctx);

      // Kiểm tra row được tạo với giá trị mặc định đúng
      expect(contextRow.id).toBeDefined();
      expect(contextRow.workspaceId).toBe(BigInt(user.workspaceId));
      expect(contextRow.revision).toBe(1);
      expect(contextRow.status).toBe("draft");
      expect(contextRow.updatedByUserId).toBe(BigInt(user.userId));
      expect(contextRow.offerArchitecture).toEqual({});
      expect(contextRow.twelveWeekPlan).toEqual({});
    });

    it("returns existing context row on subsequent calls", async () => {
      // Khởi tạo workspace test
      const user = await createTestSession({
        displayName: "Test User - getOrCreate Existing",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-002",
      };

      // Tạo lần đầu
      const firstCall = await getOrCreateContextRow(ctx);

      // Tạo lần thứ hai - phải trả về cùng một row
      const secondCall = await getOrCreateContextRow(ctx);

      expect(firstCall.id).toBe(secondCall.id);
      expect(firstCall.revision).toBe(secondCall.revision);
    });

    it("creates empty product marketing record alongside context", async () => {
      // Kiểm tra rằng empty product marketing record được tạo kèm theo
      const user = await createTestSession({
        displayName: "Test User - Product Marketing Create",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-003",
      };

      const contextRow = await getOrCreateContextRow(ctx);

      // Kiểm tra product marketing record được tạo
      const [pmRow] = await db
        .select()
        .from(schema.marketingProductMarketing)
        .where(
          and(
            eq(schema.marketingProductMarketing.workspaceId, BigInt(user.workspaceId)),
            eq(schema.marketingProductMarketing.contextId, contextRow.id)
          )
        )
        .limit(1);

      expect(pmRow).toBeDefined();
      expect(pmRow?.category).toBeNull();
      expect(pmRow?.positioningStatement).toBeNull();
      expect(pmRow?.alternatives).toEqual([]);
      expect(pmRow?.differentiators).toEqual([]);
      expect(pmRow?.brandVoice).toEqual({});
    });
  });

  describe("assembleContextDTO", () => {
    it("assembles complete DTO with all empty related data", async () => {
      // Khởi tạo workspace
      const user = await createTestSession({
        displayName: "Test User - Assemble Empty",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-004",
      };

      // Tạo context row
      const contextRow = await getOrCreateContextRow(ctx);

      // Assemble DTO
      const dto = await assembleContextDTO(contextRow, ctx);

      // Kiểm tra DTO cấu trúc và giá trị
      expect(dto.id).toBe(contextRow.id.toString());
      expect(dto.workspaceId).toBe(user.workspaceId);
      expect(dto.revision).toBe(1);
      expect(dto.status).toBe("draft");
      expect(dto.productMarketing).toBeDefined();
      expect(dto.productMarketing.category).toBeNull();
      expect(dto.icpSegments).toEqual([]);
      expect(dto.customerResearchThemes).toEqual([]);
      expect(dto.customerLanguage).toEqual([]);
      expect(dto.evidence).toEqual([]);
      expect(dto.createdAt).toBeDefined();
      expect(dto.updatedAt).toBeDefined();
    });

    it("maps ISO datetime strings correctly", async () => {
      // Kiểm tra rằng dates được convert từ Date object sang ISO string
      const user = await createTestSession({
        displayName: "Test User - Date Mapping",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-005",
      };

      const contextRow = await getOrCreateContextRow(ctx);
      const dto = await assembleContextDTO(contextRow, ctx);

      // createdAt và updatedAt phải là ISO string
      expect(typeof dto.createdAt).toBe("string");
      expect(typeof dto.updatedAt).toBe("string");
      expect(dto.createdAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
      expect(dto.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });

    it("handles null reviewedAt field when context not yet approved", async () => {
      // Kiểm tra null handling cho reviewedAt trước khi approve
      const user = await createTestSession({
        displayName: "Test User - Reviewed At Null",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-006",
      };

      const contextRow = await getOrCreateContextRow(ctx);
      const dto = await assembleContextDTO(contextRow, ctx);

      expect(dto.reviewedAt).toBeNull();
      expect(dto.reviewedByUserId).toBeNull();
    });
  });

  describe("recordRevisionSnapshot", () => {
    it("creates a revision snapshot with all context data", async () => {
      // Khởi tạo workspace
      const user = await createTestSession({
        displayName: "Test User - Snapshot Record",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-007",
      };

      // Tạo context row
      const contextRow = await getOrCreateContextRow(ctx);
      const dto = await assembleContextDTO(contextRow, ctx);

      // Record snapshot
      await recordRevisionSnapshot(
        contextRow.id,
        BigInt(user.workspaceId),
        2,
        dto,
        BigInt(user.userId),
        {
          id: "skill.marketing",
          version: "1.0.0",
          hash: "abc123",
        }
      );

      // Kiểm tra snapshot được lưu
      const [snapshot] = await db
        .select()
        .from(marketingContextRevisions)
        .where(
          and(
            eq(marketingContextRevisions.workspaceId, BigInt(user.workspaceId)),
            eq(marketingContextRevisions.contextId, contextRow.id),
            eq(marketingContextRevisions.revision, 2)
          )
        )
        .limit(1);

      function hasSnapshotId(value: unknown): value is { id: string } {
        return typeof value === "object" && value !== null &&
          "id" in value && typeof (value as { id?: unknown }).id === "string";
      }

      expect(snapshot).toBeDefined();
      expect(snapshot?.revision).toBe(2);
      const snapshotPayload = snapshot?.snapshot;
      expect(hasSnapshotId(snapshotPayload)).toBe(true);
      if (!hasSnapshotId(snapshotPayload)) throw new Error("snapshot payload must contain an id");
      expect(snapshotPayload.id).toBe(dto.id);
      expect(snapshot?.sourceSkillId).toBe("skill.marketing");
      expect(snapshot?.sourceSkillVersion).toBe("1.0.0");
      expect(snapshot?.sourceSkillHash).toBe("abc123");
    });

    it("records snapshot without optional skill metadata", async () => {
      // Kiểm tra snapshot được tạo khi không có source skill
      const user = await createTestSession({
        displayName: "Test User - Snapshot No Skill",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-008",
      };

      const contextRow = await getOrCreateContextRow(ctx);
      const dto = await assembleContextDTO(contextRow, ctx);

      // Record snapshot mà không có skill metadata
      await recordRevisionSnapshot(
        contextRow.id,
        BigInt(user.workspaceId),
        2,
        dto,
        BigInt(user.userId)
      );

      const [snapshot] = await db
        .select()
        .from(marketingContextRevisions)
        .where(
          and(
            eq(marketingContextRevisions.contextId, contextRow.id),
            eq(marketingContextRevisions.revision, 2)
          )
        );

      expect(snapshot?.sourceSkillId).toBeNull();
      expect(snapshot?.sourceSkillVersion).toBeNull();
      expect(snapshot?.sourceSkillHash).toBeNull();
    });
  });

  describe("verifyOptimisticLock", () => {
    it("allows update when no expectedRevision is specified", () => {
      // Không throw khi expectedRevision undefined
      expect(() => verifyOptimisticLock(5)).not.toThrow();
    });

    it("allows update when expectedRevision matches currentRevision", () => {
      // Không throw khi revision khớp
      expect(() => verifyOptimisticLock(5, 5)).not.toThrow();
    });

    it("throws APIError.aborted when expectedRevision mismatches", () => {
      // Throw APIError.aborted khi revision không khớp
      expect(() => verifyOptimisticLock(5, 3)).toThrow();
      expect(() => verifyOptimisticLock(5, 3)).toThrow(/revision conflict/i);
    });

    it("error message includes revision details", () => {
      // Kiểm tra error message có chi tiết revision
      let errorMessage = "";
      try {
        verifyOptimisticLock(10, 7);
      } catch (e) {
        if (e instanceof APIError) {
          errorMessage = e.message;
        }
      }
      expect(errorMessage).toContain("expected revision 7");
      expect(errorMessage).toContain("current revision is 10");
    });
  });

  describe("getMarketingContextService", () => {
    it("returns complete assembled context for existing workspace", async () => {
      // Lấy context service đầy đủ
      const user = await createTestSession({
        displayName: "Test User - Get Context Service",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-009",
      };

      const result = await getMarketingContextService(ctx);

      expect(result).toBeInstanceOf(Object);
      expect(result.id).toBeDefined();
      expect(result.workspaceId).toBe(user.workspaceId);
      expect(result.revision).toBe(1);
      expect(result.status).toBe("draft");
    });
  });

  describe("updateOfferArchitectureService", () => {
    it("updates offer architecture and increments revision", async () => {
      // Cập nhật offer architecture và tăng revision
      const user = await createTestSession({
        displayName: "Test User - Update Offer Arch",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-010",
      };

      const updateParams = {
        offerArchitecture: {
          coreOffer: "Growth Plan",
          pricingModel: "Monthly Subscription",
          guarantee: "30-day money back",
        },
        expectedRevision: 1,
      };

      const result = await updateOfferArchitectureService(ctx, updateParams);

      // Kiểm tra revision tăng
      expect(result.revision).toBe(2);
      // Kiểm tra offer architecture được cập nhật
      expect(result.offerArchitecture).toEqual(updateParams.offerArchitecture);
      // Status phải vẫn là draft
      expect(result.status).toBe("draft");
      // Kiểm tra updatedByUserId được set
      expect(result.updatedByUserId).toBe(user.userId);
    });

    it("rejects update with wrong expectedRevision", async () => {
      // Reject khi expectedRevision không match
      const user = await createTestSession({
        displayName: "Test User - Update Offer Arch Wrong Rev",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-011",
      };

      const updateParams = {
        offerArchitecture: { coreOffer: "Plan" },
        expectedRevision: 999, // Wrong revision
      };

      await expect(updateOfferArchitectureService(ctx, updateParams)).rejects.toThrow(
        /revision conflict/i
      );
    });

    it("records revision snapshot with new offer architecture data", async () => {
      // Kiểm tra snapshot được record sau update
      const user = await createTestSession({
        displayName: "Test User - Update Offer Snapshot",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-012",
      };

      const offerArch = { coreOffer: "Premium Plan", pricingModel: "Seat-based" };

      const result = await updateOfferArchitectureService(ctx, {
        offerArchitecture: offerArch,
        expectedRevision: 1,
      });

      // Tìm revision snapshot
      const [snapshot] = await db
        .select()
        .from(marketingContextRevisions)
        .where(
          and(
            eq(marketingContextRevisions.workspaceId, BigInt(user.workspaceId)),
            eq(marketingContextRevisions.revision, 2)
          )
        );

      expect(snapshot).toBeDefined();
      expect((snapshot?.snapshot as any)?.offerArchitecture).toEqual(offerArch);
    });

    it("preserves and updates source skill metadata", async () => {
      // Cập nhật source skill metadata
      const user = await createTestSession({
        displayName: "Test User - Update Offer Skill Meta",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-013",
      };

      const result = await updateOfferArchitectureService(ctx, {
        offerArchitecture: { coreOffer: "Plan" },
        expectedRevision: 1,
        sourceSkillId: "skill.offer",
        sourceSkillVersion: "1.2.3",
        sourceSkillHash: "hash123",
      });

      expect(result.sourceSkillId).toBe("skill.offer");
      expect(result.sourceSkillVersion).toBe("1.2.3");
      expect(result.sourceSkillHash).toBe("hash123");
    });
  });

  describe("updateTwelveWeekPlanService", () => {
    it("updates twelve-week plan and increments revision", async () => {
      // Cập nhật 12-week plan
      const user = await createTestSession({
        displayName: "Test User - Update 12Week Plan",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-014",
      };

      const planData = {
        theme: "Q3 Launch Campaign",
        weeklyGoals: [
          { week: 1, objective: "Setup tracking" },
          { week: 2, objective: "Validate messaging" },
        ],
      };

      const result = await updateTwelveWeekPlanService(ctx, {
        twelveWeekPlan: planData,
        expectedRevision: 1,
      });

      expect(result.revision).toBe(2);
      expect(result.twelveWeekPlan).toEqual(planData);
      expect(result.status).toBe("draft");
    });

    it("rejects update with wrong expectedRevision", async () => {
      // Reject khi expectedRevision không match
      const user = await createTestSession({
        displayName: "Test User - Update 12Week Plan Wrong Rev",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-015",
      };

      await expect(
        updateTwelveWeekPlanService(ctx, {
          twelveWeekPlan: { theme: "Campaign" },
          expectedRevision: 999,
        })
      ).rejects.toThrow(/revision conflict/i);
    });

    it("records revision snapshot after plan update", async () => {
      // Snapshot được record
      const user = await createTestSession({
        displayName: "Test User - 12Week Plan Snapshot",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-016",
      };

      const planData = { theme: "Launch Phase", weeklyGoals: [] };

      await updateTwelveWeekPlanService(ctx, {
        twelveWeekPlan: planData,
        expectedRevision: 1,
      });

      const [snapshot] = await db
        .select()
        .from(marketingContextRevisions)
        .where(
          and(
            eq(marketingContextRevisions.workspaceId, BigInt(user.workspaceId)),
            eq(marketingContextRevisions.revision, 2)
          )
        );

      expect(snapshot).toBeDefined();
      expect((snapshot?.snapshot as any)?.twelveWeekPlan).toEqual(planData);
    });
  });

  describe("submitForReviewService", () => {
    it("changes status to review_required and increments revision", async () => {
      // Đổi status sang review_required
      const user = await createTestSession({
        displayName: "Test User - Submit Review",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-017",
      };

      const result = await submitForReviewService(ctx, {
        expectedRevision: 1,
      });

      expect(result.status).toBe("review_required");
      expect(result.revision).toBe(2);
      expect(result.updatedByUserId).toBe(user.userId);
    });

    it("rejects submission with wrong expectedRevision", async () => {
      // Reject khi expectedRevision không match
      const user = await createTestSession({
        displayName: "Test User - Submit Review Wrong Rev",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-018",
      };

      await expect(
        submitForReviewService(ctx, { expectedRevision: 999 })
      ).rejects.toThrow(/revision conflict/i);
    });

    it("allows submission without expectedRevision parameter", async () => {
      // Cho phép submit mà không cần expectedRevision
      const user = await createTestSession({
        displayName: "Test User - Submit Review No Param",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-019",
      };

      const result = await submitForReviewService(ctx);

      expect(result.status).toBe("review_required");
      expect(result.revision).toBe(2);
    });

    it("records revision snapshot on submission", async () => {
      // Snapshot được record trên submit
      const user = await createTestSession({
        displayName: "Test User - Submit Review Snapshot",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-020",
      };

      await submitForReviewService(ctx, { expectedRevision: 1 });

      const [snapshot] = await db
        .select()
        .from(marketingContextRevisions)
        .where(
          and(
            eq(marketingContextRevisions.workspaceId, BigInt(user.workspaceId)),
            eq(marketingContextRevisions.revision, 2)
          )
        );

      expect(snapshot).toBeDefined();
      expect((snapshot?.snapshot as any)?.status).toBe("review_required");
    });
  });

  describe("approveContextService", () => {
    it("allows founder to approve context", async () => {
      // Founder có thể approve
      const user = await createTestSession({
        displayName: "Test User - Founder Approve",
        role: "founder",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "test-corr-021",
      };

      // Ít nhất phải đứng ở review_required trước khi approve
      await submitForReviewService(ctx, { expectedRevision: 1 });

      const result = await approveContextService(ctx, {
        expectedRevision: 2,
      });

      expect(result.status).toBe("approved");
      expect(result.revision).toBe(3);
      expect(result.reviewedByUserId).toBe(user.userId);
      expect(result.reviewedAt).toBeDefined();
    });

    it("allows co-founder to approve context", async () => {
      // Co-founder có thể approve
      const user = await createTestSession({
        displayName: "Test User - CoFounder Approve",
        role: "co-founder",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "co-founder",
        permissions: [],
        correlationId: "test-corr-022",
      };

      await submitForReviewService(ctx, { expectedRevision: 1 });

      const result = await approveContextService(ctx, {
        expectedRevision: 2,
      });

      expect(result.status).toBe("approved");
      expect(result.reviewedByUserId).toBe(user.userId);
    });

    it("allows user with * permission to approve context", async () => {
      // User với * permission có thể approve
      const user = await createTestSession({
        displayName: "Test User - Star Permission Approve",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: ["*"], // Star permission
        correlationId: "test-corr-023",
      };

      await submitForReviewService(ctx, { expectedRevision: 1 });

      const result = await approveContextService(ctx, {
        expectedRevision: 2,
      });

      expect(result.status).toBe("approved");
      expect(result.reviewedByUserId).toBe(user.userId);
    });

    it("rejects non-founder approval attempt", async () => {
      // Reject khi user không phải founder
      const user = await createTestSession({
        displayName: "Test User - Member Approve Reject",
        role: "member",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "member",
        permissions: [],
        correlationId: "test-corr-024",
      };

      await submitForReviewService(ctx, { expectedRevision: 1 });

      await expect(approveContextService(ctx, { expectedRevision: 2 })).rejects.toThrow(
        /founder/i
      );
    });

    it("rejects approval with wrong expectedRevision", async () => {
      // Reject khi expectedRevision không match
      const user = await createTestSession({
        displayName: "Test User - Approve Wrong Rev",
        role: "founder",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "test-corr-025",
      };

      await submitForReviewService(ctx, { expectedRevision: 1 });

      await expect(
        approveContextService(ctx, { expectedRevision: 999 })
      ).rejects.toThrow(/revision conflict/i);
    });

    it("records approval timestamp and reviewer info", async () => {
      // Kiểm tra reviewedAt được set chính xác
      const user = await createTestSession({
        displayName: "Test User - Approve Timestamp",
        role: "founder",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "test-corr-026",
      };

      const beforeApprove = new Date();

      await submitForReviewService(ctx, { expectedRevision: 1 });
      const result = await approveContextService(ctx, {
        expectedRevision: 2,
      });

      const afterApprove = new Date();

      const reviewedAt = new Date(result.reviewedAt || "");
      expect(reviewedAt.getTime()).toBeGreaterThanOrEqual(beforeApprove.getTime());
      expect(reviewedAt.getTime()).toBeLessThanOrEqual(afterApprove.getTime());
    });

    it("records revision snapshot on approval", async () => {
      // Snapshot được record trên approve
      const user = await createTestSession({
        displayName: "Test User - Approve Snapshot",
        role: "founder",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "test-corr-027",
      };

      await submitForReviewService(ctx, { expectedRevision: 1 });
      await approveContextService(ctx, { expectedRevision: 2 });

      const [snapshot] = await db
        .select()
        .from(marketingContextRevisions)
        .where(
          and(
            eq(marketingContextRevisions.workspaceId, BigInt(user.workspaceId)),
            eq(marketingContextRevisions.revision, 3)
          )
        );

      expect(snapshot).toBeDefined();
      expect((snapshot?.snapshot as any)?.status).toBe("approved");
    });
  });

  describe("Tenant Isolation", () => {
    it("strictly isolates contexts across different workspaces", async () => {
      // Tạo 2 workspaces riêng biệt
      const wsA = await createTestSession({
        displayName: "Tenant A User",
        role: "founder",
      });

      const wsB = await createTestSession({
        displayName: "Tenant B User",
        role: "founder",
      });

      const ctxA = {
        workspaceId: wsA.workspaceId,
        userId: wsA.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "tenant-a",
      };

      const ctxB = {
        workspaceId: wsB.workspaceId,
        userId: wsB.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "tenant-b",
      };

      // Workspace A cập nhật offer architecture
      const offerArchA = { coreOffer: "Secret Offer A", pricingModel: "Per-seat" };
      await updateOfferArchitectureService(ctxA, {
        offerArchitecture: offerArchA,
        expectedRevision: 1,
      });

      // Workspace B cập nhật offer architecture với dữ liệu khác
      const offerArchB = { coreOffer: "Public Offer B", pricingModel: "Monthly" };
      await updateOfferArchitectureService(ctxB, {
        offerArchitecture: offerArchB,
        expectedRevision: 1,
      });

      // Lấy dữ liệu từ cả hai workspace
      const resultA = await getMarketingContextService(ctxA);
      const resultB = await getMarketingContextService(ctxB);

      // Kiểm tra isolation
      expect(resultA.workspaceId).toBe(wsA.workspaceId);
      expect(resultB.workspaceId).toBe(wsB.workspaceId);
      expect(resultA.offerArchitecture).toEqual(offerArchA);
      expect(resultB.offerArchitecture).toEqual(offerArchB);
      // Dữ liệu A không được có trong B
      expect(resultB.offerArchitecture?.coreOffer).not.toContain("Secret");
    });

    it("prevents revision snapshots from leaking across workspaces", async () => {
      // Snapshots không bị leak qua workspaces
      const wsA = await createTestSession({
        displayName: "Tenant Snapshot A",
        role: "founder",
      });

      const wsB = await createTestSession({
        displayName: "Tenant Snapshot B",
        role: "founder",
      });

      const ctxA = {
        workspaceId: wsA.workspaceId,
        userId: wsA.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "snap-a",
      };

      const ctxB = {
        workspaceId: wsB.workspaceId,
        userId: wsB.userId,
        membershipRole: "founder",
        permissions: ["*"],
        correlationId: "snap-b",
      };

      // Workspace A tạo snapshot
      await updateOfferArchitectureService(ctxA, {
        offerArchitecture: { secret: "data A" },
        expectedRevision: 1,
      });

      // Workspace B tạo snapshot
      await updateOfferArchitectureService(ctxB, {
        offerArchitecture: { secret: "data B" },
        expectedRevision: 1,
      });

      // Kiểm tra snapshots không bị mix
      const snapshotsA = await db
        .select()
        .from(marketingContextRevisions)
        .where(eq(marketingContextRevisions.workspaceId, BigInt(wsA.workspaceId)));

      const snapshotsB = await db
        .select()
        .from(marketingContextRevisions)
        .where(eq(marketingContextRevisions.workspaceId, BigInt(wsB.workspaceId)));

      // Mỗi workspace chỉ có snapshots của chính nó
      snapshotsA.forEach((snap) => {
        expect(snap.workspaceId).toBe(BigInt(wsA.workspaceId));
      });

      snapshotsB.forEach((snap) => {
        expect(snap.workspaceId).toBe(BigInt(wsB.workspaceId));
      });
    });
  });

  describe("Edge Cases and Boundary Conditions", () => {
    it("handles empty offerArchitecture object", async () => {
      // Xử lý empty object cho offer architecture
      const user = await createTestSession({
        displayName: "Test User - Empty Offer Arch",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-028",
      };

      const result = await updateOfferArchitectureService(ctx, {
        offerArchitecture: {},
        expectedRevision: 1,
      });

      expect(result.offerArchitecture).toEqual({});
    });

    it("handles large nested JSON structures", async () => {
      // Xử lý các cấu trúc JSON lớn phức tạp
      const user = await createTestSession({
        displayName: "Test User - Large JSON",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-029",
      };

      const largeStructure = {
        weeks: Array.from({ length: 12 }, (_, i) => ({
          week: i + 1,
          goals: Array.from({ length: 5 }, (_, j) => ({
            id: `goal-${i}-${j}`,
            description: `Goal description for week ${i + 1}, goal ${j + 1}`,
            metrics: ["metric-1", "metric-2", "metric-3"],
          })),
        })),
      };

      const result = await updateTwelveWeekPlanService(ctx, {
        twelveWeekPlan: largeStructure,
        expectedRevision: 1,
      });

      expect(result.twelveWeekPlan).toEqual(largeStructure);
      expect(result.twelveWeekPlan?.weeks).toHaveLength(12);
    });

    it("handles multiple sequential updates preserving history", async () => {
      // Kiểm tra lịch sử updates được giữ lại chính xác
      const user = await createTestSession({
        displayName: "Test User - Sequential Updates",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-030",
      };

      // Update 1: offer architecture
      const update1 = await updateOfferArchitectureService(ctx, {
        offerArchitecture: { version: "v1" },
        expectedRevision: 1,
      });
      expect(update1.revision).toBe(2);

      // Update 2: twelve week plan
      const update2 = await updateTwelveWeekPlanService(ctx, {
        twelveWeekPlan: { version: "v1" },
        expectedRevision: 2,
      });
      expect(update2.revision).toBe(3);

      // Update 3: offer architecture again
      const update3 = await updateOfferArchitectureService(ctx, {
        offerArchitecture: { version: "v2" },
        expectedRevision: 3,
      });
      expect(update3.revision).toBe(4);

      // Kiểm tra tất cả snapshots được lưu
      const snapshots = await db
        .select()
        .from(marketingContextRevisions)
        .where(eq(marketingContextRevisions.workspaceId, BigInt(user.workspaceId)));

      expect(snapshots).toHaveLength(3); // revisions 2, 3, 4
      expect(snapshots[0]?.revision).toBe(2);
      expect(snapshots[1]?.revision).toBe(3);
      expect(snapshots[2]?.revision).toBe(4);
    });

    it("handles concurrent revision conflicts gracefully", async () => {
      // Kiểm tra xử lý concurrent conflicts
      const user = await createTestSession({
        displayName: "Test User - Concurrent Conflict",
        role: "admin",
      });

      const ctx = {
        workspaceId: user.workspaceId,
        userId: user.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test-corr-031",
      };

      // First update
      const first = await updateOfferArchitectureService(ctx, {
        offerArchitecture: { step: "first" },
        expectedRevision: 1,
      });

      // Attempt second update with stale expectedRevision (should fail)
      await expect(
        updateOfferArchitectureService(ctx, {
          offerArchitecture: { step: "second" },
          expectedRevision: 1, // Still expecting 1, but it's now 2
        })
      ).rejects.toThrow(/revision conflict/i);

      // But valid update should work
      const valid = await updateOfferArchitectureService(ctx, {
        offerArchitecture: { step: "second" },
        expectedRevision: 2,
      });

      expect(valid.revision).toBe(3);
    });
  });
});
