import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  EXECUTIVE_ROLE_CATALOG,
  ExecutiveRoleKey,
} from "../../shared/contracts/executive-advisor-roles.generated";
import { resolveProjectAgentAuthorityV2 } from "./founder-agent-compatibility.service";
import { getWorkspaceExecutiveRoleStates } from "./workspace-executive-role-activation.service";
import { roleKeysForStage, PERSISTENT_EXECUTIVE_ROLES } from "./executive-board-stage-presets";
import { AGENT_PROFILE_SPEC_ID, OwnerAgentProfile } from "./ai-member.service";

const { projects, workspaceAgents } = schema;

/**
 * Guard quyền Founder cho Hội đồng Cố vấn Điều hành.
 * Chỉ con người (HUMAN) có role founder/co-founder mới có quyền quản trị.
 * Project bắt buộc phải thuộc đúng Workspace (chống cross-tenant enumeration).
 */
export async function requireExecutiveBoardFounderAuthority(
  ctx: TenantContext,
  projectId: string
): Promise<void> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "FOUNDER_AUTHORITY_REQUIRED: Only HUMAN members can hold founder authority"
    );
  }

  const role = (ctx.membershipRole || "").toLowerCase();
  if (!["founder", "co-founder"].includes(role)) {
    throw APIError.permissionDenied(
      "FOUNDER_AUTHORITY_REQUIRED: Active human founder role required"
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }
}

/**
 * Guard quyền Founder ở phạm vi Workspace (không gắn Project nào).
 * Dùng cho activation cấp Workspace (2026-09-14) — giữ đúng 2 check danh tính
 * của bản project-scoped, nhưng bỏ bước query bảng `projects` vì hành động này
 * không thuộc về một Project cụ thể.
 */
export async function requireExecutiveBoardFounderAuthorityForWorkspace(
  ctx: TenantContext
): Promise<void> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "FOUNDER_AUTHORITY_REQUIRED: Only HUMAN members can hold founder authority"
    );
  }

  const role = (ctx.membershipRole || "").toLowerCase();
  if (!["founder", "co-founder"].includes(role)) {
    throw APIError.permissionDenied(
      "FOUNDER_AUTHORITY_REQUIRED: Active human founder role required"
    );
  }
}

/**
 * Trạng thái Hội đồng Cố vấn Điều hành CHIẾU theo một Project cụ thể
 * (2026-09-14 — thay cho activation cấp Project cũ, xem
 * docs/superpowers/specs/2026-09-14-foundation-correctness-remediation-design.md).
 *
 * Role (CFO/CMO/…) vẫn là Workspace Role duy nhất — KHÔNG có bản ghi Role
 * riêng theo Project. Project chỉ deploy Workspace Agent tương ứng
 * (`project_agent_deployments`, xem founder-asset-deployment.service.ts).
 * View này compose 3 tín hiệu độc lập để trả lời "role này có thể tư vấn cho
 * ĐÚNG Project này ngay bây giờ không":
 *   1. officeState  — activation cấp Workspace có ACTIVE không (nguồn sự thật
 *      duy nhất, đọc trực tiếp từ `workspace_executive_role_activations`,
 *      KHÔNG dùng lại phép OR-toàn-workspace của board hiển thị chung).
 *   2. projectDeploymentState — agent nền có đang deploy ACTIVE vào ĐÚNG
 *      Project này không (`resolveProjectAgentAuthorityV2`, nhánh V2 thật —
 *      không suy diễn từ bảng legacy `project_agent_assignments`).
 *   3. stageEligibility — stage hiện tại của Project có "gợi ý" role này
 *      không (role persistent luôn ALLOWED).
 */
export type ProjectExecutiveOfficeState =
  | "ACTIVE"
  | "DISABLED"
  | "AVAILABLE_NOT_ACTIVATED"
  | "UNAVAILABLE";
export type ProjectExecutiveDeploymentState = "ACTIVE" | "INACTIVE" | "PAUSED" | "RETIRED";
export type ProjectExecutiveStageEligibility = "ALLOWED" | "NOT_SUGGESTED";
export type ProjectExecutiveEffectiveState =
  | "EFFECTIVE"
  | "OFFICE_DISABLED"
  | "DEPLOYMENT_INACTIVE"
  | "STAGE_FORBIDDEN";

export interface ProjectExecutiveRoleView {
  roleKey: ExecutiveRoleKey;
  /** Metadata từ catalog built-in — để client hiển thị mà không cần tự nhân bản catalog. */
  label: string;
  advisoryRemit: string;
  requiredProfileKey: string;
  officeState: ProjectExecutiveOfficeState;
  projectDeploymentState: ProjectExecutiveDeploymentState;
  stageEligibility: ProjectExecutiveStageEligibility;
  effectiveState: ProjectExecutiveEffectiveState;
  workspaceOfficeVersion: number;
  /** Server-authorized repair action: chỉ true với Project P0 chưa đủ P0 Core. */
  p0CoreBootstrapAvailable: boolean;
  workspaceAgentId?: string;
  projectAgentDeploymentId?: string;
  disabledReason?: string;
}

export interface ProjectExecutiveBoardState {
  projectId: string;
  roles: ProjectExecutiveRoleView[];
}

/**
 * Lấy trạng thái tư vấn hiệu lực (effective) của toàn bộ 13 Executive Role
 * cho MỘT Project cụ thể. KHÔNG đọc/ghi `project_executive_role_activations`
 * — bảng đó không còn là nguồn sự thật (xem module doc ở trên).
 */
export async function getProjectExecutiveRoleStates(
  ctx: TenantContext,
  projectId: string
): Promise<ProjectExecutiveBoardState> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  // Xác nhận Project thuộc đúng Workspace (chống cross-tenant enumeration).
  const [project] = await db
    .select({ id: projects.id, lifecycleStage: projects.lifecycleStage })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }

  // Giữ cùng semantics với Workspace Board: chỉ `AVAILABLE_NOT_ACTIVATED`
  // là tín hiệu server xác nhận Founder có thể bật Office. Không suy luận từ
  // việc thiếu activation row vì `UNAVAILABLE` còn có thể là profile/catalog
  // chưa sẵn sàng và endpoint activation sẽ fail closed.
  const workspaceBoard = await getWorkspaceExecutiveRoleStates(ctx);
  const workspaceRoleByKey = new Map(
    workspaceBoard.roles.map((role) => [role.roleKey, role])
  );

  const stageEligibleSet = new Set(roleKeysForStage(project.lifecycleStage));
  const persistentSet = new Set(PERSISTENT_EXECUTIVE_ROLES);
  const activeWorkspaceAgents = await db
    .select({ id: workspaceAgents.id, agentAssetId: workspaceAgents.agentAssetId })
    .from(workspaceAgents)
    .where(and(eq(workspaceAgents.workspaceId, wsId), eq(workspaceAgents.state, "ACTIVE")));
  const workspaceAgentByAssetId = new Map(
    activeWorkspaceAgents.map((agent) => [agent.agentAssetId, agent.id.toString()])
  );

  // N+1 truy vấn có chủ đích: chỉ 13 role/Project, quy mô MVP hiện tại chưa
  // cần batch hoá — `resolveProjectAgentAuthorityV2` là nguồn sự thật duy
  // nhất cho "agent V2 có đang deploy ACTIVE vào Project này" nên không nhân
  // bản logic đó ở đây (cùng lý do đã ghi ở
  // workspace-executive-role-activation.service.ts::resolveAvailableProfileKeys).
  const roles: ProjectExecutiveRoleView[] = [];
  for (const roleDef of Object.values(EXECUTIVE_ROLE_CATALOG)) {
    const workspaceRole = workspaceRoleByKey.get(roleDef.key);
    const officeState: ProjectExecutiveOfficeState =
      workspaceRole?.displayState ?? "UNAVAILABLE";

    const authority = await resolveProjectAgentAuthorityV2(
      { workspaceId: ctx.workspaceId, projectId },
      { projectId, profileKey: roleDef.requiredProfileKey }
    );
    const projectDeploymentState = authority.v2Deployment.state;

    const stageEligibility: ProjectExecutiveStageEligibility =
      persistentSet.has(roleDef.key) || stageEligibleSet.has(roleDef.key)
        ? "ALLOWED"
        : "NOT_SUGGESTED";

    let effectiveState: ProjectExecutiveEffectiveState;
    if (officeState !== "ACTIVE") {
      effectiveState = "OFFICE_DISABLED";
    } else if (projectDeploymentState !== "ACTIVE") {
      effectiveState = "DEPLOYMENT_INACTIVE";
    } else if (stageEligibility !== "ALLOWED") {
      effectiveState = "STAGE_FORBIDDEN";
    } else {
      effectiveState = "EFFECTIVE";
    }

    roles.push({
      roleKey: roleDef.key,
      label: roleDef.label,
      advisoryRemit: roleDef.advisoryRemit,
      requiredProfileKey: roleDef.requiredProfileKey,
      officeState,
      projectDeploymentState,
      stageEligibility,
      effectiveState,
      workspaceOfficeVersion: workspaceRole?.version ?? 1,
      p0CoreBootstrapAvailable: false,
      workspaceAgentId:
        workspaceAgentByAssetId.get(
          AGENT_PROFILE_SPEC_ID[roleDef.requiredProfileKey as OwnerAgentProfile]
        ),
      projectAgentDeploymentId: authority.v2Deployment.deploymentId,
      disabledReason: workspaceRole?.disabledReason,
    });
  }

  const p0CoreBootstrapAvailable =
    project.lifecycleStage === "P0_DISCOVERY" &&
    PERSISTENT_EXECUTIVE_ROLES.some(
      (roleKey) => roles.find((role) => role.roleKey === roleKey)?.effectiveState !== "EFFECTIVE"
    );

  return {
    projectId,
    roles: roles.map((role) => ({ ...role, p0CoreBootstrapAvailable })),
  };
}

export interface StageSuggestion {
  stage: string;
  /** Role đã đủ điều kiện eligible theo stage nhưng Workspace office CHƯA bật — Founder cần gọi activate ở cấp Workspace. */
  workspaceOfficeToEnable: ExecutiveRoleKey[];
  /** Role đã ACTIVE ở cấp Workspace nhưng CHƯA có agent deploy vào ĐÚNG Project này — Founder cần gọi POST .../agent-deployments. */
  projectAgentsToDeploy: ExecutiveRoleKey[];
  /** Toàn bộ role được gợi ý cho stage hiện tại của Project (bất kể đã bật/deploy hay chưa). */
  stageEligibleRoles: ExecutiveRoleKey[];
}

/**
 * Tính diff gợi ý Executive Board theo stage hiện tại của Project — CHỈ gợi ý,
 * KHÔNG tự activate Workspace office, KHÔNG tự deploy Project agent (CLAUDE.md
 * quy tắc #5). Trả về 2 hành động Founder tách biệt vì chúng là 2 endpoint
 * khác nhau với phạm vi tác động khác nhau (activate = toàn Workspace, deploy
 * = 1 Project cụ thể) — không được gộp làm 1 danh sách như bản cũ.
 */
export async function getStageSuggestion(
  ctx: TenantContext,
  projectId: string
): Promise<StageSuggestion> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ lifecycleStage: projects.lifecycleStage })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }

  const stage = project.lifecycleStage;
  const stageEligibleRoles = [...roleKeysForStage(stage)];

  const board = await getWorkspaceExecutiveRoleStates(ctx);
  const boardByRole = new Map(board.roles.map((r) => [r.roleKey, r]));

  const workspaceOfficeToEnable: ExecutiveRoleKey[] = [];
  const projectAgentsToDeploy: ExecutiveRoleKey[] = [];

  for (const roleKey of stageEligibleRoles) {
    const boardRole = boardByRole.get(roleKey);

    if (boardRole?.displayState === "AVAILABLE_NOT_ACTIVATED") {
      workspaceOfficeToEnable.push(roleKey);
      continue;
    }

    if (boardRole?.displayState === "ACTIVE") {
      const roleDef = EXECUTIVE_ROLE_CATALOG[roleKey];
      const authority = await resolveProjectAgentAuthorityV2(
        { workspaceId: ctx.workspaceId, projectId },
        { projectId, profileKey: roleDef.requiredProfileKey }
      );
      if (authority.v2Deployment.state !== "ACTIVE") {
        projectAgentsToDeploy.push(roleKey);
      }
    }

    // UNAVAILABLE (agent nền chưa chạy ở project nào) hoặc DISABLED (Founder
    // đã tắt tường minh) → không gợi ý gì, để tránh gợi ý bật lại thứ Founder
    // vừa chủ động tắt.
  }

  return { stage, workspaceOfficeToEnable, projectAgentsToDeploy, stageEligibleRoles };
}
