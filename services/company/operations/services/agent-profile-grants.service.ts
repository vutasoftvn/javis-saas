import { and, desc, eq, inArray, isNull, or } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import {
  coreAgentCapabilityGrants,
  coreCapabilityPermissionBindings,
  coreMemberRoleAssignments,
  coreRolePermissions,
  coreWorkspaceRoles,
} from "../../shared/db/schema/identity";
import { db, schema } from "../models/db";
import {
  appendAuthorizationEvent,
  advanceAuthorizationEpoch,
} from "../../identity/services/authorization.service";

// Spec 2026-09-27-chat-business-actions / ADR-CHAT-ACTIONS-001.
//
// Capability ghi mà founder CẤP cho AI member khi kích hoạt profile trong Project startup team.
// Kích hoạt là hành động của founder; mỗi lần chạy thật vẫn phải qua founder duyệt trong chat
// (T2) và live authorization ticket. Tập này = capability_refs của spec profile ∩ capability
// T1/T2 có AGENT_CAP trong apps/cosa/capabilities/access_matrix.py — test parity
// tests/apps/cosa/test_agent_capability_grants_parity.py chặn lệch.
//
// Cố ý KHÔNG tự cấp `finance.transaction.record`: hạn mức chưa được founder chốt (spec §8.3);
// founder cấp tay qua POST /identity/agent-capability-grants với constraints.maxAmountMinor.
export const AGENT_PROFILE_GRANTED_CAPABILITIES: Readonly<Record<string, readonly string[]>> =
  Object.freeze({
    operations: Object.freeze([
      "operations.task.create_draft",
      "operations.task.advance",
      "okr.key_result.create",
      "okr.key_result.checkin",
      "startup_os.goal.create",
      "startup_os.project.triage",
      "venture.profile.propose_update",
      // ADR-FOUNDER-CHANNEL-001: T2-self, chỉ gửi về kênh đã xác minh của founder sở hữu run.
      "founder.notify.send",
      // Plan hub đợt 2 B4: T1, chỉ lưu nháp kế hoạch tự động hoá cho founder duyệt.
      "automation.plan.propose",
    ]),
    finance: Object.freeze([
      "finance.transaction.classify_propose",
      "finance.accounting_document.create_draft",
    ]),
  });

// Nhãn hiển thị (vi/en) cho capability agent có thể được cấp — card vận hành ở hub không hiển thị
// enum thô. Test parity Python chặn thiếu nhãn cho capability trong bảng grant ở trên.
export const CAPABILITY_LABELS: Readonly<Record<string, { vi: string; en: string }>> = Object.freeze({
  "operations.task.create_draft": { vi: "Soạn nháp công việc", en: "Draft tasks" },
  "operations.task.advance": { vi: "Chuyển trạng thái công việc", en: "Update task status" },
  "okr.key_result.create": { vi: "Tạo Key Result", en: "Create Key Results" },
  "okr.key_result.checkin": { vi: "Ghi nhận tiến độ Key Result", en: "Check in Key Results" },
  "startup_os.goal.create": { vi: "Tạo mục tiêu", en: "Create goals" },
  "startup_os.project.triage": { vi: "Phân loại dự án", en: "Triage projects" },
  "venture.profile.propose_update": {
    vi: "Cập nhật hồ sơ khởi nghiệp",
    en: "Update the venture profile",
  },
  "finance.transaction.classify_propose": {
    vi: "Đề xuất phân loại giao dịch",
    en: "Propose transaction categories",
  },
  "finance.accounting_document.create_draft": {
    vi: "Soạn nháp chứng từ kế toán",
    en: "Draft accounting documents",
  },
  "finance.transaction.record": { vi: "Ghi giao dịch tài chính", en: "Record transactions" },
  "founder.notify.send": {
    vi: "Gửi thông báo vào kênh riêng của founder",
    en: "Send notifications to the founder's own channel",
  },
  "automation.plan.propose": {
    vi: "Đề xuất kế hoạch tự động hoá",
    en: "Propose automation plans",
  },
});

const UNKNOWN_CAPABILITY_LABEL = Object.freeze({ vi: "Quyền khác", en: "Other permission" });

// Transaction Drizzle của operations (cùng DB workspace với bảng core.* của identity).
type DbLike = Parameters<Parameters<typeof db.transaction>[0]>[0];

// Role workspace gán cho AI member của startup team: live authorization ticket đòi AI member có
// role chứa permission của capability (identity/services/agent-authorization.service.ts bước 6),
// ngoài grant. Chỉ cho AI_AGENT; phạm vi thực tế vẫn do grant theo capability + Project quyết định.
export const STARTUP_TEAM_AGENT_ROLE_KEY = "startup_team_agent";

export interface ProfileGrantInput {
  workspaceId: string;
  projectId: string;
  profileKey: string;
  agentWorkforceMemberId: string;
  founderMemberId: string;
  correlationId?: string;
  /**
   * Agent workspace (clone của built-in): chỉ cấp phần giao với capability_refs đã thu hẹp —
   * không bao giờ nhiều hơn bảng grant của profile gốc.
   */
  capabilityFilter?: readonly string[];
}

function profileCapabilities(profileKey: string, filter?: readonly string[]): string[] {
  const base = AGENT_PROFILE_GRANTED_CAPABILITIES[profileKey] ?? [];
  if (!filter) return [...base];
  const allowed = new Set(filter);
  return base.filter((c) => allowed.has(c));
}

/**
 * Đảm bảo AI member có grant ACTIVE (scope Project) cho mọi capability của profile. Idempotent:
 * bỏ qua capability chưa có binding hoặc đã có grant ACTIVE cùng Project. Trả danh sách
 * capability vừa cấp mới.
 */
export async function ensureProfileCapabilityGrants(
  tx: DbLike,
  input: ProfileGrantInput
): Promise<string[]> {
  const capabilities = profileCapabilities(input.profileKey, input.capabilityFilter);
  if (capabilities.length === 0) return [];
  const wsId = BigInt(input.workspaceId);
  const projectId = BigInt(input.projectId);
  const memberId = BigInt(input.agentWorkforceMemberId);

  const bound = await tx
    .select({
      capabilityId: coreCapabilityPermissionBindings.capabilityId,
      permissionKey: coreCapabilityPermissionBindings.permissionKey,
    })
    .from(coreCapabilityPermissionBindings)
    .where(inArray(coreCapabilityPermissionBindings.capabilityId, [...capabilities]));
  const boundIds = new Set<string>(bound.map((b) => b.capabilityId));
  await ensureStartupTeamAgentRole(tx, {
    workspaceId: input.workspaceId,
    agentWorkforceMemberId: input.agentWorkforceMemberId,
    permissionKeys: [...new Set(bound.map((b) => b.permissionKey))],
  });

  const existing = await tx
    .select({ capabilityId: coreAgentCapabilityGrants.capabilityId })
    .from(coreAgentCapabilityGrants)
    .where(
      and(
        eq(coreAgentCapabilityGrants.workspaceId, wsId),
        eq(coreAgentCapabilityGrants.agentWorkforceMemberId, memberId),
        eq(coreAgentCapabilityGrants.projectId, projectId),
        eq(coreAgentCapabilityGrants.status, "ACTIVE")
      )
    );
  const granted = new Set<string>(existing.map((g) => g.capabilityId));

  const created: string[] = [];
  for (const capabilityId of capabilities) {
    if (!boundIds.has(capabilityId) || granted.has(capabilityId)) continue;
    const [grant] = await tx
      .insert(coreAgentCapabilityGrants)
      .values({
        workspaceId: wsId,
        agentWorkforceMemberId: memberId,
        capabilityId,
        projectId,
        constraints: {},
        status: "ACTIVE",
        grantedByFounderMemberId: BigInt(input.founderMemberId),
      })
      .returning({ id: coreAgentCapabilityGrants.id });
    await appendAuthorizationEvent(tx, {
      workspaceId: input.workspaceId,
      eventType: "AGENT_CAPABILITY_GRANTED",
      actorMemberId: input.founderMemberId,
      targetMemberId: input.agentWorkforceMemberId,
      capabilityId,
      grantId: grant.id,
      reason: "Startup team activation",
      correlationId: input.correlationId,
      details: { projectId: input.projectId, profileKey: input.profileKey },
    });
    created.push(capabilityId);
  }
  if (created.length > 0) {
    await advanceAuthorizationEpoch(
      tx,
      input.workspaceId,
      input.founderMemberId,
      "Grant startup team capabilities"
    );
  }
  return created;
}

/**
 * Thu hồi grant đã cấp theo profile cho đúng Project khi founder tạm dừng agent. Trả danh sách
 * capability bị thu hồi.
 */
export async function revokeProfileCapabilityGrants(
  tx: DbLike,
  input: Omit<ProfileGrantInput, "founderMemberId"> & { actorMemberId?: string; reason: string }
): Promise<string[]> {
  const capabilities = AGENT_PROFILE_GRANTED_CAPABILITIES[input.profileKey] ?? [];
  if (capabilities.length === 0) return [];
  const revoked = await tx
    .update(coreAgentCapabilityGrants)
    .set({ status: "REVOKED", revokedAt: new Date(), revokeReason: input.reason })
    .where(
      and(
        eq(coreAgentCapabilityGrants.workspaceId, BigInt(input.workspaceId)),
        eq(coreAgentCapabilityGrants.agentWorkforceMemberId, BigInt(input.agentWorkforceMemberId)),
        eq(coreAgentCapabilityGrants.projectId, BigInt(input.projectId)),
        eq(coreAgentCapabilityGrants.status, "ACTIVE"),
        inArray(coreAgentCapabilityGrants.capabilityId, [...capabilities])
      )
    )
    .returning({
      id: coreAgentCapabilityGrants.id,
      capabilityId: coreAgentCapabilityGrants.capabilityId,
    });
  for (const row of revoked) {
    await appendAuthorizationEvent(tx, {
      workspaceId: input.workspaceId,
      eventType: "AGENT_CAPABILITY_REVOKED",
      actorMemberId: input.actorMemberId,
      targetMemberId: input.agentWorkforceMemberId,
      capabilityId: row.capabilityId,
      grantId: row.id,
      reason: input.reason,
      correlationId: input.correlationId,
      details: { projectId: input.projectId, profileKey: input.profileKey },
    });
  }
  if (revoked.length > 0) {
    await advanceAuthorizationEpoch(
      tx,
      input.workspaceId,
      input.actorMemberId,
      "Revoke startup team capabilities"
    );
  }
  return revoked.map((r) => r.capabilityId);
}

/**
 * Đảm bảo role `startup_team_agent` của workspace tồn tại, có ALLOW cho các permission cần và
 * được gán cho AI member. Idempotent.
 */
export async function ensureStartupTeamAgentRole(
  tx: DbLike,
  input: { workspaceId: string; agentWorkforceMemberId: string; permissionKeys: string[] }
): Promise<void> {
  if (input.permissionKeys.length === 0) return;
  const wsId = BigInt(input.workspaceId);
  const memberId = BigInt(input.agentWorkforceMemberId);

  await tx
    .insert(coreWorkspaceRoles)
    .values({
      workspaceId: wsId,
      roleKey: STARTUP_TEAM_AGENT_ROLE_KEY,
      name: "Startup team agent",
      isSystem: true,
      allowedMemberTypes: ["AI_AGENT"],
    })
    .onConflictDoNothing();
  const [role] = await tx
    .select({ id: coreWorkspaceRoles.id })
    .from(coreWorkspaceRoles)
    .where(
      and(
        eq(coreWorkspaceRoles.workspaceId, wsId),
        eq(coreWorkspaceRoles.roleKey, STARTUP_TEAM_AGENT_ROLE_KEY)
      )
    )
    .limit(1);

  await tx
    .insert(coreRolePermissions)
    .values(
      input.permissionKeys.map((permissionKey) => ({
        roleId: role.id,
        permissionKey,
        effect: "ALLOW",
      }))
    )
    .onConflictDoNothing();

  const [assigned] = await tx
    .select({ id: coreMemberRoleAssignments.id })
    .from(coreMemberRoleAssignments)
    .where(
      and(
        eq(coreMemberRoleAssignments.workspaceId, wsId),
        eq(coreMemberRoleAssignments.workforceMemberId, memberId),
        eq(coreMemberRoleAssignments.roleId, role.id)
      )
    )
    .limit(1);
  if (!assigned) {
    await tx
      .insert(coreMemberRoleAssignments)
      .values({ workspaceId: wsId, workforceMemberId: memberId, roleId: role.id });
  }
}

export interface ProjectAgentCapabilityGrant {
  grantId: string;
  profileKey: string;
  agentWorkforceMemberId: string;
  capabilityId: string;
  label: { vi: string; en: string };
  scope: "PROJECT" | "WORKSPACE";
  status: string;
  grantedAt: string;
  grantedByMemberId: string;
  revokedAt?: string;
  revokeReason?: string;
}

// Số grant REVOKED gần nhất trả kèm để founder thấy lịch sử thu hồi mà không tải cả lịch sử.
const RECENT_REVOKED_LIMIT = 20;

/**
 * Quyền đang cấp (và thu hồi gần đây) cho AI member của startup team trong Project — tab Công cụ
 * của card vận hành ở hub. Gồm grant scope Project này và grant scope toàn workspace (projectId
 * rỗng) của cùng AI member. Chỉ đọc; thu hồi đi qua POST /identity/agent-capability-grants/:id/revoke.
 */
export async function listProjectAgentCapabilityGrants(input: {
  workspaceId: string;
  projectId: string;
}): Promise<ProjectAgentCapabilityGrant[]> {
  const wsId = BigInt(input.workspaceId);
  let projId: bigint;
  try {
    projId = BigInt(input.projectId);
  } catch {
    throw APIError.invalidArgument("projectId must be numeric");
  }
  const { projects, projectAgentAssignments } = schema;

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);
  if (!project) {
    throw APIError.notFound("Project not found");
  }

  const assignments = await db
    .select({
      profileKey: projectAgentAssignments.profileKey,
      memberId: projectAgentAssignments.agentWorkforceMemberId,
    })
    .from(projectAgentAssignments)
    .where(
      and(eq(projectAgentAssignments.workspaceId, wsId), eq(projectAgentAssignments.projectId, projId))
    );
  const profileByMember = new Map<string, string>();
  for (const a of assignments) {
    if (a.memberId !== null) profileByMember.set(a.memberId.toString(), a.profileKey);
  }
  if (profileByMember.size === 0) return [];

  const rows = await db
    .select()
    .from(coreAgentCapabilityGrants)
    .where(
      and(
        eq(coreAgentCapabilityGrants.workspaceId, wsId),
        inArray(
          coreAgentCapabilityGrants.agentWorkforceMemberId,
          [...profileByMember.keys()].map((id) => BigInt(id))
        ),
        or(eq(coreAgentCapabilityGrants.projectId, projId), isNull(coreAgentCapabilityGrants.projectId))
      )
    )
    .orderBy(desc(coreAgentCapabilityGrants.createdAt));

  const active = rows.filter((r) => r.status === "ACTIVE");
  const revoked = rows.filter((r) => r.status !== "ACTIVE").slice(0, RECENT_REVOKED_LIMIT);
  return [...active, ...revoked].map((row) => ({
    grantId: row.id,
    profileKey: profileByMember.get(row.agentWorkforceMemberId.toString()) ?? "",
    agentWorkforceMemberId: row.agentWorkforceMemberId.toString(),
    capabilityId: row.capabilityId,
    label: CAPABILITY_LABELS[row.capabilityId] ?? UNKNOWN_CAPABILITY_LABEL,
    scope: row.projectId === null ? "WORKSPACE" : "PROJECT",
    status: row.status,
    grantedAt: row.createdAt.toISOString(),
    grantedByMemberId: row.grantedByFounderMemberId.toString(),
    revokedAt: row.revokedAt ? row.revokedAt.toISOString() : undefined,
    revokeReason: row.revokeReason ?? undefined,
  }));
}
