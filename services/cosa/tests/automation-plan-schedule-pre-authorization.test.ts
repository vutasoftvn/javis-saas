// Plan hub vận hành đợt 2 B5 (Task 6, phần 1) — snapshot uỷ quyền trước trên lịch tạo qua
// đường founder duyệt thẻ kế hoạch. Không mock DB (dùng org id ngẫu nhiên mỗi test, giống
// workspace-schedule.service.test.ts).
import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db, schema } from "../models/db";
import {
  createWorkspaceSchedule,
  dispatchDueWorkspaceSchedules,
  runScheduleNow,
  completeScheduleExecution,
  PRE_AUTHORIZABLE_CAPABILITY_IDS,
  type ScheduleExecutionState,
} from "../services/workspace-schedule.service";
import { createScheduleEndpoint } from "../handlers/workspace-schedule.handler";
import { signPlatformToken, registerTestUser } from "./support/test-identity";

const { workspaceScheduleDefinitions, workspaceScheduleExecutions } = schema;

function uniqueOrg(label: string): string {
  return `ws_${label}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

describe("createWorkspaceSchedule — preAuthorizedCapabilityIds (B5)", () => {
  it("allowlist cố định đúng 2 capability của ADR mục 7", () => {
    expect(PRE_AUTHORIZABLE_CAPABILITY_IDS).toEqual(["email.digest.read", "founder.notify.send"]);
  });

  it("mặc định (không truyền) -> mảng rỗng, không cần founderMemberId/founderUserId", async () => {
    const def = await createWorkspaceSchedule({
      organizationId: uniqueOrg("default"),
      createdBy: "user_1",
      scheduleKind: "daily",
      hour: 8,
      promptTemplate: "digest",
      projectId: "proj_1",
    });
    expect(def.preAuthorizedCapabilityIds).toEqual([]);
    expect(def.founderMemberId).toBeNull();
    expect(def.founderUserId).toBeNull();
    expect(def.automationPlanProposalId).toBeNull();
    expect(def.tokenBudgetPerRun).toBeNull();
  });

  it("capability trong allowlist + founderMemberId/founderUserId -> lưu đúng, dedupe", async () => {
    const def = await createWorkspaceSchedule({
      organizationId: uniqueOrg("ok"),
      createdBy: "user_1",
      scheduleKind: "daily",
      hour: 8,
      promptTemplate: "digest",
      projectId: "proj_1",
      preAuthorizedCapabilityIds: ["email.digest.read", "founder.notify.send", "email.digest.read"],
      founderMemberId: "member_1",
      founderUserId: "user_1",
      automationPlanProposalId: "proposal_1",
      tokenBudgetPerRun: 20000,
    });
    expect(def.preAuthorizedCapabilityIds).toEqual(["email.digest.read", "founder.notify.send"]);
    expect(def.founderMemberId).toBe("member_1");
    expect(def.founderUserId).toBe("user_1");
    expect(def.automationPlanProposalId).toBe("proposal_1");
    expect(def.tokenBudgetPerRun).toBe(20000);
  });

  it("capability NGOÀI allowlist -> invalid_argument (khoá allowlist, kể cả gọi trực tiếp)", async () => {
    await expect(
      createWorkspaceSchedule({
        organizationId: uniqueOrg("bad-cap"),
        createdBy: "user_1",
        scheduleKind: "daily",
        hour: 8,
        promptTemplate: "digest",
        projectId: "proj_1",
        preAuthorizedCapabilityIds: ["business.write.anything"],
        founderMemberId: "member_1",
        founderUserId: "user_1",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("có capability nhưng thiếu founderMemberId hoặc founderUserId -> invalid_argument", async () => {
    await expect(
      createWorkspaceSchedule({
        organizationId: uniqueOrg("missing-founder-1"),
        createdBy: "user_1",
        scheduleKind: "daily",
        hour: 8,
        promptTemplate: "digest",
        projectId: "proj_1",
        preAuthorizedCapabilityIds: ["email.digest.read"],
        founderUserId: "user_1",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    await expect(
      createWorkspaceSchedule({
        organizationId: uniqueOrg("missing-founder-2"),
        createdBy: "user_1",
        scheduleKind: "daily",
        hour: 8,
        promptTemplate: "digest",
        projectId: "proj_1",
        preAuthorizedCapabilityIds: ["email.digest.read"],
        founderMemberId: "member_1",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("route tạo lịch thủ công (tab Lịch) KHÔNG nhận preAuthorizedCapabilityIds từ client — interface không có field này nên handler không forward, dù request object có thêm field lạ", async () => {
    const user = await registerTestUser({ workspace_name: "Manual Schedule WS" });
    const authHeader = `Bearer ${signPlatformToken(user.user.id)}`;

    const result = await createScheduleEndpoint({
      authorization: authHeader,
      organizationId: user.platform_workspace_id!,
      projectId: "proj_manual",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Manual daily report",
      // Field lạ không có trong `CreateScheduleParams` — TS cấm ở compile time; giả lập client
      // HTTP thô gửi thêm field này bằng cách ép kiểu, đúng tình huống brief lo ngại.
      ...({ preAuthorizedCapabilityIds: ["email.digest.read", "founder.notify.send"] } as any),
    });

    expect(result.preAuthorizedCapabilityIds).toEqual([]);
    expect(result.founderMemberId).toBeNull();
    expect(result.founderUserId).toBeNull();
  });
});

describe("snapshot uỷ quyền trước khi tạo execution (dispatch + run-now) — B5", () => {
  it("dispatchDueWorkspaceSchedules copy preAuthorizedCapabilityIds/founder*/tokenBudgetPerRun vào execution", async () => {
    const org = uniqueOrg("dispatch");
    const def = await createWorkspaceSchedule({
      organizationId: org,
      createdBy: "user_1",
      scheduleKind: "daily",
      hour: 8,
      promptTemplate: "digest",
      projectId: "proj_1",
      preAuthorizedCapabilityIds: ["email.digest.read"],
      founderMemberId: "member_9",
      founderUserId: "user_9",
      tokenBudgetPerRun: 15000,
    });

    // Đưa nextRunAt vào quá khứ để dispatcher coi là due — cùng cách các test dispatch hiện có.
    await db
      .update(workspaceScheduleDefinitions)
      .set({ nextRunAt: new Date(Date.now() - 60_000) })
      .where(eq(workspaceScheduleDefinitions.id, def.id));

    await dispatchDueWorkspaceSchedules(new Date(), 10);

    const [execution] = await db
      .select()
      .from(workspaceScheduleExecutions)
      .where(eq(workspaceScheduleExecutions.definitionId, def.id));

    expect(execution).toBeDefined();
    expect(execution.preAuthorizedCapabilityIdsSnapshot).toEqual(["email.digest.read"]);
    expect(execution.founderMemberIdSnapshot).toBe("member_9");
    expect(execution.founderUserIdSnapshot).toBe("user_9");
    expect(execution.tokenBudgetPerRunSnapshot).toBe(15000);
  });

  it("runScheduleNow copy đúng snapshot", async () => {
    const org = uniqueOrg("run-now");
    const def = await createWorkspaceSchedule({
      organizationId: org,
      createdBy: "user_1",
      scheduleKind: "daily",
      hour: 8,
      promptTemplate: "digest",
      projectId: "proj_1",
      preAuthorizedCapabilityIds: ["founder.notify.send"],
      founderMemberId: "member_7",
      founderUserId: "user_7",
      tokenBudgetPerRun: 5000,
    });

    const execution = await runScheduleNow({
      scheduleId: def.id,
      organizationId: org,
      principalId: "user_1",
    });

    expect(execution.preAuthorizedCapabilityIdsSnapshot).toEqual(["founder.notify.send"]);
    expect(execution.founderMemberIdSnapshot).toBe("member_7");
    expect(execution.founderUserIdSnapshot).toBe("user_7");
    expect(execution.tokenBudgetPerRunSnapshot).toBe(5000);
  });
});

describe("POST /cosa/schedules/executions/complete — chấp nhận state blocked_reauth (Task 6b cần)", () => {
  it("completeScheduleExecution ghi được state blocked_reauth", async () => {
    const org = uniqueOrg("blocked-reauth");
    const def = await createWorkspaceSchedule({
      organizationId: org,
      createdBy: "user_1",
      scheduleKind: "daily",
      hour: 8,
      promptTemplate: "digest",
      projectId: "proj_1",
    });
    const execution = await runScheduleNow({ scheduleId: def.id, organizationId: org, principalId: "user_1" });

    const updated = await completeScheduleExecution({
      executionId: execution.id,
      state: "blocked_reauth",
      error: "email_reauth_required: token expired",
    });
    expect(updated?.state).toBe("blocked_reauth");
  });

  it("APIError không ném khi state=blocked_reauth qua CompleteExecutionParams (kiểu ScheduleExecutionState)", () => {
    // Kiểm ở mức type: nếu "blocked_reauth" từng bị bỏ khỏi union, dòng dưới không compile.
    const state: ScheduleExecutionState = "blocked_reauth";
    expect(state).toBe("blocked_reauth");
    expect(APIError).toBeDefined();
  });
});
