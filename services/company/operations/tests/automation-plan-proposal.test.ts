// Plan hub vận hành đợt 2 B4 — capability `automation.plan.propose` (T1, nháp).
// Chạy trên DB test thật (không mock DB). Không gọi mạng: không cần adapter Telegram vì
// đề xuất chỉ TRA trạng thái kênh (resolveUsableChannelForFounder), không gửi gì.
import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { founderNotificationChannels, identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import { FOUNDER_CHANNEL_SECRET_NAMESPACE } from "../../identity/services/founder-channel-secret";
import {
  proposeAutomationPlanApi,
  getAutomationPlanProposalApi,
  type ProposeAutomationPlanParams,
} from "../handlers/automation-plan-proposal.handler";
import {
  MAX_AUTOMATION_PLAN_PROPOSALS_PER_PROJECT_PER_DAY,
  normalizeAutomationSchedule,
  proposeAutomationPlan,
  type ProposeAutomationPlanInput,
} from "../services/automation-plan-proposal.service";
import {
  createTestWorkspaceWithMember,
  deployWorkspaceAgentForProfile,
  makeTestTenantContext,
} from "./_helpers";

const { automationPlanProposals } = schema;

const CHAT_ID = "987654321";

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

function founderCtx(f: Founder) {
  return makeTestTenantContext({
    workspaceId: f.workspaceId,
    userId: f.userId,
    workforceMemberId: f.memberId,
    membershipRole: "founder",
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
    run_id: "run-automation-plan-1",
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

describe("automation.plan.propose — tái dùng agent (quy tắc 3)", () => {
  it("Project có agent operations: tự chọn agent đó, sẵn sàng khi đủ kênh + connector", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    const ctx = founderCtx(f);
    const { deploymentId } = await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");

    const res = await proposeAutomationPlan(ctx, f.projectId, baseInput(), { runId: "run-1" });

    expect(res.data.status).toBe("DRAFT");
    expect(res.data.plan.agentDeploymentId).toBe(deploymentId);
    expect(res.data.plan.proposeNewAgent).toBe(false);
    expect(res.data.plan.agentLabel).toBe("AI operations");
    expect(res.data.plan.skillLabel).toBe("Tóm tắt email chưa đọc");
    expect(res.data.plan.connectors).toEqual([{ key: "email-read", status: "connected" }]);
    expect(res.data.plan.channel).toEqual({ kind: "telegram", label: "Nhóm vận hành", verified: true });
    expect(res.data.plan.capabilityIds).toEqual(["email.digest.read", "founder.notify.send"]);
    expect(res.data.plan.schedule.humanReadable).toBe("Hằng ngày lúc 07:30 (Asia/Ho_Chi_Minh)");
    expect(res.data.readiness).toEqual({ ready: true, blockers: [] });

    const [row] = await db
      .select()
      .from(automationPlanProposals)
      .where(sql`${automationPlanProposals.id} = ${BigInt(res.data.proposalId)}`);
    expect(row.runId).toBe("run-1");
    expect(row.proposedByMemberId.toString()).toBe(f.memberId);
    expect(row.status).toBe("DRAFT");
    expect(row.approvedScheduleId).toBeNull();
  });

  it("chọn đúng agentDeploymentId có sẵn thì được; id lạ -> agent_reuse_required", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    const ctx = founderCtx(f);
    const { deploymentId } = await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");

    const ok = await proposeAutomationPlan(ctx, f.projectId, baseInput({ agentDeploymentId: deploymentId }));
    expect(ok.data.plan.agentDeploymentId).toBe(deploymentId);

    const err = await errorOf(
      proposeAutomationPlan(ctx, f.projectId, baseInput({ agentDeploymentId: "123456789" }))
    );
    expect(err.code).toBe("invalid_argument");
    expect(err.message).toMatch(/^agent_reuse_required:/);
  });

  it("proposeNewAgent bị từ chối khi Project đã có agent khớp profile, message nêu agent có sẵn", async () => {
    const f = await seedFounder();
    const ctx = founderCtx(f);
    const { deploymentId } = await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");

    const err = await errorOf(proposeAutomationPlan(ctx, f.projectId, baseInput({ proposeNewAgent: true })));
    expect(err.code).toBe("invalid_argument");
    expect(err.message).toMatch(/^agent_reuse_required:/);
    expect(err.message).toContain("AI operations");
    expect(err.message).toContain(deploymentId);
  });

  it("agent profile khác (finance) không được tính là khớp", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    const ctx = founderCtx(f);
    await deployWorkspaceAgentForProfile(ctx, f.projectId, "finance");

    const res = await proposeAutomationPlan(ctx, f.projectId, baseInput({ proposeNewAgent: true }));
    expect(res.data.plan.agentDeploymentId).toBeNull();
    expect(res.data.readiness.blockers).toEqual([{ code: "requires_new_agent", target: "agents_tab" }]);
  });

  it("không có agent khớp: proposeNewAgent được chấp nhận kèm blocker requires_new_agent; thiếu cờ -> agent_required", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    const ctx = founderCtx(f);

    const res = await proposeAutomationPlan(ctx, f.projectId, baseInput({ proposeNewAgent: true }));
    expect(res.data.plan.proposeNewAgent).toBe(true);
    expect(res.data.plan.agentDeploymentId).toBeNull();
    expect(res.data.readiness.ready).toBe(false);
    expect(res.data.readiness.blockers).toEqual([{ code: "requires_new_agent", target: "agents_tab" }]);

    const err = await errorOf(proposeAutomationPlan(ctx, f.projectId, baseInput()));
    expect(err.code).toBe("invalid_argument");
    expect(err.message).toMatch(/^agent_required:/);
  });
});

describe("automation.plan.propose — readiness", () => {
  it("chưa có kênh đã xác minh -> blocker founder_channel_unverified (founder_profile)", async () => {
    const f = await seedFounder();
    const ctx = founderCtx(f);
    await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");

    const res = await proposeAutomationPlan(ctx, f.projectId, baseInput());
    expect(res.data.plan.channel).toEqual({ kind: "telegram", label: "Telegram", verified: false });
    expect(res.data.readiness).toEqual({
      ready: false,
      blockers: [{ code: "founder_channel_unverified", target: "founder_profile" }],
    });
  });

  it("connector missing (hoặc không báo trạng thái) -> blocker connector_missing (tools_tab)", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    const ctx = founderCtx(f);
    await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");

    const missing = await proposeAutomationPlan(
      ctx,
      f.projectId,
      baseInput({ connectorStatus: { "email-read": "missing" } })
    );
    expect(missing.data.plan.connectors).toEqual([{ key: "email-read", status: "missing" }]);
    expect(missing.data.readiness.blockers).toEqual([{ code: "connector_missing", target: "tools_tab" }]);

    const unreported = await proposeAutomationPlan(
      ctx,
      f.projectId,
      baseInput({ connectorKeys: [], connectorStatus: undefined })
    );
    expect(unreported.data.plan.connectors).toEqual([{ key: "email-read", status: "missing" }]);
    expect(unreported.data.readiness.ready).toBe(false);
  });

  it("response không chứa chat id / secret_ref / token của kênh", async () => {
    const f = await seedFounder();
    const secretRef = await insertVerifiedChannel(f);
    const ctx = founderCtx(f);
    await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");

    const res = await proposeAutomationPlan(ctx, f.projectId, baseInput());
    const text = JSON.stringify(res);
    expect(text).not.toContain(CHAT_ID);
    expect(text).not.toContain(secretRef);
    expect(text).not.toContain(FOUNDER_CHANNEL_SECRET_NAMESPACE);
    expect(text).not.toMatch(/chatId|secretRef|secret_ref|chat_id/);

    const [row] = await db
      .select()
      .from(automationPlanProposals)
      .where(sql`${automationPlanProposals.id} = ${BigInt(res.data.proposalId)}`);
    const stored = JSON.stringify({ plan: row.plan, readiness: row.readiness });
    expect(stored).not.toContain(CHAT_ID);
    expect(stored).not.toContain(secretRef);
  });
});

describe("automation.plan.propose — quota", () => {
  it("lần thứ 21 trong ngày UTC cùng Project -> resource_exhausted; nháp hôm trước không tính", async () => {
    expect(MAX_AUTOMATION_PLAN_PROPOSALS_PER_PROJECT_PER_DAY).toBe(20);
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    const ctx = founderCtx(f);
    await deployWorkspaceAgentForProfile(ctx, f.projectId, "operations");
    const now = new Date();

    // 1 nháp của hôm trước (UTC) không được tính vào quota hôm nay.
    await db.insert(automationPlanProposals).values({
      id: generateSnowflake(),
      workspaceId: BigInt(f.workspaceId),
      projectId: BigInt(f.projectId),
      proposedByMemberId: BigInt(f.memberId),
      plan: {},
      readiness: {},
      createdAt: new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()) - 1000),
    });

    for (let i = 0; i < 20; i += 1) {
      await proposeAutomationPlan(ctx, f.projectId, baseInput(), { now });
    }
    const err = await errorOf(proposeAutomationPlan(ctx, f.projectId, baseInput(), { now }));
    expect(err.code).toBe("resource_exhausted");
    expect(err.message).toMatch(/^automation_plan_quota_exceeded:/);

    // Project khác (cùng workspace) không bị ảnh hưởng.
    const otherProjectId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.projects (id, workspace_id, title, status, lifecycle_stage)
      VALUES (${otherProjectId}, ${BigInt(f.workspaceId)}, 'Other', 'ACTIVE', 'P0_DISCOVERY')
    `);
    const other = await proposeAutomationPlan(
      ctx,
      otherProjectId.toString(),
      baseInput({ proposeNewAgent: true }),
      { now }
    );
    expect(other.data.status).toBe("DRAFT");
  });
});

describe("automation.plan.propose — validate input", () => {
  it("skillId lạ -> invalid_argument", async () => {
    const f = await seedFounder();
    const ctx = founderCtx(f);
    const err = await errorOf(proposeAutomationPlan(ctx, f.projectId, baseInput({ skillId: "operations.payout" })));
    expect(err.code).toBe("invalid_argument");
    expect(err.message).toMatch(/^automation_plan_invalid: skillId/);
  });

  it.each<[string, Partial<ProposeAutomationPlanInput>]>([
    ["connector ngoài skill", { connectorKeys: ["email-read", "slack"] }],
    ["connectorStatus key lạ", { connectorStatus: { stripe: "connected" } }],
    ["connectorStatus value lạ", { connectorStatus: { "email-read": "ok" } }],
    ["channelKind lạ", { channelKind: "sms" }],
    ["token budget 0", { tokenBudgetPerRun: 0 }],
    ["token budget quá trần", { tokenBudgetPerRun: 200001 }],
    ["token budget lẻ", { tokenBudgetPerRun: 10.5 }],
    ["timezone sai", { schedule: { kind: "daily", hour: 7, timezone: "Mars/Olympus" } }],
    ["giờ 24", { schedule: { kind: "daily", hour: 24, timezone: "UTC" } }],
    ["phút 60", { schedule: { kind: "daily", hour: 7, minute: 60, timezone: "UTC" } }],
    ["weekdays rỗng", { schedule: { kind: "weekdays", hour: 7, weekdays: [], timezone: "UTC" } }],
    ["weekdays 8", { schedule: { kind: "weekdays", hour: 7, weekdays: [1, 8], timezone: "UTC" } }],
    ["one_time quá khứ", { schedule: { kind: "one_time", runAt: "2020-01-01T00:00:00Z", timezone: "UTC" } }],
    ["kind lạ", { schedule: { kind: "hourly" as never, hour: 1, timezone: "UTC" } }],
    ["vừa chọn agent vừa đề xuất mới", { agentDeploymentId: "1", proposeNewAgent: true }],
  ])("%s -> invalid_argument", async (_name, overrides) => {
    const f = await seedFounder();
    const err = await errorOf(proposeAutomationPlan(founderCtx(f), f.projectId, baseInput(overrides)));
    expect(err.code).toBe("invalid_argument");
  });

  it("chuẩn hoá lịch weekdays + one_time kèm mô tả dễ đọc", () => {
    const now = new Date("2026-09-28T00:00:00Z");
    expect(
      normalizeAutomationSchedule({ kind: "weekdays", hour: 8, weekdays: [5, 1, 3], timezone: "Asia/Ho_Chi_Minh" }, now)
    ).toEqual({
      kind: "weekdays",
      timezone: "Asia/Ho_Chi_Minh",
      hour: 8,
      minute: 0,
      weekdays: [1, 3, 5],
      runAt: null,
      humanReadable: "Thứ 2, Thứ 4, Thứ 6 lúc 08:00 (Asia/Ho_Chi_Minh)",
    });
    expect(
      normalizeAutomationSchedule(
        { kind: "one_time", runAt: "2026-10-01T00:30:00Z", timezone: "Asia/Ho_Chi_Minh" },
        now
      ).humanReadable
    ).toBe("Một lần lúc 2026-10-01 07:30 (Asia/Ho_Chi_Minh)");
  });
});

describe("automation.plan.propose — handler + quyền", () => {
  function params(f: Founder, authorization: string, extra: Partial<ProposeAutomationPlanParams> = {}) {
    return {
      authorization,
      workspaceId: f.workspaceId,
      projectId: f.projectId,
      ...baseInput(),
      ...extra,
    } as ProposeAutomationPlanParams;
  }

  it("delegation có capability: founder = danh tính delegation, run id từ header", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    await deployWorkspaceAgentForProfile(founderCtx(f), f.projectId, "operations");

    const res = await proposeAutomationPlanApi(
      params(f, delegationFor(f, [AGENT_CAP.AUTOMATION_PLAN_PROPOSE]), { runId: "run-hdr-9" })
    );
    expect(res.data.readiness.ready).toBe(true);
    const [row] = await db
      .select()
      .from(automationPlanProposals)
      .where(sql`${automationPlanProposals.id} = ${BigInt(res.data.proposalId)}`);
    expect(row.proposedByMemberId.toString()).toBe(f.memberId);
    expect(row.runId).toBe("run-hdr-9");
  });

  it("delegation thiếu capability -> permission_denied", async () => {
    const f = await seedFounder();
    const err = await errorOf(proposeAutomationPlanApi(params(f, delegationFor(f, [AGENT_CAP.FOUNDER_NOTIFY_SEND]))));
    expect(err.code).toBe("permission_denied");
  });

  it("role không phải founder -> founder_owner_not_authorized", async () => {
    const f = await seedFounder("member");
    const err = await errorOf(
      proposeAutomationPlanApi(params(f, delegationFor(f, [AGENT_CAP.AUTOMATION_PLAN_PROPOSE])))
    );
    expect(err.code).toBe("permission_denied");
    expect(err.message).toMatch(/^founder_owner_not_authorized:/);
  });

  it("GET: founder nạp lại nháp của mình; project khác / id lạ -> not_found", async () => {
    const f = await seedFounder();
    await insertVerifiedChannel(f);
    await deployWorkspaceAgentForProfile(founderCtx(f), f.projectId, "operations");
    const created = await proposeAutomationPlanApi(
      params(f, delegationFor(f, [AGENT_CAP.AUTOMATION_PLAN_PROPOSE]))
    );

    const got = await getAutomationPlanProposalApi({
      authorization: f.bearerToken,
      workspaceId: f.workspaceId,
      projectId: f.projectId,
      proposalId: created.data.proposalId,
    });
    expect(got.data).toEqual(created.data);

    const wrongProject = await errorOf(
      getAutomationPlanProposalApi({
        authorization: f.bearerToken,
        workspaceId: f.workspaceId,
        projectId: "42",
        proposalId: created.data.proposalId,
      })
    );
    expect(wrongProject.code).toBe("not_found");

    // Delegation agent không đọc được qua route founder-session.
    const byAgent = await errorOf(
      getAutomationPlanProposalApi({
        authorization: delegationFor(f, [AGENT_CAP.AUTOMATION_PLAN_PROPOSE]),
        workspaceId: f.workspaceId,
        projectId: f.projectId,
        proposalId: created.data.proposalId,
      })
    );
    // resolveTenantContext coi delegation ở endpoint không khai báo capability là token không hợp lệ.
    expect(byAgent.code).toBe("unauthenticated");
  });
});
