// Plan hub vận hành đợt 2 B5 (Task 6, phần 1) — founder bấm Duyệt thẻ kế hoạch tự động hoá
// (services/company B4 `operating.automation_plan_proposals`) MỘT LẦN, services/cosa tạo lịch
// có snapshot uỷ quyền trước. Luồng:
//   1. Forward Authorization (phiên founder) sang services/company
//      `POST /operations/projects/:projectId/automation-plans/proposals/:id/approve` — company
//      chuyển status DRAFT -> APPROVED sau khi re-verify kênh + agent deployment, trả về
//      plan/capabilityIds/founderMemberId/founderUserId. KHÔNG nhận dữ liệu lịch nào khác từ
//      client ngoài `proposalId` (không tin lại `plan` cũ do client gửi lên).
//   2. Re-verify connector THẬT (phát hiện review Task 5 mục 1) — bảng `connectorAuthorizations`
//      sống ở services/cosa, company không đọc được. Không có authorization active nào cho một
//      connector key mà skill cần ⇒ từ chối, KHÔNG tạo lịch.
//   3. Dựng `promptTemplate` từ skill + plan (hằng số/hàm ở đây, KHÔNG nhận từ client).
//   4. `createWorkspaceSchedule` với `connectorGrantIds` THẬT (authorization id vừa re-verify,
//      không phải chuỗi founder tự khai) + snapshot uỷ quyền trước (`preAuthorizedCapabilityIds`
//      = `capabilityIds` company trả về, `founderMemberId`/`founderUserId` = người đã bấm duyệt).
//   5. Gọi `link-schedule` để company ghi `approved_schedule_id`.
// Idempotent: nếu đã có lịch cho đúng `proposalId` này (approve bị gọi lại giữa lúc tạo lịch xong
// và link-schedule thất bại) thì KHÔNG tạo lịch thứ hai — chỉ retry link-schedule.
import { APIError } from "encore.dev/api";
import * as repo from "./schedule/schedule.repository";
import {
  createWorkspaceSchedule,
  type ScheduleKind,
} from "./workspace-schedule.service";
import { findActiveConnectorAuthorizationIds, resolveCompanyServiceUrl } from "./workspace-connector.service";

// Đọc tối đa bao nhiêu email chưa đọc — khớp DEFAULT_MAX_RESULTS ở
// apps/cosa/capabilities/email_digest_read.py. Hai hằng số này KHÔNG chia sẻ được qua ranh giới
// TypeScript/Python; đổi một bên phải đổi bên kia (ghi lại ở CONCERNS report Task 6).
const EMAIL_DIGEST_DEFAULT_MAX_RESULTS = 20;

interface CompanyAutomationPlanConnector {
  key: string;
  status: "connected" | "missing";
}

interface CompanyAutomationPlanChannel {
  kind: string;
  label: string;
  verified: boolean;
}

interface CompanyAutomationPlanSchedule {
  kind: ScheduleKind;
  timezone: string;
  hour: number | null;
  minute: number | null;
  weekdays: number[];
  runAt: string | null;
  humanReadable: string;
}

interface CompanyAutomationPlan {
  agentDeploymentId: string | null;
  agentLabel: string;
  proposeNewAgent: boolean;
  skillId: string;
  skillLabel: string;
  connectors: CompanyAutomationPlanConnector[];
  channel: CompanyAutomationPlanChannel;
  schedule: CompanyAutomationPlanSchedule;
  tokenBudgetPerRun: number;
  capabilityIds: string[];
}

interface CompanyApprovalData {
  proposalId: string;
  projectId: string;
  status: "APPROVED";
  plan: CompanyAutomationPlan;
  capabilityIds: string[];
  founderMemberId: string;
  founderUserId: string;
  decidedAt: string;
}

// Nhãn agent profile theo skill — chỉ khớp catalog skill hiện có (services/company
// `AUTOMATION_PLAN_SKILLS`, chỉ 1 skill `operations.email-digest` lúc viết task này). Không import
// được trực tiếp từ services/company (ranh giới service); nếu company thêm skill mới thì phải cập
// nhật cả 2 chỗ (ghi lại ở CONCERNS report).
const SKILL_AGENT_PROFILE: Record<string, string> = {
  "operations.email-digest": "operations",
};

const SKILL_PROMPT_BUILDERS: Record<string, (plan: CompanyAutomationPlan) => string> = {
  "operations.email-digest": (plan) =>
    `Chạy skill email-digest: đọc tối đa ${EMAIL_DIGEST_DEFAULT_MAX_RESULTS} email chưa đọc, ` +
    `tóm tắt theo người gửi/chủ đề, rồi gửi bản tóm tắt vào kênh ${plan.channel.label} của founder ` +
    `qua founder.notify.send. Không gửi cho ai khác ngoài founder, không đọc quá số email cho phép.`,
};

function buildAutomationPlanPrompt(plan: CompanyAutomationPlan): string {
  const builder = SKILL_PROMPT_BUILDERS[plan.skillId];
  if (!builder) {
    // Không nên xảy ra: company đã validate skillId theo đúng allowlist AUTOMATION_PLAN_SKILLS.
    throw APIError.internal(`automation_plan_unknown_skill: ${plan.skillId}`);
  }
  return builder(plan);
}

async function callCompanyApprove(input: {
  organizationId: string;
  projectId: string;
  proposalId: string;
  authorization: string;
}): Promise<CompanyApprovalData> {
  const url = `${resolveCompanyServiceUrl()}/operations/projects/${encodeURIComponent(
    input.projectId
  )}/automation-plans/proposals/${encodeURIComponent(input.proposalId)}/approve`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: input.authorization,
      "X-Workspace-Id": input.organizationId,
    },
    body: JSON.stringify({}),
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const message = typeof body?.message === "string" ? body.message : `HTTP ${resp.status}`;
    const code = typeof body?.code === "string" ? body.code : "unknown";
    throw errorFromCompanyCode(code, `automation_plan_approve_upstream: ${message}`);
  }
  return body.data as CompanyApprovalData;
}

async function callCompanyLinkSchedule(input: {
  organizationId: string;
  projectId: string;
  proposalId: string;
  authorization: string;
  scheduleId: string;
}): Promise<void> {
  const url = `${resolveCompanyServiceUrl()}/operations/projects/${encodeURIComponent(
    input.projectId
  )}/automation-plans/proposals/${encodeURIComponent(input.proposalId)}/link-schedule`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: input.authorization,
      "X-Workspace-Id": input.organizationId,
    },
    body: JSON.stringify({ scheduleId: input.scheduleId }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const message = typeof body?.message === "string" ? body.message : `HTTP ${resp.status}`;
    // Lịch đã tạo thật rồi — không rollback (schedule đã có promptTemplate đúng). Founder/worker
    // gọi lại approve sẽ tự khớp lại nhờ findScheduleDefinitionByProposalId và retry link-schedule.
    throw APIError.internal(`automation_plan_link_schedule_failed: ${message}`);
  }
}

// company trả lỗi theo khuôn Encore { code, message, details }. `code` ở đây là ErrCode string
// value ("not_found", "invalid_argument", ...) — map lại sang APIError cùng mã để cosa's caller
// (Flutter Task 7) nhận đúng HTTP status như company đã quyết định, chỉ bọc thêm tiền tố truy vết.
const ERR_FACTORY_BY_CODE: Record<string, (msg: string) => APIError> = {
  not_found: APIError.notFound,
  invalid_argument: APIError.invalidArgument,
  failed_precondition: APIError.failedPrecondition,
  permission_denied: APIError.permissionDenied,
  already_exists: APIError.alreadyExists,
  unauthenticated: APIError.unauthenticated,
  resource_exhausted: APIError.resourceExhausted,
};

function errorFromCompanyCode(code: string, message: string): APIError {
  const factory = ERR_FACTORY_BY_CODE[code] || APIError.internal;
  return factory(message);
}

export interface ApproveAutomationPlanInput {
  organizationId: string;
  projectId: string;
  proposalId: string;
  authorization: string | undefined;
}

export async function approveAutomationPlan(
  input: ApproveAutomationPlanInput
): Promise<repo.ScheduleDefinitionRow> {
  if (!input.authorization) {
    throw APIError.unauthenticated("missing authorization header");
  }
  if (!input.projectId || !input.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }

  // Idempotency: approve đã tạo lịch thành công lần trước (chỉ link-schedule bị lỗi giữa
  // đường) — KHÔNG tạo lịch thứ hai, chỉ thử lại link-schedule.
  const existing = await repo.findScheduleDefinitionByProposalId(input.organizationId, input.proposalId);
  if (existing) {
    await callCompanyLinkSchedule({ ...input, authorization: input.authorization, scheduleId: existing.id });
    return existing;
  }

  const approval = await callCompanyApprove({
    organizationId: input.organizationId,
    projectId: input.projectId,
    proposalId: input.proposalId,
    authorization: input.authorization,
  });

  const plan = approval.plan;

  // Phát hiện review Task 5 mục 1 — re-verify connector THẬT ở services/cosa (bảng
  // connectorAuthorizations sống ở đây), không tin plan.connectors[].status cũ của nháp.
  const connectorGrantIds: string[] = [];
  for (const connector of plan.connectors) {
    const ids = await findActiveConnectorAuthorizationIds(input.organizationId, connector.key);
    if (ids.length === 0) {
      throw APIError.failedPrecondition(
        `automation_plan_not_ready: connector_missing (${connector.key})`
      );
    }
    connectorGrantIds.push(...ids);
  }

  const promptTemplate = buildAutomationPlanPrompt(plan);
  const agentProfile = SKILL_AGENT_PROFILE[plan.skillId] || "operations";

  const schedule = await createWorkspaceSchedule({
    organizationId: input.organizationId,
    createdBy: approval.founderUserId,
    scheduleKind: plan.schedule.kind,
    timezone: plan.schedule.timezone,
    runAt: plan.schedule.runAt ? new Date(plan.schedule.runAt) : null,
    hour: plan.schedule.hour ?? undefined,
    minute: plan.schedule.minute ?? undefined,
    weekdays: plan.schedule.weekdays,
    promptTemplate,
    agentProfile,
    connectorGrantIds: [...new Set(connectorGrantIds)],
    projectId: input.projectId,
    preAuthorizedCapabilityIds: approval.capabilityIds,
    founderMemberId: approval.founderMemberId,
    founderUserId: approval.founderUserId,
    automationPlanProposalId: approval.proposalId,
    tokenBudgetPerRun: plan.tokenBudgetPerRun,
  });

  await callCompanyLinkSchedule({
    organizationId: input.organizationId,
    projectId: input.projectId,
    proposalId: input.proposalId,
    authorization: input.authorization,
    scheduleId: schedule.id,
  });

  return schedule;
}
