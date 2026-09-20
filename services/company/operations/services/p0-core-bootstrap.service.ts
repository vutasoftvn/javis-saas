import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { ExecutiveRoleKey } from "../../shared/contracts/executive-advisor-roles.generated";
import {
  getProjectExecutiveRoleStates,
  requireExecutiveBoardFounderAuthority,
} from "./executive-role-activation.service";
import {
  activateProjectStartupTeamMember,
  ensureProjectStartupTeam,
  listProjectStartupTeam,
} from "./project-startup-team.service";
import { activateWorkspaceExecutiveRole } from "./workspace-executive-role-activation.service";
import { deployAgentToProject } from "./founder-asset-deployment.service";

const { projects } = schema;

/**
 * P0 Core là workforce mặc định duy nhất được Founder chấp thuận để khởi tạo
 * cùng một Project greenfield: điều phối, tài chính, marketing và product.
 * Danh sách này được giữ song song với PERSISTENT_EXECUTIVE_ROLES vì đây là
 * policy thực thi (không phải chỉ một gợi ý hiển thị theo stage).
 */
export const P0_CORE_ROLES = Object.freeze([
  { roleKey: "chief_of_staff", profileKey: "operations" },
  { roleKey: "cfo", profileKey: "finance" },
  { roleKey: "cmo", profileKey: "marketing" },
  { roleKey: "cpo", profileKey: "product" },
] as const satisfies readonly { roleKey: ExecutiveRoleKey; profileKey: string }[]);

export interface P0CoreBootstrapResult {
  readonly projectId: string;
  readonly roleKeys: readonly ExecutiveRoleKey[];
}

/**
 * Hội tụ P0 Core về trạng thái có thể tư vấn ngay trên một Project P0.
 *
 * Các primitive bên dưới đều append-only/idempotent theo trạng thái hiện hữu:
 * vì vậy một retry sau khi process lỗi giữa chừng chỉ hoàn tất phần còn thiếu,
 * không nhân đôi workforce, Workspace Agent hoặc Project deployment. Không
 * được gọi khi đọc Board hoặc khi chuyển stage; chỉ caller tạo Project NEW và
 * lệnh Founder tường minh cho Project P0 có sẵn được phép gọi vào đây.
 */
export async function bootstrapP0CoreForProject(
  ctx: TenantContext,
  projectId: string
): Promise<P0CoreBootstrapResult> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

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
  if (project.lifecycleStage !== "P0_DISCOVERY") {
    throw APIError.failedPrecondition("P0_CORE_BOOTSTRAP_REQUIRES_P0_PROJECT");
  }

  // 1. Materialize agent nền và Workspace Agent cho đúng Project P0.
  await db.transaction(async (tx) => {
    await ensureProjectStartupTeam(tx, {
      workspaceId: ctx.workspaceId,
      projectId,
      actorId: ctx.userId ?? ctx.workspaceId,
    });
  });

  let startupTeam = await listProjectStartupTeam({
    workspaceId: ctx.workspaceId,
    projectId,
  });
  for (const coreRole of P0_CORE_ROLES) {
    const member = startupTeam.find((item) => item.profileKey === coreRole.profileKey);
    if (!member?.assignmentVersion) {
      throw APIError.failedPrecondition(
        `P0_CORE_PROFILE_UNAVAILABLE: ${coreRole.profileKey}`
      );
    }
    if (member.displayState !== "ACTIVE") {
      await activateProjectStartupTeamMember(ctx, projectId, coreRole.profileKey, {
        expectedVersion: member.assignmentVersion,
        idempotencyKey: `p0-core:${projectId}:activate-profile:${coreRole.profileKey}`,
      });
      // Tải lại để retry/khởi tạo từ template luôn dùng đúng CAS version.
      startupTeam = await listProjectStartupTeam({ workspaceId: ctx.workspaceId, projectId });
    }
  }

  // 2. Bật bốn Workspace Office. Activation scope là Workspace, nhưng chỉ
  // những Project P0 được bootstrap mới được deploy agent ở bước 3.
  for (const coreRole of P0_CORE_ROLES) {
    await activateWorkspaceExecutiveRole(ctx, coreRole.roleKey, {
      idempotencyKey: `p0-core:${projectId}:activate-office:${coreRole.roleKey}`,
    });
  }

  // 3. Deploy đúng Workspace Agent vào đúng Project. Đọc lại board để server
  // (không phải client) resolve agent id / trạng thái deployment thật.
  const beforeDeploy = await getProjectExecutiveRoleStates(ctx, projectId);
  for (const coreRole of P0_CORE_ROLES) {
    const role = beforeDeploy.roles.find((item) => item.roleKey === coreRole.roleKey);
    if (!role?.workspaceAgentId) {
      throw APIError.failedPrecondition(
        `P0_CORE_WORKSPACE_AGENT_UNAVAILABLE: ${coreRole.roleKey}`
      );
    }
    if (role.projectDeploymentState !== "ACTIVE") {
      await deployAgentToProject(ctx, {
        projectId,
        workspaceAgentId: role.workspaceAgentId,
        reason: `Bootstrap P0 Core: ${coreRole.roleKey}`,
        idempotencyKey: `p0-core:${projectId}:deploy:${coreRole.roleKey}`,
      });
    }
  }

  return { projectId, roleKeys: P0_CORE_ROLES.map((item) => item.roleKey) };
}
