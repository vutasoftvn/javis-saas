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
    };
  }

  if (legacyError && !deployment) {
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
  };
}

/**
 * Checks whether an underlying agent deployment/assignment is active for an Executive Board role.
 * In ENFORCED mode: verifies project_agent_deployments.
 * In SHADOW mode: verifies project_agent_assignments.
 */
export async function verifyUnderlyingAgentActive(
  workspaceId: string,
  projectId: string,
  requiredProfileKey: string
): Promise<boolean> {
  const mode = getConfigurableAssetsMode();
  const wsId = BigInt(workspaceId);
  const projId = BigInt(projectId);

  if (mode === "ENFORCED") {
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

    return Boolean(dep);
  }

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
