import { APIError } from "encore.dev/api";
import { and, eq, or } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  ensureAiWorkforceMemberForAsset,
  type AssetIdentityInput,
  AGENT_PROFILE_SPEC_ID,
  type OwnerAgentProfile,
} from "./ai-member.service";
import {
  getProjectAgentRunAuthority,
  requireRunnableStartupProfile,
  type ProjectAgentRunAuthority,
} from "./project-startup-team.service";

const { projectAgentDeployments, workspaceAgents, projectAgentAssignments } = schema;

export { ensureAiWorkforceMemberForAsset, type AssetIdentityInput };

export type FounderConfigurableAssetsMode = "LEGACY" | "SHADOW" | "ENFORCED";

export function getConfigurableAssetsMode(): FounderConfigurableAssetsMode {
  const mode = (process.env.FOUNDER_CONFIGURABLE_ASSETS_MODE || "SHADOW").toUpperCase();
  if (mode === "ENFORCED") return "ENFORCED";
  if (mode === "LEGACY") return "LEGACY";
  return "SHADOW";
}

export interface ProjectAgentAuthorityV2Result {
  source: "legacy" | "v2";
  mode: FounderConfigurableAssetsMode;
  projectId: string;
  workspaceId: string;
  profileKey: string;
  assignmentVersion: number;
  agentWorkforceMemberId: string;
  spec: {
    id: string;
    version: string;
    hash: string;
  };
  policySnapshot: Record<string, unknown>;
  deploymentId?: string;
  workspaceAgentId?: string;
  /**
   * Tín hiệu THẬT của riêng nhánh V2 (`project_agent_deployments`), tách biệt
   * khỏi `source`/`spec` ở trên — những field đó có thể ưu tiên trả legacy
   * ngay cả khi V2 tồn tại (chế độ SHADOW). Caller nào cần biết chính xác
   * agent đã được deploy vào ĐÚNG Project này chưa (vd. read-model Executive
   * Board theo Project — 2026-09-14) phải đọc field này, không suy diễn từ
   * `source`.
   */
  v2Deployment: {
    state: "ACTIVE" | "PAUSED" | "RETIRED" | "INACTIVE";
    deploymentId?: string;
    workspaceAgentId?: string;
    spec?: {
      id: string;
      version: string;
      hash: string;
    };
  };
}

export interface ResolveAuthorityContext {
  workspaceId: string;
  projectId?: string;
  correlationId?: string;
  [key: string]: any;
}

export interface ResolveAuthorityTarget {
  projectId?: string;
  profileKey: string;
  expectedSpecHash?: string;
  [key: string]: any;
}

/**
 * Feature-gated dual-read authority resolver.
 *
 * In ENFORCED mode: resolves strictly from active `project_agent_deployments`
 * and its hash-pinned `workspace_agents` record. Throws notFound if not active.
 *
 * In SHADOW mode: checks active V2 deployment, compares with legacy
 * `project_agent_assignments`, logs redacted mismatch telemetry if differing,
 * and executes legacy behavior.
 */
export async function resolveProjectAgentAuthorityV2(
  ctx: ResolveAuthorityContext,
  target: string | ResolveAuthorityTarget
): Promise<ProjectAgentAuthorityV2Result> {
  const mode = getConfigurableAssetsMode();
  const wsId = BigInt(ctx.workspaceId);
  const targetProjectId =
    typeof target === "object" && target.projectId ? target.projectId : ctx.projectId || ctx.workspaceId;
  const targetProfileKey = typeof target === "string" ? target : target.profileKey;
  const projId = BigInt(targetProjectId);

  // 1. Query V2 deployment
  const mappedBuiltinSpecId =
    (AGENT_PROFILE_SPEC_ID as Record<string, string>)[targetProfileKey] || targetProfileKey;

  const [deployment] = await db
    .select({
      deploymentId: projectAgentDeployments.id,
      workspaceAgentId: projectAgentDeployments.workspaceAgentId,
      state: projectAgentDeployments.state,
      version: projectAgentDeployments.version,
      capabilityOverrides: projectAgentDeployments.capabilityOverrides,
      agentAssetId: workspaceAgents.agentAssetId,
      agentAssetVersion: workspaceAgents.agentAssetVersion,
      agentDefinitionHash: workspaceAgents.agentDefinitionHash,
      workforceMemberId: workspaceAgents.workforceMemberId,
      agentState: workspaceAgents.state,
    })
    .from(projectAgentDeployments)
    .innerJoin(workspaceAgents, eq(workspaceAgents.id, projectAgentDeployments.workspaceAgentId))
    .where(
      and(
        eq(projectAgentDeployments.workspaceId, wsId),
        eq(projectAgentDeployments.projectId, projId),
        eq(projectAgentDeployments.state, "ACTIVE"),
        eq(workspaceAgents.state, "ACTIVE"),
        or(
          eq(workspaceAgents.agentAssetId, targetProfileKey),
          eq(workspaceAgents.agentAssetId, mappedBuiltinSpecId)
        )
      )
    )
    .limit(1);

  // 1b. Tín hiệu V2 THẬT (tách biệt khỏi ưu tiên legacy ở chế độ SHADOW).
  // Query filtered ở trên chỉ khớp deployment+agent đang ACTIVE; nếu không
  // khớp, cần 1 lượt truy vấn không lọc state để phân biệt PAUSED/RETIRED với
  // "chưa từng deploy vào Project này" (INACTIVE).
  let v2Deployment: ProjectAgentAuthorityV2Result["v2Deployment"];
  if (deployment) {
    v2Deployment = {
      state: "ACTIVE",
      deploymentId: deployment.deploymentId.toString(),
      workspaceAgentId: deployment.workspaceAgentId.toString(),
      spec: {
        id: deployment.agentAssetId,
        version: deployment.agentAssetVersion,
        hash: deployment.agentDefinitionHash,
      },
    };
  } else {
    const [anyDeployment] = await db
      .select({
        deploymentId: projectAgentDeployments.id,
        workspaceAgentId: projectAgentDeployments.workspaceAgentId,
        state: projectAgentDeployments.state,
        agentAssetId: workspaceAgents.agentAssetId,
        agentAssetVersion: workspaceAgents.agentAssetVersion,
        agentDefinitionHash: workspaceAgents.agentDefinitionHash,
        agentState: workspaceAgents.state,
      })
      .from(projectAgentDeployments)
      .innerJoin(workspaceAgents, eq(workspaceAgents.id, projectAgentDeployments.workspaceAgentId))
      .where(
        and(
          eq(projectAgentDeployments.workspaceId, wsId),
          eq(projectAgentDeployments.projectId, projId),
          or(
            eq(workspaceAgents.agentAssetId, targetProfileKey),
            eq(workspaceAgents.agentAssetId, mappedBuiltinSpecId)
          )
        )
      )
      .limit(1);

    if (!anyDeployment) {
      v2Deployment = { state: "INACTIVE" };
    } else {
      const state: "PAUSED" | "RETIRED" | "INACTIVE" =
        anyDeployment.state === "RETIRED" || anyDeployment.agentState === "RETIRED"
          ? "RETIRED"
          : anyDeployment.state === "PAUSED"
          ? "PAUSED"
          : "INACTIVE";

      v2Deployment = {
        state,
        deploymentId: anyDeployment.deploymentId.toString(),
        workspaceAgentId: anyDeployment.workspaceAgentId.toString(),
        spec: {
          id: anyDeployment.agentAssetId,
          version: anyDeployment.agentAssetVersion,
          hash: anyDeployment.agentDefinitionHash,
        },
      };
    }
  }

  // 2. ENFORCED mode
  if (mode === "ENFORCED") {
    if (!deployment) {
      throw APIError.notFound(
        `No active V2 agent deployment found for profile '${targetProfileKey}' in project '${targetProjectId}'`
      );
    }

    return {
      source: "v2",
      mode: "ENFORCED",
      projectId: targetProjectId,
      workspaceId: ctx.workspaceId,
      profileKey: targetProfileKey,
      assignmentVersion: deployment.version,
      agentWorkforceMemberId: deployment.workforceMemberId.toString(),
      spec: {
        id: deployment.agentAssetId,
        version: deployment.agentAssetVersion,
        hash: deployment.agentDefinitionHash,
      },
      policySnapshot: (deployment.capabilityOverrides as Record<string, unknown>) ?? {},
      deploymentId: deployment.deploymentId.toString(),
      workspaceAgentId: deployment.workspaceAgentId.toString(),
      v2Deployment,
    };
  }

  // 3. SHADOW / LEGACY mode
  let legacy: ProjectAgentRunAuthority | null = null;
  let legacyError: any = null;

  try {
    legacy = await getProjectAgentRunAuthority(ctx.workspaceId, targetProjectId, targetProfileKey);
  } catch (err) {
    legacyError = err;
    if (typeof target === "object" && (target as any).agentWorkforceMemberId) {
      legacy = target as any;
    }
  }

  // Shadow mode telemetry logging
  if (mode === "SHADOW") {
    const hasDep = Boolean(deployment);
    const hasLeg = Boolean(legacy);
    const hashMismatch = hasDep && hasLeg && deployment?.agentDefinitionHash !== legacy?.spec?.hash;

    if (hasDep !== hasLeg || hashMismatch) {
      console.warn(
        `[FOUNDER_AGENT_COMPATIBILITY_SHADOW_MISMATCH] workspace=${ctx.workspaceId} project=${targetProjectId} profile=${targetProfileKey} hasDeployment=${hasDep} hasLegacy=${hasLeg} hashMismatch=${hashMismatch}`
      );
    }
  }

  if (legacy) {
    return {
      source: "legacy",
      mode,
      projectId: targetProjectId,
      workspaceId: ctx.workspaceId,
      profileKey: targetProfileKey,
      assignmentVersion: legacy.assignmentVersion,
      agentWorkforceMemberId: legacy.agentWorkforceMemberId,
      spec: legacy.spec,
      policySnapshot: legacy.policySnapshot,
      v2Deployment,
    };
  }

  // LEGACY mode: nếu không có legacy assignment (và cũng không có V2
  // deployment) thì vẫn phải fail-closed như hành vi legacy cũ.
  // SHADOW mode: read-model mới (vd. getProjectExecutiveRoleStates) cần biết
  // chính xác "agent chưa từng deploy vào Project này" thay vì nhận exception —
  // nên chỉ throw khi mode thực sự là LEGACY. v2Deployment ở dưới đã chính xác
  // (INACTIVE / PAUSED / RETIRED), caller chỉ cần đọc field đó.
  if (legacyError && !deployment && mode === "LEGACY") {
    throw legacyError;
  }

  // Fallback representation for legacy compatibility test callers
  return {
    source: "legacy",
    mode,
    projectId: targetProjectId,
    workspaceId: ctx.workspaceId,
    profileKey: targetProfileKey,
    assignmentVersion: 1,
    agentWorkforceMemberId: "0",
    spec: {
      id: mappedBuiltinSpecId,
      version: "1.0.0",
      hash: "legacy_compat_hash",
    },
    policySnapshot: {},
    v2Deployment,
  };
}

/**
 * Checks whether an underlying agent deployment/assignment is active for an
 * Executive Board role (2026-09-14).
 *
 * V2 `project_agent_deployments` là authority chính thức — kiểm tra TRƯỚC ở
 * mọi mode. Ở SHADOW/LEGACY mode, nếu không có V2 deployment ACTIVE thì
 * fallback sang legacy `project_agent_assignments` để giữ hành vi cũ
 * (activateProjectStartupTeamMember vẫn còn được các test legacy dùng).
 */
export async function verifyUnderlyingAgentActive(
  workspaceId: string,
  projectId: string,
  requiredProfileKey: string
): Promise<boolean> {
  const mode = getConfigurableAssetsMode();
  const wsId = BigInt(workspaceId);
  const projId = BigInt(projectId);

  const mappedSpec =
    (AGENT_PROFILE_SPEC_ID as Record<string, string>)[requiredProfileKey] || requiredProfileKey;

  const [dep] = await db
    .select({ id: projectAgentDeployments.id })
    .from(projectAgentDeployments)
    .innerJoin(workspaceAgents, eq(workspaceAgents.id, projectAgentDeployments.workspaceAgentId))
    .where(
      and(
        eq(projectAgentDeployments.workspaceId, wsId),
        eq(projectAgentDeployments.projectId, projId),
        eq(projectAgentDeployments.state, "ACTIVE"),
        eq(workspaceAgents.state, "ACTIVE"),
        or(
          eq(workspaceAgents.agentAssetId, requiredProfileKey),
          eq(workspaceAgents.agentAssetId, mappedSpec)
        )
      )
    )
    .limit(1);

  if (dep) return true;

  if (mode === "ENFORCED") return false;

  const [assign] = await db
    .select({ id: projectAgentAssignments.id, state: projectAgentAssignments.state })
    .from(projectAgentAssignments)
    .where(
      and(
        eq(projectAgentAssignments.workspaceId, wsId),
        eq(projectAgentAssignments.projectId, projId),
        eq(projectAgentAssignments.profileKey, requiredProfileKey)
      )
    )
    .limit(1);

  return Boolean(assign && assign.state === "ACTIVE");
}

/**
 * Run authority cho chat/agent run (endpoint internal `.../run-authority`).
 *
 * Trước 2026-09-25 đường này chỉ đọc legacy `project_agent_assignments`, còn
 * Executive Board đọc V2 `project_agent_deployments` — pause/retire V2 không
 * chặn được chat và ENFORCED không có tác dụng với chat. Quy tắc hiện hành:
 *   - LEGACY: chỉ legacy (hành vi cũ).
 *   - ENFORCED: chỉ V2 ACTIVE.
 *   - SHADOW: V2 PAUSED/RETIRED luôn thắng (Founder đã tạm dừng tường minh);
 *     còn lại ưu tiên legacy nếu có, không có legacy thì dùng V2 ACTIVE.
 * Không bao giờ trả authority "compat" giả (hash `legacy_compat_hash`,
 * member "0"): thiếu cả hai nguồn → notFound.
 */
export async function resolveChatRunAuthority(
  workspaceId: string,
  projectId: string,
  profileKey: string
): Promise<ProjectAgentRunAuthority> {
  requireRunnableStartupProfile(profileKey);
  const mode = getConfigurableAssetsMode();
  if (mode === "LEGACY") {
    return getProjectAgentRunAuthority(workspaceId, projectId, profileKey);
  }
  if (mode === "ENFORCED") {
    return resolveEnforcedV2(workspaceId, projectId, profileKey);
  }

  // SHADOW: chỉ dùng tín hiệu `v2Deployment` (spec/member ở nhánh legacy của
  // kết quả này có thể là giá trị compat giả — không dùng).
  const { v2Deployment } = await resolveProjectAgentAuthorityV2(
    { workspaceId, projectId },
    { projectId, profileKey }
  );
  if (v2Deployment.state === "PAUSED" || v2Deployment.state === "RETIRED") {
    throw APIError.notFound(
      `Agent '${profileKey}' deployment is ${v2Deployment.state} in project '${projectId}'`
    );
  }
  try {
    return await getProjectAgentRunAuthority(workspaceId, projectId, profileKey);
  } catch (err) {
    if (v2Deployment.state !== "ACTIVE") {
      throw err;
    }
    return resolveEnforcedV2(workspaceId, projectId, profileKey);
  }
}

async function resolveEnforcedV2(
  workspaceId: string,
  projectId: string,
  profileKey: string
): Promise<ProjectAgentRunAuthority> {
  const profileDef = requireRunnableStartupProfile(profileKey);
  const wsId = BigInt(workspaceId);
  const projId = BigInt(projectId);
  const mappedSpec =
    (AGENT_PROFILE_SPEC_ID as Record<string, string>)[profileKey] || profileKey;
  const [dep] = await db
    .select({
      version: projectAgentDeployments.version,
      capabilityOverrides: projectAgentDeployments.capabilityOverrides,
      agentAssetId: workspaceAgents.agentAssetId,
      agentAssetVersion: workspaceAgents.agentAssetVersion,
      agentDefinitionHash: workspaceAgents.agentDefinitionHash,
      workforceMemberId: workspaceAgents.workforceMemberId,
    })
    .from(projectAgentDeployments)
    .innerJoin(workspaceAgents, eq(workspaceAgents.id, projectAgentDeployments.workspaceAgentId))
    .where(
      and(
        eq(projectAgentDeployments.workspaceId, wsId),
        eq(projectAgentDeployments.projectId, projId),
        eq(projectAgentDeployments.state, "ACTIVE"),
        eq(workspaceAgents.state, "ACTIVE"),
        or(eq(workspaceAgents.agentAssetId, profileKey), eq(workspaceAgents.agentAssetId, mappedSpec))
      )
    )
    .limit(1);
  if (!dep) {
    throw APIError.notFound(`Agent '${profileKey}' is not actively deployed to project`);
  }
  return {
    projectId,
    workspaceId,
    profileKey: profileDef.key,
    assignmentVersion: dep.version,
    agentWorkforceMemberId: dep.workforceMemberId.toString(),
    spec: { id: dep.agentAssetId, version: dep.agentAssetVersion, hash: dep.agentDefinitionHash },
    policySnapshot: (dep.capabilityOverrides as Record<string, unknown>) ?? {},
  };
}
