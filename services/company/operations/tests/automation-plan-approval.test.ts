// Plan hub vận hành đợt 2 B5 (Task 6, phần 1) — founder duyệt MỘT LẦN thẻ kế hoạch tự động hoá.
// Chạy trên DB test thật. Phát hiện review Task 5 (bắt buộc xử lý): re-verify kênh + agent
// deployment BÂY GIỜ, không tin `readiness` cũ của nháp.
import { describe, expect, it } from "vitest";
import { eq, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { founderNotificationChannels, identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { FOUNDER_CHANNEL_SECRET_NAMESPACE } from "../../identity/services/founder-channel-secret";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import { proposeAutomationPlan, type ProposeAutomationPlanInput } from "../services/automation-plan-proposal.service";
import {
  approveAutomationPlanProposal,
  linkAutomationPlanSchedule,
} from "../services/automation-plan-approval.service";
import { approveAutomationPlanApi, linkAutomationPlanScheduleApi } from "../handlers/automation-plan-approval.handler";
import { pauseProjectDeployment } from "../services/founder-asset-deployment.service";
import {
  addMemberToWorkspace,
  createTestWorkspaceWithMember,
  deployWorkspaceAgentForProfile,
  makeTestTenantContext,
} from "./_helpers";

const { automationPlanProposals } = schema;
const CHAT_ID = "555000111";

interface Founder {
  workspaceId: string;
  projectId: string;
  userId: string;
  memberId: string;
  bearerToken: string;
}

async function seedFounder(role = "founder"): Promise<Founder> {
  const ws = await createTestWorkspaceWithMember({ role });
  const memberId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: memberId,
    workspaceId: BigInt(ws.workspaceId),
    memberType: "HUMAN",
    humanUserId: BigInt(ws.userId),
    roleTitle: role,
    status: "active",
  });
  return { ...ws, memberId: memberId.toString() };
}

function founderCtx(f: Founder, membershipRole = "founder") {
  return makeTestTenantContext({
    workspaceId: f.workspaceId,
    userId: f.userId,
    workforceMemberId: f.memberId,
    membershipRole,
  });
}

async function insertVerifiedChannel(f: Founder, label: string | null = "Nhóm vận hành"): Promise<string> {
  const id = generateSnowflake();
  const secretRef = `${FOUNDER_CHANNEL_SECRET_NAMESPACE}telegram/${id.toString()}`;
  await db.insert(founderNotificationChannels).values({
    id,
    workspaceId: BigInt(f.workspaceId),
    founderMemberId: BigInt(f.memberId),
    kind: "telegram",
    secretRef,
    chatId: CHAT_ID,
    label,
    verifiedAt: new Date("2026-09-27T01:00:00Z"),
  });
  return secretRef;
}

function baseInput(overrides: Partial<ProposeAutomationPlanInput> = {}): ProposeAutomationPlanInput {
  return {
    skillId: "operations.email-digest",
    connectorKeys: ["email-read"],
    connectorStatus: { "email-read": "connected" },
    channelKind: "telegram",
    schedule: { kind: "daily", hour: 7, minute: 30, timezone: "Asia/Ho_Chi_Minh" },
    tokenBudgetPerRun: 20000,
    ...overrides,
  };
}

function delegationFor(f: Founder, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${f.userId}`,
    workspace_id: f.workspaceId,
    run_id: "run-automation-plan-approve-1",
    capability_ids: capabilityIds,
  })}`;
}

async function errorOf(p: Promise<unknown>): Promise<{ code?: string; message: string }> {
  try {
    await p;
  } catch (err) {
    return { code: (err as { code?: string }).code, message: (err as Error).message };
  }
  throw new Error("expected rejection");
}

/** Thêm co-founder vào ĐÚNG workspace của `f` (khác `seedFounder`, tạo workspace mới riêng). */
async function addCoFounderToWorkspace(f: Founder): Promise<Founder> {
  const member = await addMemberToWorkspace(f.workspaceId, "co-founder");
  const memberId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: memberId,
    workspaceId: BigInt(f.workspaceId),
    memberType: "HUMAN",
    humanUserId: BigInt(member.userId),
    roleTitle: "co-founder",
    status: "active",
  });
  return {
    workspaceId: f.workspaceId,
    projectId: f.projectId,
    userId: member.userId,
    memberId: memberId.toString(),
    bearerToken: member.bearerToken,
  };
}

/** Đề xuất nháp READY (agent + channel + connector đủ) — tiện dùng cho các test approve. */
async function seedReadyDraft(
  overrides: Partial<ProposeAutomationPlanInput> = {}
): Promise<{ f: Founder; proposalId: string; deploymentId: string }> {
  const f = await seedFounder();
  await insertVerifiedChannel(f);
  const ctx = founderCtx(f);
  const { deploymentId } = await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");
  const res = await proposeAutomationPlan(ctx, f.projectId, baseInput(overrides));
  expect(res.data.readiness.ready).toBe(true);
  return { f, proposalId: res.data.proposalId, deploymentId };
}

describe("automation-plan-approval — approve", () => {
  it("duyệt nháp DRAFT ready: chuyển APPROVED, trả founderMemberId/founderUserId từ ctx (người bấm duyệt)", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const ctx = founderCtx(f);

    const res = await approveAutomationPlanProposal(ctx, f.projectId, proposalId);

    expect(res.data.status).toBe("APPROVED");
    expect(res.data.proposalId).toBe(proposalId);
    expect(res.data.founderMemberId).toBe(f.memberId);
    expect(res.data.founderUserId).toBe(f.userId);
    expect(res.data.capabilityIds).toEqual(["email.digest.read", "founder.notify.send"]);
    expect(res.data.plan.skillId).toBe("operations.email-digest");

    const [row] = await db
      .select()
      .from(automationPlanProposals)
      .where(sql`${automationPlanProposals.id} = ${BigInt(proposalId)}`);
    expect(row.status).toBe("APPROVED");
    expect(row.decidedAt).not.toBeNull();
    expect(row.decidedByMemberId?.toString()).toBe(f.memberId);
    expect(row.decidedByUserId).toBe(f.userId);
    expect(row.approvedScheduleId).toBeNull();
  });

  it("co-founder (không phải người đề xuất) vẫn duyệt được — founder sở hữu lịch = người bấm duyệt", async () => {
    const { f, proposalId } = await seedReadyDraft();
    // Co-founder CÙNG workspace, có kênh riêng đã xác minh (channel re-verify dùng danh tính
    // người duyệt, không phải người đề xuất).
    const coFounder = await addCoFounderToWorkspace(f);
    await insertVerifiedChannel(coFounder, "Kênh co-founder");
    const ctx = founderCtx(coFounder, "co-founder");

    const res = await approveAutomationPlanProposal(ctx, f.projectId, proposalId);
    expect(res.data.founderMemberId).toBe(coFounder.memberId);
    expect(res.data.founderUserId).toBe(coFounder.userId);
  });

  it("không phải founder/co-founder -> permission_denied", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const member = await seedFounder("member");
    const ctx = founderCtx(member, "member");

    const err = await errorOf(approveAutomationPlanProposal(ctx, f.projectId, proposalId));
    expect(err.code).toBe("permission_denied");
    expect(err.message).toMatch(/^founder_owner_not_authorized:/);
  });

  it("proposal thuộc project khác trong cùng workspace -> not_found", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const otherProjectId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
      VALUES (${otherProjectId}, ${BigInt(f.workspaceId)}, 'Other', 'ACTIVE', 'P0_DISCOVERY')
    `);
    const err = await errorOf(
      approveAutomationPlanProposal(founderCtx(f), otherProjectId.toString(), proposalId)
    );
    expect(err.code).toBe("not_found");
    expect(err.message).toMatch(/^automation_plan_not_found:/);
  });

  it("proposalId không tồn tại -> not_found", async () => {
    const f = await seedFounder();
    const err = await errorOf(approveAutomationPlanProposal(founderCtx(f), f.projectId, "123456789"));
    expect(err.code).toBe("not_found");
  });

  describe("re-verify readiness lúc duyệt (phát hiện review Task 5 mục 1) — KHÔNG tin readiness cũ", () => {
    it("kênh founder bị thu hồi sau khi đề xuất -> failed_precondition automation_plan_not_ready", async () => {
      const { f, proposalId } = await seedReadyDraft();
      await db
        .update(founderNotificationChannels)
        .set({ revokedAt: new Date() })
        .where(eq(founderNotificationChannels.founderMemberId, BigInt(f.memberId)));

      const err = await errorOf(approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId));
      expect(err.code).toBe("failed_precondition");
      expect(err.message).toMatch(/^automation_plan_not_ready:/);
      expect(err.message).toContain("founder_channel_unverified");

      const [row] = await db
        .select()
        .from(automationPlanProposals)
        .where(sql`${automationPlanProposals.id} = ${BigInt(proposalId)}`);
      expect(row.status).toBe("DRAFT");
    });

    it("agent deployment đã bị pause giữa lúc đề xuất và duyệt -> agent_deployment_unavailable, KHÔNG duyệt", async () => {
      const { f, proposalId, deploymentId } = await seedReadyDraft();
      await pauseProjectDeployment(founderCtx(f), {
        deploymentId,
        kind: "AGENT",
        expectedVersion: 1,
        reason: "test: agent bị dừng giữa lúc chờ duyệt",
      });

      const err = await errorOf(approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId));
      expect(err.code).toBe("failed_precondition");
      expect(err.message).toMatch(/^agent_deployment_unavailable:/);
      expect(err.message).toContain(deploymentId);

      const [row] = await db
        .select()
        .from(automationPlanProposals)
        .where(sql`${automationPlanProposals.id} = ${BigInt(proposalId)}`);
      expect(row.status).toBe("DRAFT");
    });

    it("nháp đã có blocker requires_new_agent (proposeNewAgent) lúc đề xuất -> vẫn not_ready lúc duyệt", async () => {
      const f = await seedFounder();
      await insertVerifiedChannel(f);
      const ctx = founderCtx(f);
      const res = await proposeAutomationPlan(ctx, f.projectId, baseInput({ proposeNewAgent: true }));
      expect(res.data.readiness.ready).toBe(false);

      const err = await errorOf(approveAutomationPlanProposal(ctx, f.projectId, res.data.proposalId));
      expect(err.code).toBe("failed_precondition");
      expect(err.message).toContain("requires_new_agent");
    });
  });

  describe("idempotency", () => {
    it("gọi lại approve khi đã APPROVED mà chưa link lịch -> trả lại ĐÚNG founder đã quyết định lần trước", async () => {
      const { f, proposalId } = await seedReadyDraft();
      const first = await approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId);

      // Retry bằng một ctx khác (giả lập worker gọi lại): kết quả PHẢI vẫn là founder đã duyệt
      // lần đầu, không phải ctx của lần gọi lại.
      const coFounder = await addCoFounderToWorkspace(f);
      const retry = await approveAutomationPlanProposal(founderCtx(coFounder, "co-founder"), f.projectId, proposalId);

      expect(retry.data.founderMemberId).toBe(first.data.founderMemberId);
      expect(retry.data.founderUserId).toBe(first.data.founderUserId);
      expect(retry.data.decidedAt).toBe(first.data.decidedAt);
    });

    it("nháp đã có approved_schedule_id -> already_exists", async () => {
      const { f, proposalId } = await seedReadyDraft();
      await approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId);
      await linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_test_1");

      const err = await errorOf(approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId));
      expect(err.code).toBe("already_exists");
      expect(err.message).toMatch(/^automation_plan_already_linked:/);
    });

    it("nháp đã DISCARDED -> failed_precondition", async () => {
      const { f, proposalId } = await seedReadyDraft();
      await db
        .update(automationPlanProposals)
        .set({ status: "DISCARDED" })
        .where(sql`${automationPlanProposals.id} = ${BigInt(proposalId)}`);

      const err = await errorOf(approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId));
      expect(err.code).toBe("failed_precondition");
      expect(err.message).toMatch(/^automation_plan_discarded:/);
    });
  });
});

describe("automation-plan-approval — link-schedule", () => {
  it("ghi approved_schedule_id sau khi APPROVED", async () => {
    const { f, proposalId } = await seedReadyDraft();
    await approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId);

    const res = await linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_abc");
    expect(res.data).toEqual({ proposalId, approvedScheduleId: "sched_def_abc" });

    const [row] = await db
      .select()
      .from(automationPlanProposals)
      .where(sql`${automationPlanProposals.id} = ${BigInt(proposalId)}`);
    expect(row.approvedScheduleId).toBe("sched_def_abc");
  });

  it("gọi lại link-schedule với ĐÚNG scheduleId -> no-op idempotent", async () => {
    const { f, proposalId } = await seedReadyDraft();
    await approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId);
    await linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_xyz");

    const res = await linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_xyz");
    expect(res.data.approvedScheduleId).toBe("sched_def_xyz");
  });

  it("gọi lại link-schedule với scheduleId KHÁC -> already_exists (không âm thầm ghi đè)", async () => {
    const { f, proposalId } = await seedReadyDraft();
    await approveAutomationPlanProposal(founderCtx(f), f.projectId, proposalId);
    await linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_one");

    const err = await errorOf(linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_two"));
    expect(err.code).toBe("already_exists");

    const [row] = await db
      .select()
      .from(automationPlanProposals)
      .where(sql`${automationPlanProposals.id} = ${BigInt(proposalId)}`);
    expect(row.approvedScheduleId).toBe("sched_def_one");
  });

  it("nháp còn DRAFT (chưa duyệt) -> failed_precondition automation_plan_not_approved", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const err = await errorOf(linkAutomationPlanSchedule(founderCtx(f), f.projectId, proposalId, "sched_def_zzz"));
    expect(err.code).toBe("failed_precondition");
    expect(err.message).toMatch(/^automation_plan_not_approved:/);
  });
});

describe("automation-plan-approval — handler (route founder session, cosa gọi cả 2)", () => {
  it("approveAutomationPlanApi: founder session (bearerToken) duyệt được qua route thật", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const res = await approveAutomationPlanApi({
      authorization: f.bearerToken,
      workspaceId: f.workspaceId,
      projectId: f.projectId,
      proposalId,
    });
    expect(res.data.status).toBe("APPROVED");
    expect(res.data.founderMemberId).toBe(f.memberId);
  });

  it("linkAutomationPlanScheduleApi: founder session ghi được approved_schedule_id", async () => {
    const { f, proposalId } = await seedReadyDraft();
    await approveAutomationPlanApi({
      authorization: f.bearerToken,
      workspaceId: f.workspaceId,
      projectId: f.projectId,
      proposalId,
    });
    const res = await linkAutomationPlanScheduleApi({
      authorization: f.bearerToken,
      workspaceId: f.workspaceId,
      projectId: f.projectId,
      proposalId,
      scheduleId: "sched_def_handler_1",
    });
    expect(res.data.approvedScheduleId).toBe("sched_def_handler_1");
  });

  it("delegation agent gọi route approve -> unauthenticated (founder session mới đọc/ghi được, giống GET B4)", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const err = await errorOf(
      approveAutomationPlanApi({
        authorization: delegationFor(f, [AGENT_CAP.AUTOMATION_PLAN_PROPOSE]),
        workspaceId: f.workspaceId,
        projectId: f.projectId,
        proposalId,
      })
    );
    expect(err.code).toBe("unauthenticated");
  });

  it("member (không phải founder) gọi route approve -> permission_denied", async () => {
    const { f, proposalId } = await seedReadyDraft();
    const member = await addMemberToWorkspace(f.workspaceId, "member");
    const err = await errorOf(
      approveAutomationPlanApi({
        authorization: member.bearerToken,
        workspaceId: f.workspaceId,
        projectId: f.projectId,
        proposalId,
      })
    );
    expect(err.code).toBe("permission_denied");
  });
});
