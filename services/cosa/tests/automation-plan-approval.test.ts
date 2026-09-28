// Plan hub vận hành đợt 2 B5 (Task 6, phần 1) — services/cosa tạo lịch sau khi services/company
// duyệt nháp kế hoạch. Mock fetch tới services/company (cùng cách core-organization.test.ts mock
// gọi core: vi.stubGlobal("fetch", ...)) — không cần app company chạy thật.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { approveAutomationPlan } from "../services/automation-plan-approval.service";
import * as repo from "../services/schedule/schedule.repository";

const { workspaceConnectorInstallations, connectorAuthorizations, workspaceScheduleDefinitions } = schema;

const COMPANY_URL = "http://company.test";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function uniqueId(label: string): string {
  return `${label}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

async function seedActiveConnectorAuthorization(organizationId: string, connectorKey: string): Promise<string> {
  const installId = uniqueId("conn_inst");
  await db.insert(workspaceConnectorInstallations).values({
    id: installId,
    organizationId,
    connectorKey,
    installedBy: "user_seed",
    status: "enabled",
  });
  const authId = uniqueId("conn_auth");
  await db.insert(connectorAuthorizations).values({
    id: authId,
    installationId: installId,
    principalId: "user_seed",
    secretRef: "secret://cosa-connectors/test/email-read",
    grantedScopes: ["mail:read"],
    state: "active",
    expiresAt: new Date(Date.now() + 3600_000),
    organizationId,
  });
  return authId;
}

function companyPlanFixture(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    agentDeploymentId: "dep_1",
    agentLabel: "AI operations",
    proposeNewAgent: false,
    skillId: "operations.email-digest",
    skillLabel: "Tóm tắt email chưa đọc",
    connectors: [{ key: "email-read", status: "connected" }],
    channel: { kind: "telegram", label: "Nhóm vận hành", verified: true },
    schedule: {
      kind: "daily",
      timezone: "Asia/Ho_Chi_Minh",
      hour: 7,
      minute: 30,
      weekdays: [],
      runAt: null,
      humanReadable: "Hằng ngày lúc 07:30 (Asia/Ho_Chi_Minh)",
    },
    tokenBudgetPerRun: 20000,
    capabilityIds: ["email.digest.read", "founder.notify.send"],
    ...overrides,
  };
}

function companyApproveFixture(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    data: {
      proposalId: "prop_1",
      projectId: "proj_1",
      status: "APPROVED",
      plan: companyPlanFixture(),
      capabilityIds: ["email.digest.read", "founder.notify.send"],
      founderMemberId: "member_1",
      founderUserId: "user_1",
      decidedAt: new Date().toISOString(),
      ...overrides,
    },
    meta: { dataState: "populated", observedAt: new Date().toISOString(), sources: [] },
  };
}

describe("approveAutomationPlan (B5) — services/cosa tạo lịch sau khi company duyệt", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    process.env.COMPANY_SERVICE_URL = COMPANY_URL;
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("tạo lịch với connectorGrantIds THẬT (authorization id vừa re-verify, không phải chuỗi founder tự khai) + snapshot uỷ quyền trước", async () => {
    const org = uniqueId("ws");
    const authId = await seedActiveConnectorAuthorization(org, "email-read");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: "prop_a" })))
      .mockResolvedValueOnce(jsonResponse({ data: { proposalId: "prop_a", approvedScheduleId: "will-be-set" } }));

    const schedule = await approveAutomationPlan({
      organizationId: org,
      projectId: "proj_a",
      proposalId: "prop_a",
      authorization: "Bearer founder-session-token",
    });

    expect(schedule.connectorGrantIds).toEqual([authId]);
    expect(schedule.preAuthorizedCapabilityIds).toEqual(["email.digest.read", "founder.notify.send"]);
    expect(schedule.founderMemberId).toBe("member_1");
    expect(schedule.founderUserId).toBe("user_1");
    expect(schedule.automationPlanProposalId).toBe("prop_a");
    expect(schedule.tokenBudgetPerRun).toBe(20000);
    expect(schedule.scheduleKind).toBe("daily");
    expect(schedule.timezone).toBe("Asia/Ho_Chi_Minh");
    expect(schedule.hour).toBe(7);
    expect(schedule.minute).toBe(30);
    expect(schedule.promptTemplate).toContain("email-digest");
    expect(schedule.promptTemplate).toContain("Nhóm vận hành");
    expect(schedule.promptTemplate).not.toContain("undefined");
    expect(schedule.createdBy).toBe("user_1");

    // Gọi đúng 2 lần: approve rồi link-schedule, forward Authorization + X-Workspace-Id.
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const [approveUrl, approveInit] = fetchMock.mock.calls[0];
    expect(approveUrl).toBe(`${COMPANY_URL}/operations/projects/proj_a/automation-plans/proposals/prop_a/approve`);
    expect(approveInit.headers.Authorization).toBe("Bearer founder-session-token");
    expect(approveInit.headers["X-Workspace-Id"]).toBe(org);

    const [linkUrl, linkInit] = fetchMock.mock.calls[1];
    expect(linkUrl).toBe(
      `${COMPANY_URL}/operations/projects/proj_a/automation-plans/proposals/prop_a/link-schedule`
    );
    expect(JSON.parse(linkInit.body)).toEqual({ scheduleId: schedule.id });
  });

  it("connector chưa kết nối thật (KHÔNG tin plan.connectors[].status của nháp) -> failed_precondition, KHÔNG tạo lịch", async () => {
    const org = uniqueId("ws");
    // KHÔNG seed connectorAuthorizations — company vẫn báo status "connected" (cũ, hết hiệu lực).
    fetchMock.mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: "prop_b" })));

    await expect(
      approveAutomationPlan({
        organizationId: org,
        projectId: "proj_b",
        proposalId: "prop_b",
        authorization: "Bearer founder-session-token",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });

    // Không gọi link-schedule (chỉ 1 lần fetch: approve).
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const rows = await db
      .select()
      .from(workspaceScheduleDefinitions)
      .where(eq(workspaceScheduleDefinitions.organizationId, org));
    expect(rows).toHaveLength(0);
  });

  it("thiếu Authorization -> unauthenticated, không gọi company", async () => {
    await expect(
      approveAutomationPlan({
        organizationId: uniqueId("ws"),
        projectId: "proj_c",
        proposalId: "prop_c",
        authorization: undefined,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("company approve trả lỗi (permission_denied) -> propagate đúng mã lỗi", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ code: "permission_denied", message: "founder_owner_not_authorized: ...", details: null }, 403)
    );
    await expect(
      approveAutomationPlan({
        organizationId: uniqueId("ws"),
        projectId: "proj_d",
        proposalId: "prop_d",
        authorization: "Bearer x",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("idempotent: đã có lịch cho đúng proposalId này -> KHÔNG gọi lại approve, chỉ retry link-schedule", async () => {
    const org = uniqueId("ws");
    const authId = await seedActiveConnectorAuthorization(org, "email-read");
    // Lần đầu tạo lịch thành công.
    fetchMock
      .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: "prop_e" })))
      .mockResolvedValueOnce(jsonResponse({ data: { proposalId: "prop_e", approvedScheduleId: "x" } }));
    const first = await approveAutomationPlan({
      organizationId: org,
      projectId: "proj_e",
      proposalId: "prop_e",
      authorization: "Bearer founder-session-token",
    });
    expect(first.connectorGrantIds).toEqual([authId]);

    // Retry (giả lập lần link-schedule trước đó lỗi giữa đường): KHÔNG được tạo lịch thứ 2.
    fetchMock.mockClear();
    fetchMock.mockResolvedValueOnce(jsonResponse({ data: { proposalId: "prop_e", approvedScheduleId: "x" } }));
    const retry = await approveAutomationPlan({
      organizationId: org,
      projectId: "proj_e",
      proposalId: "prop_e",
      authorization: "Bearer founder-session-token",
    });
    expect(retry.id).toBe(first.id);
    expect(fetchMock).toHaveBeenCalledTimes(1); // chỉ link-schedule, không gọi lại approve
    expect(fetchMock.mock.calls[0][0]).toBe(
      `${COMPANY_URL}/operations/projects/proj_e/automation-plans/proposals/prop_e/link-schedule`
    );

    const found = await repo.findScheduleDefinitionByProposalId(org, "prop_e");
    expect(found?.id).toBe(first.id);
  });

  it("link-schedule thất bại (company lỗi hạ tầng) -> internal, nhưng lịch đã tạo vẫn còn (retry sẽ tự khớp lại)", async () => {
    const org = uniqueId("ws");
    await seedActiveConnectorAuthorization(org, "email-read");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: "prop_f" })))
      .mockResolvedValueOnce(jsonResponse({ code: "internal", message: "db down" }, 500));

    await expect(
      approveAutomationPlan({
        organizationId: org,
        projectId: "proj_f",
        proposalId: "prop_f",
        authorization: "Bearer founder-session-token",
      })
    ).rejects.toMatchObject({ code: "internal" });

    const found = await repo.findScheduleDefinitionByProposalId(org, "prop_f");
    expect(found).toBeDefined();
  });

  it("nhiều connector cần thiết: mỗi connector đều phải có authorization active riêng", async () => {
    const org = uniqueId("ws");
    const emailAuthId = await seedActiveConnectorAuthorization(org, "email-read");
    // Không seed "calendar-read" — mô phỏng skill cần 2 connector, thiếu 1.
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        companyApproveFixture({
          proposalId: "prop_g",
          plan: companyPlanFixture({
            connectors: [
              { key: "email-read", status: "connected" },
              { key: "calendar-read", status: "connected" },
            ],
          }),
        })
      )
    );

    await expect(
      approveAutomationPlan({
        organizationId: org,
        projectId: "proj_g",
        proposalId: "prop_g",
        authorization: "Bearer founder-session-token",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
    void emailAuthId;
  });
});
