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

// `principalId` mặc định "user_1" khớp `founderUserId` trong `companyApproveFixture` — fix review
// "Needs fixes" Critical 1 đòi `findActiveConnectorAuthorizationIds` lọc đúng principal, nên các
// test approve mặc định phải seed authorization CHO ĐÚNG founder đang duyệt.
//
// `organization_connector_installations` có UNIQUE (organization_id, connector_key) — một
// installation dùng chung cho NHIỀU principal (nhiều authorization trỏ vào cùng 1 installation,
// giống cách `registerConnectorAuthorization` thật hoạt động), nên tái dùng installation nếu đã
// có cho đúng org+connectorKey thay vì tạo installation mới mỗi lần gọi.
const installationCache = new Map<string, string>();

async function seedActiveConnectorAuthorization(
  organizationId: string,
  connectorKey: string,
  principalId = "user_1"
): Promise<string> {
  const cacheKey = `${organizationId}:${connectorKey}`;
  let installId = installationCache.get(cacheKey);
  if (!installId) {
    installId = uniqueId("conn_inst");
    await db.insert(workspaceConnectorInstallations).values({
      id: installId,
      organizationId,
      connectorKey,
      installedBy: principalId,
      status: "enabled",
    });
    installationCache.set(cacheKey, installId);
  }
  const authId = uniqueId("conn_auth");
  await db.insert(connectorAuthorizations).values({
    id: authId,
    installationId: installId,
    principalId,
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
    const propA = uniqueId("prop");
    const authId = await seedActiveConnectorAuthorization(org, "email-read");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: propA })))
      .mockResolvedValueOnce(jsonResponse({ data: { proposalId: propA, approvedScheduleId: "will-be-set" } }));

    const schedule = await approveAutomationPlan({
      organizationId: org,
      projectId: "proj_a",
      proposalId: propA,
      authorization: "Bearer founder-session-token",
    });

    expect(schedule.connectorGrantIds).toEqual([authId]);
    expect(schedule.preAuthorizedCapabilityIds).toEqual(["email.digest.read", "founder.notify.send"]);
    expect(schedule.founderMemberId).toBe("member_1");
    expect(schedule.founderUserId).toBe("user_1");
    expect(schedule.automationPlanProposalId).toBe(propA);
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
    expect(approveUrl).toBe(`${COMPANY_URL}/operations/projects/proj_a/automation-plans/proposals/${propA}/approve`);
    expect(approveInit.headers.Authorization).toBe("Bearer founder-session-token");
    expect(approveInit.headers["X-Workspace-Id"]).toBe(org);

    const [linkUrl, linkInit] = fetchMock.mock.calls[1];
    expect(linkUrl).toBe(
      `${COMPANY_URL}/operations/projects/proj_a/automation-plans/proposals/${propA}/link-schedule`
    );
    expect(JSON.parse(linkInit.body)).toEqual({ scheduleId: schedule.id });
  });

  it("connector chưa kết nối thật (KHÔNG tin plan.connectors[].status của nháp) -> failed_precondition, KHÔNG tạo lịch", async () => {
    const org = uniqueId("ws");
    const propB = uniqueId("prop");
    // KHÔNG seed connectorAuthorizations — company vẫn báo status "connected" (cũ, hết hiệu lực).
    fetchMock.mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: propB })));

    await expect(
      approveAutomationPlan({
        organizationId: org,
        projectId: "proj_b",
        proposalId: propB,
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
    const propC = uniqueId("prop");
    await expect(
      approveAutomationPlan({
        organizationId: uniqueId("ws"),
        projectId: "proj_c",
        proposalId: propC,
        authorization: undefined,
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("company approve trả lỗi (permission_denied) -> propagate đúng mã lỗi", async () => {
    const propD = uniqueId("prop");
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ code: "permission_denied", message: "founder_owner_not_authorized: ...", details: null }, 403)
    );
    await expect(
      approveAutomationPlan({
        organizationId: uniqueId("ws"),
        projectId: "proj_d",
        proposalId: propD,
        authorization: "Bearer x",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("idempotent: đã có lịch cho đúng proposalId này -> KHÔNG gọi lại approve, chỉ retry link-schedule", async () => {
    const org = uniqueId("ws");
    const propE = uniqueId("prop");
    const authId = await seedActiveConnectorAuthorization(org, "email-read");
    // Lần đầu tạo lịch thành công.
    fetchMock
      .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: propE })))
      .mockResolvedValueOnce(jsonResponse({ data: { proposalId: propE, approvedScheduleId: "x" } }));
    const first = await approveAutomationPlan({
      organizationId: org,
      projectId: "proj_e",
      proposalId: propE,
      authorization: "Bearer founder-session-token",
    });
    expect(first.connectorGrantIds).toEqual([authId]);

    // Retry (giả lập lần link-schedule trước đó lỗi giữa đường): KHÔNG được tạo lịch thứ 2.
    fetchMock.mockClear();
    fetchMock.mockResolvedValueOnce(jsonResponse({ data: { proposalId: propE, approvedScheduleId: "x" } }));
    const retry = await approveAutomationPlan({
      organizationId: org,
      projectId: "proj_e",
      proposalId: propE,
      authorization: "Bearer founder-session-token",
    });
    expect(retry.id).toBe(first.id);
    expect(fetchMock).toHaveBeenCalledTimes(1); // chỉ link-schedule, không gọi lại approve
    expect(fetchMock.mock.calls[0][0]).toBe(
      `${COMPANY_URL}/operations/projects/proj_e/automation-plans/proposals/${propE}/link-schedule`
    );

    const found = await repo.findScheduleDefinitionByProposalId(org, propE);
    expect(found?.id).toBe(first.id);
  });

  it("link-schedule thất bại (company lỗi hạ tầng) -> internal, nhưng lịch đã tạo vẫn còn (retry sẽ tự khớp lại)", async () => {
    const org = uniqueId("ws");
    const propF = uniqueId("prop");
    await seedActiveConnectorAuthorization(org, "email-read");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: propF })))
      .mockResolvedValueOnce(jsonResponse({ code: "internal", message: "db down" }, 500));

    await expect(
      approveAutomationPlan({
        organizationId: org,
        projectId: "proj_f",
        proposalId: propF,
        authorization: "Bearer founder-session-token",
      })
    ).rejects.toMatchObject({ code: "internal" });

    const found = await repo.findScheduleDefinitionByProposalId(org, propF);
    expect(found).toBeDefined();
  });

  it("nhiều connector cần thiết: mỗi connector đều phải có authorization active riêng", async () => {
    const org = uniqueId("ws");
    const propG = uniqueId("prop");
    const emailAuthId = await seedActiveConnectorAuthorization(org, "email-read");
    // Không seed "calendar-read" — mô phỏng skill cần 2 connector, thiếu 1.
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        companyApproveFixture({
          proposalId: propG,
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
        proposalId: propG,
        authorization: "Bearer founder-session-token",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
    void emailAuthId;
  });

  describe("fix review Needs fixes — Critical 1: connector re-verify PHẢI lọc theo principal", () => {
    it("founder A đã connect email-read, founder B duyệt (B chưa connect) -> KHÔNG được mượn authorization của A", async () => {
      const org = uniqueId("ws");
      const propH = uniqueId("prop");
      // Founder A (principal khác) đã connect — KHÔNG phải người đang duyệt kế hoạch này.
      await seedActiveConnectorAuthorization(org, "email-read", "user_founder_A");
      fetchMock.mockResolvedValueOnce(
        jsonResponse(companyApproveFixture({ proposalId: propH, founderUserId: "user_founder_B" }))
      );

      await expect(
        approveAutomationPlan({
          organizationId: org,
          projectId: "proj_h",
          proposalId: propH,
          authorization: "Bearer founder-B-session-token",
        })
      ).rejects.toMatchObject({ code: "failed_precondition" });

      // Không tạo lịch nào — nhất là không tạo lịch mượn connectorGrantIds của A.
      const rows = await db
        .select()
        .from(workspaceScheduleDefinitions)
        .where(eq(workspaceScheduleDefinitions.organizationId, org));
      expect(rows).toHaveLength(0);
    });

    it("founder B tự connect email-read của chính mình -> duyệt được, connectorGrantIds là authorization của B (không phải A)", async () => {
      const org = uniqueId("ws");
      const propI = uniqueId("prop");
      await seedActiveConnectorAuthorization(org, "email-read", "user_founder_A");
      const authIdOfB = await seedActiveConnectorAuthorization(org, "email-read", "user_founder_B");
      fetchMock
        .mockResolvedValueOnce(
          jsonResponse(companyApproveFixture({ proposalId: propI, founderUserId: "user_founder_B" }))
        )
        .mockResolvedValueOnce(jsonResponse({ data: { proposalId: propI, approvedScheduleId: "x" } }));

      const schedule = await approveAutomationPlan({
        organizationId: org,
        projectId: "proj_i",
        proposalId: propI,
        authorization: "Bearer founder-B-session-token",
      });

      expect(schedule.connectorGrantIds).toEqual([authIdOfB]);
      expect(schedule.founderUserId).toBe("user_founder_B");
    });
  });

  describe("fix review Needs fixes — Critical 2: race 2 request approve đồng thời", () => {
    it("Promise.all 2 lần approveAutomationPlan cùng proposalId -> chỉ 1 lịch được tạo (UNIQUE INDEX + fallback đọc lại)", async () => {
      const org = uniqueId("ws");
      const propRace = uniqueId("prop");
      await seedActiveConnectorAuthorization(org, "email-read", "user_1");

      // Cả 2 request đều thấy proposal chưa có lịch (idempotency check ban đầu rỗng ở cả 2), rồi
      // cả 2 đều gọi company approve thành công (company APPROVED là idempotent, không phải điểm
      // race cần kiểm ở đây — race nằm ở bước createWorkspaceSchedule phía cosa).
      fetchMock
        .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: propRace })))
        .mockResolvedValueOnce(jsonResponse(companyApproveFixture({ proposalId: propRace })))
        .mockResolvedValueOnce(jsonResponse({ data: { proposalId: propRace, approvedScheduleId: "x" } }))
        .mockResolvedValueOnce(jsonResponse({ data: { proposalId: propRace, approvedScheduleId: "x" } }));

      const input = {
        organizationId: org,
        projectId: "proj_race",
        proposalId: propRace,
        authorization: "Bearer founder-session-token",
      };

      const [a, b] = await Promise.all([approveAutomationPlan(input), approveAutomationPlan(input)]);

      // Cả 2 lần gọi PHẢI trả về đúng 1 lịch (id giống nhau) — không phải mỗi lần một lịch riêng.
      expect(a.id).toBe(b.id);

      const rows = await db
        .select()
        .from(workspaceScheduleDefinitions)
        .where(eq(workspaceScheduleDefinitions.organizationId, org));
      expect(rows).toHaveLength(1);
      expect(rows[0].automationPlanProposalId).toBe(propRace);
    });
  });
});
