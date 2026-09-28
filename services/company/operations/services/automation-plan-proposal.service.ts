// Plan hub vận hành đợt 2 B4 — capability `automation.plan.propose` (T1, nháp).
//
// Agent (chat) đề xuất một kế hoạch tự động hoá: agent tái dùng trong Project (quy tắc 3),
// skill, connector, kênh nhận của founder, lịch, ngân sách token/lần chạy. Bước này CHỈ lưu
// nháp (`operating.automation_plan_proposals`) và trả readiness để thẻ kế hoạch (B6) khoá nút
// Duyệt khi còn blocker. KHÔNG tạo lịch thật (B5 duyệt theo id), KHÔNG mở OAuth thay founder.
//
// Bất biến an toàn (ADR-FOUNDER-CHANNEL-001, Consequences B4):
//   - Founder = danh tính trong delegation (`ctx.workforceMemberId`), không nhận từ payload.
//   - Kênh nhận chỉ trả `{kind, label, verified}` — không chat id, secret_ref, token.
//   - `capabilityIds` (tập sẽ uỷ quyền trước khi duyệt ở B5) cố định theo skill, không nhận từ
//     model.
//   - Trạng thái connector do apps/cosa kiểm với control plane rồi gửi lên (company không biết
//     connector); company chỉ nhận đúng key của skill và giá trị `connected|missing`.
import { APIError } from "encore.dev/api";
import { and, eq, gte, inArray, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { mvpItem, type MvpSuccess } from "../../shared/contracts/mvp-response";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { resolveUsableChannelForFounder } from "../../identity/services/founder-notification-channel.service";
import { getProjectFounderDeployments } from "./founder-asset-query.service";
import { AGENT_PROFILE_SPEC_ID, type OwnerAgentProfile } from "./ai-member.service";

const { automationPlanProposals, workspaceAgents } = schema;

// Quota nháp kế hoạch/Project/ngày UTC (plan hub đợt 1 đã chốt 20). Cùng kiểu cấu hình env với
// MAX_ACTIVE_SCHEDULES_PER_WORKSPACE (services/cosa/services/schedule/schedule-types.ts).
export const MAX_AUTOMATION_PLAN_PROPOSALS_PER_PROJECT_PER_DAY = parseInt(
  process.env.COMPANY_AUTOMATION_PLAN_MAX_PER_PROJECT_PER_DAY || "20",
  10
);

/** Trần ngân sách token cho một lần chạy — chặn giá trị vô lý do model tự điền. */
export const MAX_TOKEN_BUDGET_PER_RUN = 200_000;

export type AutomationConnectorStatus = "connected" | "missing";
export type AutomationScheduleKind = "one_time" | "daily" | "weekdays";
export type AutomationChannelKind = "telegram";
export type AutomationPlanBlockerCode =
  | "founder_channel_unverified"
  | "connector_missing"
  | "requires_new_agent";
export type AutomationPlanBlockerTarget = "founder_profile" | "tools_tab" | "agents_tab";
export type AutomationPlanProposalStatus = "DRAFT" | "APPROVED" | "DISCARDED";

interface AutomationSkillDefinition {
  readonly label: string;
  /** Profile agent skill cần (quy tắc 3: tái dùng agent profile này nếu đã có trong Project). */
  readonly agentProfile: OwnerAgentProfile;
  readonly connectors: readonly string[];
  /** Capability sẽ uỷ quyền trước cho lịch khi founder duyệt (B5). Cố định theo skill. */
  readonly capabilityIds: readonly string[];
}

// Skill tự động hoá được phép đề xuất — khớp skillpack tĩnh `skillpacks/operations/email-digest`.
export const AUTOMATION_PLAN_SKILLS: Readonly<Record<string, AutomationSkillDefinition>> = Object.freeze({
  "operations.email-digest": Object.freeze({
    label: "Tóm tắt email chưa đọc",
    agentProfile: "operations",
    connectors: Object.freeze(["email-read"]),
    capabilityIds: Object.freeze(["email.digest.read", "founder.notify.send"]),
  }),
});

const CHANNEL_KINDS: ReadonlySet<string> = new Set<AutomationChannelKind>(["telegram"]);
const CHANNEL_KIND_LABEL: Record<AutomationChannelKind, string> = { telegram: "Telegram" };
const FOUNDER_ROLES: ReadonlySet<string> = new Set(["founder", "co-founder"]);
const SCHEDULE_KINDS: ReadonlySet<string> = new Set<AutomationScheduleKind>(["one_time", "daily", "weekdays"]);
const WEEKDAY_LABELS = ["", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"];
const NEW_AGENT_LABEL = "Agent vận hành mới (đề xuất)";

export interface AutomationPlanScheduleInput {
  kind: AutomationScheduleKind;
  hour?: number;
  minute?: number;
  /** 1-7 = Thứ 2 … Chủ nhật (cùng quy ước services/cosa schedule-recurrence.engine). */
  weekdays?: number[];
  timezone: string;
  /** ISO 8601, chỉ cho `one_time`. */
  runAt?: string;
}

export interface ProposeAutomationPlanInput {
  agentDeploymentId?: string;
  proposeNewAgent?: boolean;
  skillId: string;
  connectorKeys: string[];
  connectorStatus?: Record<string, string>;
  channelKind?: string;
  schedule: AutomationPlanScheduleInput;
  tokenBudgetPerRun: number;
}

export interface AutomationPlanSchedule {
  kind: AutomationScheduleKind;
  timezone: string;
  hour: number | null;
  minute: number | null;
  weekdays: number[];
  runAt: string | null;
  humanReadable: string;
}

export interface AutomationPlanConnector {
  key: string;
  status: AutomationConnectorStatus;
}

export interface AutomationPlanChannel {
  kind: AutomationChannelKind;
  label: string;
  verified: boolean;
}

export interface AutomationPlan {
  /** Deployment tái dùng trong Project; null khi đề xuất agent mới. */
  agentDeploymentId: string | null;
  agentLabel: string;
  proposeNewAgent: boolean;
  skillId: string;
  skillLabel: string;
  connectors: AutomationPlanConnector[];
  channel: AutomationPlanChannel;
  schedule: AutomationPlanSchedule;
  tokenBudgetPerRun: number;
  capabilityIds: string[];
}

export interface AutomationPlanBlocker {
  code: AutomationPlanBlockerCode;
  target: AutomationPlanBlockerTarget;
}

export interface AutomationPlanReadiness {
  ready: boolean;
  blockers: AutomationPlanBlocker[];
}

export interface AutomationPlanProposalResult {
  proposalId: string;
  projectId: string;
  status: AutomationPlanProposalStatus;
  plan: AutomationPlan;
  readiness: AutomationPlanReadiness;
  createdAt: string;
  decidedAt: string | null;
  approvedScheduleId: string | null;
}

function invalid(message: string): APIError {
  return APIError.invalidArgument(`automation_plan_invalid: ${message}`);
}

function parseId(value: string, field: string): bigint {
  if (typeof value !== "string" || !/^\d{1,20}$/.test(value)) {
    throw invalid(`${field} phải là số nguyên hợp lệ`);
  }
  return BigInt(value);
}

function requireFounderOwner(ctx: TenantContext): string {
  const role = (ctx.membershipRole || "").toLowerCase();
  if (!FOUNDER_ROLES.has(role)) {
    throw APIError.permissionDenied(
      "founder_owner_not_authorized: chỉ founder/co-founder mới đề xuất được kế hoạch tự động hoá"
    );
  }
  if (!ctx.workforceMemberId) {
    throw APIError.permissionDenied(
      "founder_owner_not_authorized: không xác định được workforce member của founder"
    );
  }
  return ctx.workforceMemberId;
}

function isInteger(value: unknown, min: number, max: number): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= min && value <= max;
}

function assertIanaTimezone(tz: unknown): string {
  if (typeof tz !== "string" || tz.trim().length === 0 || tz.length > 64) {
    throw invalid("schedule.timezone phải là múi giờ IANA (vd. Asia/Ho_Chi_Minh)");
  }
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: tz });
  } catch {
    throw invalid(`schedule.timezone không phải múi giờ IANA hợp lệ: '${tz.slice(0, 64)}'`);
  }
  return tz;
}

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function formatInTimezone(date: Date, tz: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}

/** Validate lịch như `createWorkspaceSchedule` (services/cosa) và chuẩn hoá + mô tả dễ đọc. */
export function normalizeAutomationSchedule(
  input: AutomationPlanScheduleInput | undefined,
  now: Date = new Date()
): AutomationPlanSchedule {
  if (typeof input !== "object" || input === null) {
    throw invalid("thiếu schedule");
  }
  if (!SCHEDULE_KINDS.has(input.kind)) {
    throw invalid("schedule.kind phải là one_time, daily hoặc weekdays");
  }
  const timezone = assertIanaTimezone(input.timezone);

  if (input.kind === "one_time") {
    if (typeof input.runAt !== "string" || Number.isNaN(Date.parse(input.runAt))) {
      throw invalid("lịch one_time cần runAt (ISO 8601)");
    }
    const runAt = new Date(input.runAt);
    if (runAt.getTime() <= now.getTime()) {
      throw invalid("lịch one_time cần runAt ở tương lai");
    }
    return {
      kind: "one_time",
      timezone,
      hour: null,
      minute: null,
      weekdays: [],
      runAt: runAt.toISOString(),
      humanReadable: `Một lần lúc ${formatInTimezone(runAt, timezone)} (${timezone})`,
    };
  }

  if (input.runAt !== undefined && input.runAt !== null) {
    throw invalid("runAt chỉ dùng cho lịch one_time");
  }
  if (!isInteger(input.hour, 0, 23)) {
    throw invalid("schedule.hour phải là số nguyên 0-23");
  }
  const minute = input.minute ?? 0;
  if (!isInteger(minute, 0, 59)) {
    throw invalid("schedule.minute phải là số nguyên 0-59");
  }
  const time = `${pad2(input.hour)}:${pad2(minute)}`;

  if (input.kind === "daily") {
    if (input.weekdays !== undefined && input.weekdays.length > 0) {
      throw invalid("weekdays chỉ dùng cho lịch weekdays");
    }
    return {
      kind: "daily",
      timezone,
      hour: input.hour,
      minute,
      weekdays: [],
      runAt: null,
      humanReadable: `Hằng ngày lúc ${time} (${timezone})`,
    };
  }

  const weekdays = input.weekdays;
  if (
    !Array.isArray(weekdays) ||
    weekdays.length === 0 ||
    weekdays.length > 7 ||
    weekdays.some((d) => !isInteger(d, 1, 7)) ||
    new Set(weekdays).size !== weekdays.length
  ) {
    throw invalid("lịch weekdays cần weekdays là các số 1-7 (Thứ 2 … Chủ nhật), không trùng");
  }
  const sorted = [...weekdays].sort((a, b) => a - b);
  return {
    kind: "weekdays",
    timezone,
    hour: input.hour,
    minute,
    weekdays: sorted,
    runAt: null,
    humanReadable: `${sorted.map((d) => WEEKDAY_LABELS[d]).join(", ")} lúc ${time} (${timezone})`,
  };
}

interface ValidatedInput {
  skillId: string;
  skill: AutomationSkillDefinition;
  connectors: AutomationPlanConnector[];
  channelKind: AutomationChannelKind;
  schedule: AutomationPlanSchedule;
  tokenBudgetPerRun: number;
  agentDeploymentId: string | null;
  proposeNewAgent: boolean;
}

function validateInput(input: ProposeAutomationPlanInput, now: Date): ValidatedInput {
  if (typeof input !== "object" || input === null) {
    throw invalid("body phải là object JSON");
  }
  const skill = AUTOMATION_PLAN_SKILLS[input.skillId];
  if (!skill) {
    throw invalid(`skillId không được hỗ trợ (chỉ nhận: ${Object.keys(AUTOMATION_PLAN_SKILLS).join(", ")})`);
  }

  const allowedConnectors = new Set(skill.connectors);
  const connectorKeys = input.connectorKeys ?? [];
  if (!Array.isArray(connectorKeys) || connectorKeys.some((k) => typeof k !== "string" || !allowedConnectors.has(k))) {
    throw invalid(`connectorKeys chỉ được chứa connector của skill: ${skill.connectors.join(", ")}`);
  }
  const statusInput = input.connectorStatus ?? {};
  if (typeof statusInput !== "object" || statusInput === null || Array.isArray(statusInput)) {
    throw invalid("connectorStatus phải là object {connectorKey: connected|missing}");
  }
  for (const [key, value] of Object.entries(statusInput)) {
    if (!allowedConnectors.has(key)) {
      throw invalid(`connectorStatus có connector ngoài skill: ${key.slice(0, 64)}`);
    }
    if (value !== "connected" && value !== "missing") {
      throw invalid("connectorStatus chỉ nhận giá trị connected hoặc missing");
    }
  }
  // Kế hoạch luôn gồm ĐỦ connector skill cần (không để model bỏ bớt); thiếu trạng thái ⇒ missing.
  const connectors: AutomationPlanConnector[] = skill.connectors.map((key) => ({
    key,
    status: statusInput[key] === "connected" ? "connected" : "missing",
  }));

  const channelKind = input.channelKind ?? "telegram";
  if (typeof channelKind !== "string" || !CHANNEL_KINDS.has(channelKind)) {
    throw invalid("channelKind không được hỗ trợ (chỉ telegram)");
  }

  if (!isInteger(input.tokenBudgetPerRun, 1, MAX_TOKEN_BUDGET_PER_RUN)) {
    throw invalid(`tokenBudgetPerRun phải là số nguyên 1-${MAX_TOKEN_BUDGET_PER_RUN}`);
  }

  const proposeNewAgent = input.proposeNewAgent === true;
  const agentDeploymentId = input.agentDeploymentId ?? null;
  if (agentDeploymentId !== null) {
    parseId(agentDeploymentId, "agentDeploymentId");
  }
  if (proposeNewAgent && agentDeploymentId !== null) {
    throw invalid("không được vừa chọn agentDeploymentId vừa đề xuất agent mới");
  }

  return {
    skillId: input.skillId,
    skill,
    connectors,
    channelKind: channelKind as AutomationChannelKind,
    schedule: normalizeAutomationSchedule(input.schedule, now),
    tokenBudgetPerRun: input.tokenBudgetPerRun,
    agentDeploymentId,
    proposeNewAgent,
  };
}

interface MatchingAgent {
  deploymentId: string;
  label: string;
}

/**
 * Agent ACTIVE đã deploy vào Project khớp profile skill cần — tái dùng
 * `getProjectFounderDeployments` (nguồn của route GET founder-deployments), rồi đối chiếu
 * `workspace_agents.agent_asset_id` với profile / spec id built-in như
 * `resolveProjectAgentAuthorityV2`.
 */
async function findMatchingProjectAgents(
  ctx: TenantContext,
  projectId: string,
  profile: OwnerAgentProfile
): Promise<MatchingAgent[]> {
  const deployments = await getProjectFounderDeployments(ctx, projectId);
  const active = deployments.data.agents.filter((a) => a.state === "ACTIVE");
  if (active.length === 0) return [];

  const specId = AGENT_PROFILE_SPEC_ID[profile];
  const agentRows = await db
    .select({
      id: workspaceAgents.id,
      agentAssetId: workspaceAgents.agentAssetId,
      state: workspaceAgents.state,
      roleTitle: identityWorkforceMembers.roleTitle,
    })
    .from(workspaceAgents)
    .leftJoin(identityWorkforceMembers, eq(identityWorkforceMembers.id, workspaceAgents.workforceMemberId))
    .where(
      and(
        eq(workspaceAgents.workspaceId, BigInt(ctx.workspaceId)),
        inArray(
          workspaceAgents.id,
          active.map((a) => BigInt(a.workspaceAgentId))
        )
      )
    );
  const byId = new Map(agentRows.map((r) => [r.id.toString(), r]));

  const matches: MatchingAgent[] = [];
  for (const deployment of active) {
    const agent = byId.get(deployment.workspaceAgentId);
    if (!agent || agent.state !== "ACTIVE") continue;
    if (agent.agentAssetId !== profile && agent.agentAssetId !== specId) continue;
    matches.push({ deploymentId: deployment.id, label: agent.roleTitle || `Agent ${profile}` });
  }
  return matches;
}

async function resolveChannel(
  workspaceId: string,
  founderMemberId: string,
  kind: AutomationChannelKind
): Promise<AutomationPlanChannel> {
  try {
    const row = await resolveUsableChannelForFounder(workspaceId, founderMemberId, kind);
    // Chỉ nhãn + trạng thái — không bao giờ chatId / secretRef của row.
    return { kind, label: row.label || CHANNEL_KIND_LABEL[kind], verified: true };
  } catch (err) {
    const message = err instanceof Error ? err.message : "";
    if (message.startsWith("founder_channel_unavailable:") || message.startsWith("founder_channel_ambiguous:")) {
      return { kind, label: CHANNEL_KIND_LABEL[kind], verified: false };
    }
    throw err;
  }
}

function startOfUtcDay(now: Date): Date {
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

function toResult(row: typeof automationPlanProposals.$inferSelect): AutomationPlanProposalResult {
  return {
    proposalId: row.id.toString(),
    projectId: row.projectId.toString(),
    status: row.status as AutomationPlanProposalStatus,
    plan: row.plan as AutomationPlan,
    readiness: row.readiness as AutomationPlanReadiness,
    createdAt: row.createdAt.toISOString(),
    decidedAt: row.decidedAt ? row.decidedAt.toISOString() : null,
    approvedScheduleId: row.approvedScheduleId ?? null,
  };
}

export interface ProposeAutomationPlanOptions {
  /** `X-COSA-Run-Id` của run chat đề xuất (nếu có) — chỉ để truy vết. */
  runId?: string | null;
  now?: Date;
}

export async function proposeAutomationPlan(
  ctx: TenantContext,
  projectId: string,
  input: ProposeAutomationPlanInput,
  options: ProposeAutomationPlanOptions = {}
): Promise<MvpSuccess<AutomationPlanProposalResult>> {
  const founderMemberId = requireFounderOwner(ctx);
  const projId = parseId(projectId, "projectId");
  const now = options.now ?? new Date();
  const v = validateInput(input, now);

  // Quy tắc 3 — tái dùng agent có sẵn trong Project; chỉ đề xuất agent mới khi không có.
  const matches = await findMatchingProjectAgents(ctx, projId.toString(), v.skill.agentProfile);
  let agentDeploymentId: string | null;
  let agentLabel: string;
  if (matches.length > 0) {
    if (v.proposeNewAgent) {
      throw APIError.invalidArgument(
        `agent_reuse_required: Project đã có agent phù hợp, hãy dùng lại: ${matches
          .map((m) => `${m.label} (${m.deploymentId})`)
          .join(", ")}`
      );
    }
    const chosen = v.agentDeploymentId
      ? matches.find((m) => m.deploymentId === v.agentDeploymentId)
      : matches[0];
    if (!chosen) {
      throw APIError.invalidArgument(
        `agent_reuse_required: agentDeploymentId không phải agent ${v.skill.agentProfile} đang hoạt động trong Project; agent phù hợp: ${matches
          .map((m) => `${m.label} (${m.deploymentId})`)
          .join(", ")}`
      );
    }
    agentDeploymentId = chosen.deploymentId;
    agentLabel = chosen.label;
  } else {
    if (v.agentDeploymentId) {
      throw APIError.invalidArgument(
        `agent_not_found: Project chưa có agent ${v.skill.agentProfile} đang hoạt động; đặt proposeNewAgent=true để đề xuất tạo mới`
      );
    }
    if (!v.proposeNewAgent) {
      throw APIError.invalidArgument(
        `agent_required: Project chưa có agent ${v.skill.agentProfile} đang hoạt động; đặt proposeNewAgent=true để đề xuất tạo mới`
      );
    }
    agentDeploymentId = null;
    agentLabel = NEW_AGENT_LABEL;
  }

  const channel = await resolveChannel(ctx.workspaceId, founderMemberId, v.channelKind);

  const blockers: AutomationPlanBlocker[] = [];
  if (!channel.verified) blockers.push({ code: "founder_channel_unverified", target: "founder_profile" });
  if (v.connectors.some((c) => c.status !== "connected")) {
    blockers.push({ code: "connector_missing", target: "tools_tab" });
  }
  if (agentDeploymentId === null) blockers.push({ code: "requires_new_agent", target: "agents_tab" });

  const plan: AutomationPlan = {
    agentDeploymentId,
    agentLabel,
    proposeNewAgent: agentDeploymentId === null,
    skillId: v.skillId,
    skillLabel: v.skill.label,
    connectors: v.connectors,
    channel,
    schedule: v.schedule,
    tokenBudgetPerRun: v.tokenBudgetPerRun,
    capabilityIds: [...v.skill.capabilityIds],
  };
  const readiness: AutomationPlanReadiness = { ready: blockers.length === 0, blockers };
  const runId = typeof options.runId === "string" && options.runId.trim() ? options.runId.trim().slice(0, 128) : null;

  const row = await db.transaction(async (tx) => {
    // Khoá theo Project để đếm quota + insert không bị hai request song song vượt trần.
    await tx.execute(sql`SELECT pg_advisory_xact_lock(hashtext(${`automation_plan_quota:${projId.toString()}`}))`);
    const [{ count }] = await tx
      .select({ count: sql<number>`count(*)::int` })
      .from(automationPlanProposals)
      .where(
        and(
          eq(automationPlanProposals.projectId, projId),
          gte(automationPlanProposals.createdAt, startOfUtcDay(now))
        )
      );
    if (count >= MAX_AUTOMATION_PLAN_PROPOSALS_PER_PROJECT_PER_DAY) {
      throw APIError.resourceExhausted(
        `automation_plan_quota_exceeded: tối đa ${MAX_AUTOMATION_PLAN_PROPOSALS_PER_PROJECT_PER_DAY} nháp kế hoạch/Project/ngày (UTC)`
      );
    }
    const [inserted] = await tx
      .insert(automationPlanProposals)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(ctx.workspaceId),
        projectId: projId,
        proposedByMemberId: BigInt(founderMemberId),
        runId,
        plan,
        readiness,
        status: "DRAFT",
        createdAt: now,
      })
      .returning();
    return inserted;
  });

  return mvpItem(toResult(row), [
    { kind: "company_db", ref: `operating.automation_plan_proposals:${row.id.toString()}` },
  ]);
}

/** Founder nạp lại thẻ kế hoạch (B6). Chỉ người đề xuất (founder của run) xem được nháp. */
export async function getAutomationPlanProposal(
  ctx: TenantContext,
  projectId: string,
  proposalId: string
): Promise<MvpSuccess<AutomationPlanProposalResult>> {
  const projId = parseId(projectId, "projectId");
  const id = parseId(proposalId, "proposalId");
  const [row] = await db
    .select()
    .from(automationPlanProposals)
    .where(
      and(
        eq(automationPlanProposals.id, id),
        eq(automationPlanProposals.workspaceId, BigInt(ctx.workspaceId)),
        eq(automationPlanProposals.projectId, projId)
      )
    )
    .limit(1);
  if (!row || !ctx.workforceMemberId || row.proposedByMemberId.toString() !== ctx.workforceMemberId) {
    throw APIError.notFound("automation_plan_not_found: không tìm thấy nháp kế hoạch");
  }
  return mvpItem(toResult(row), [
    { kind: "company_db", ref: `operating.automation_plan_proposals:${row.id.toString()}` },
  ]);
}
