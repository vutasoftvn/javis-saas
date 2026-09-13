import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { requireFounderCommand } from "../../identity/services/command-authority.service";

const {
  projects,
  workspaceOperatingRoles,
  workspaceAgents,
  roleAgentBindings,
  projectRoleDeployments,
  projectAgentDeployments,
  projectWorkflowBindings,
  founderAssetEvents,
} = schema;

function assertHumanFounder(ctx: TenantContext, action: string): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(`AI agent cannot execute founder commands: ${action}`);
  }
  requireFounderCommand(ctx, action);
}

async function validateProjectInWorkspace(workspaceId: bigint, projectId: bigint): Promise<void> {
  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projectId), eq(projects.workspaceId, workspaceId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found in workspace");
  }
}

export interface WorkspaceOperatingRoleDto {
  readonly id: string;
  readonly workspaceId: string;
  readonly roleCode: string;
  readonly name: string;
  readonly description?: string | null;
  readonly state: string;
  readonly version: number;
}

export interface WorkspaceAgentDto {
  readonly id: string;
  readonly workspaceId: string;
  readonly agentAssetId: string;
  readonly agentAssetVersion: string;
  readonly agentDefinitionHash: string;
  readonly workforceMemberId: string;
  readonly state: string;
  readonly originKind: string;
  readonly version: number;
}

export interface RoleAgentBindingDto {
  readonly id: string;
  readonly workspaceId: string;
  readonly roleId: string;
  readonly workspaceAgentId: string;
  readonly isPrimary: boolean;
}

export interface ProjectRoleDeploymentDto {
  readonly id: string;
  readonly workspaceId: string;
  readonly projectId: string;
  readonly roleId: string;
  readonly state: string;
  readonly policyOverride: Record<string, any>;
  readonly budgetLimit?: Record<string, any> | null;
  readonly version: number;
}

export interface ProjectAgentDeploymentDto {
  readonly id: string;
  readonly workspaceId: string;
  readonly projectId: string;
  readonly workspaceAgentId: string;
  readonly projectRoleDeploymentId?: string | null;
  readonly state: string;
  readonly capabilityOverrides: readonly any[];
  readonly version: number;
}

export interface ProjectWorkflowBindingDto {
  readonly id: string;
  readonly workspaceId: string;
  readonly projectId: string;
  readonly workflowAssetId: string;
  readonly workflowAssetVersion: string;
  readonly workflowDefinitionHash: string;
  readonly state: string;
  readonly executionPolicy: Record<string, any>;
  readonly version: number;
}

export interface ProjectDeploymentAuthority {
  readonly workspaceId: string;
  readonly projectAgentDeploymentId: string;
  readonly workspaceAgentId: string;
  readonly workforceMemberId: string;
  readonly agentSpec: { id: string; version: string; definitionHash: string };
  readonly roleIds: readonly string[];
  readonly projectId: string;
  readonly state: "ACTIVE" | "PAUSED" | "RETIRED";
  readonly capabilityRestrictions?: readonly any[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isExactWorkflowAssetReference(
  value: unknown,
  workflowAssetId: string,
  workflowAssetVersion: string,
  workflowDefinitionHash: string
): boolean {
  return isRecord(value)
    && value.assetId === workflowAssetId
    && value.version === workflowAssetVersion
    && value.definitionHash === workflowDefinitionHash;
}

function isSuccessfulPublishedWorkflowReceipt(
  event: typeof founderAssetEvents.$inferSelect,
  input: {
    workflowAssetId: string;
    workflowAssetVersion: string;
    workflowDefinitionHash: string;
  }
): boolean {
  if (
    event.projectId !== null
    || event.command !== "PUBLISH"
    || event.targetKind !== "WORKFLOW"
    || event.afterHash !== input.workflowDefinitionHash
    || !isExactWorkflowAssetReference(
      event.targetRef,
      input.workflowAssetId,
      input.workflowAssetVersion,
      input.workflowDefinitionHash
    )
  ) {
    return false;
  }

  const metadata = isRecord(event.metadata) ? event.metadata : {};
  return metadata.status === "SUCCESS"
    && isExactWorkflowAssetReference(
      metadata.updatedAssetRef,
      input.workflowAssetId,
      input.workflowAssetVersion,
      input.workflowDefinitionHash
    );
}

export async function createOperatingRole(
  ctx: TenantContext,
  input: {
    roleCode: string;
    name: string;
    description?: string;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<WorkspaceOperatingRoleDto> {
  assertHumanFounder(ctx, "createOperatingRole");
  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.userId);

  return db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(workspaceOperatingRoles)
      .where(and(eq(workspaceOperatingRoles.workspaceId, wsId), eq(workspaceOperatingRoles.roleCode, input.roleCode)))
      .limit(1);

    if (existing) {
      return {
        id: existing.id.toString(),
        workspaceId: existing.workspaceId.toString(),
        roleCode: existing.roleCode,
        name: existing.name,
        description: existing.description,
        state: existing.state,
        version: existing.version,
      };
    }

    const roleId = generateSnowflake();
    await tx.insert(workspaceOperatingRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleCode: input.roleCode,
      name: input.name,
      description: input.description,
      state: "ACTIVE",
      createdBy: actorId,
      version: 1,
    });

    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      actorId,
      command: "createOperatingRole",
      targetKind: "ROLE",
      targetRef: { roleId: roleId.toString(), roleCode: input.roleCode },
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: roleId.toString(),
      workspaceId: wsId.toString(),
      roleCode: input.roleCode,
      name: input.name,
      description: input.description,
      state: "ACTIVE",
      version: 1,
    };
  });
}

export async function createWorkspaceAgent(
  ctx: TenantContext,
  input: {
    agentAssetId: string;
    agentAssetVersion: string;
    agentDefinitionHash: string;
    workforceMemberId: string;
    originKind: string;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<WorkspaceAgentDto> {
  assertHumanFounder(ctx, "createWorkspaceAgent");
  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.userId);
  const memberId = BigInt(input.workforceMemberId);

  return db.transaction(async (tx) => {
    const [member] = await tx
      .select({ id: identityWorkforceMembers.id })
      .from(identityWorkforceMembers)
      .where(
        and(
          eq(identityWorkforceMembers.id, memberId),
          eq(identityWorkforceMembers.workspaceId, wsId)
        )
      )
      .limit(1);

    if (!member) {
      throw APIError.notFound("Workforce member not found in workspace");
    }

    const [existing] = await tx
      .select()
      .from(workspaceAgents)
      .where(and(eq(workspaceAgents.workspaceId, wsId), eq(workspaceAgents.agentAssetId, input.agentAssetId)))
      .limit(1);

    if (existing) {
      return {
        id: existing.id.toString(),
        workspaceId: existing.workspaceId.toString(),
        agentAssetId: existing.agentAssetId,
        agentAssetVersion: existing.agentAssetVersion,
        agentDefinitionHash: existing.agentDefinitionHash,
        workforceMemberId: existing.workforceMemberId.toString(),
        state: existing.state,
        originKind: existing.originKind,
        version: existing.version,
      };
    }

    const agentId = generateSnowflake();
    await tx.insert(workspaceAgents).values({
      id: agentId,
      workspaceId: wsId,
      agentAssetId: input.agentAssetId,
      agentAssetVersion: input.agentAssetVersion,
      agentDefinitionHash: input.agentDefinitionHash,
      workforceMemberId: memberId,
      state: "ACTIVE",
      originKind: input.originKind,
      createdBy: actorId,
      version: 1,
    });

    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      actorId,
      command: "createWorkspaceAgent",
      targetKind: "AGENT",
      targetRef: { workspaceAgentId: agentId.toString(), agentAssetId: input.agentAssetId },
      afterHash: input.agentDefinitionHash,
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: agentId.toString(),
      workspaceId: wsId.toString(),
      agentAssetId: input.agentAssetId,
      agentAssetVersion: input.agentAssetVersion,
      agentDefinitionHash: input.agentDefinitionHash,
      workforceMemberId: memberId.toString(),
      state: "ACTIVE",
      originKind: input.originKind,
      version: 1,
    };
  });
}

export async function bindRoleAgent(
  ctx: TenantContext,
  input: {
    roleId: string;
    workspaceAgentId: string;
    isPrimary?: boolean;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<RoleAgentBindingDto> {
  assertHumanFounder(ctx, "bindRoleAgent");
  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.userId);
  const roleId = BigInt(input.roleId);
  const agentId = BigInt(input.workspaceAgentId);

  return db.transaction(async (tx) => {
    const [agent] = await tx
      .select()
      .from(workspaceAgents)
      .where(and(eq(workspaceAgents.id, agentId), eq(workspaceAgents.workspaceId, wsId)))
      .limit(1);

    if (!agent || agent.state !== "ACTIVE") {
      throw APIError.invalidArgument("Active workspace agent from same workspace required");
    }

    const [role] = await tx
      .select()
      .from(workspaceOperatingRoles)
      .where(and(eq(workspaceOperatingRoles.id, roleId), eq(workspaceOperatingRoles.workspaceId, wsId)))
      .limit(1);

    if (!role || role.state !== "ACTIVE") {
      throw APIError.invalidArgument("Active operating role from same workspace required");
    }

    const [existing] = await tx
      .select()
      .from(roleAgentBindings)
      .where(
        and(
          eq(roleAgentBindings.workspaceId, wsId),
          eq(roleAgentBindings.roleId, roleId),
          eq(roleAgentBindings.workspaceAgentId, agentId)
        )
      )
      .limit(1);

    if (existing) {
      return {
        id: existing.id.toString(),
        workspaceId: existing.workspaceId.toString(),
        roleId: existing.roleId.toString(),
        workspaceAgentId: existing.workspaceAgentId.toString(),
        isPrimary: existing.isPrimary,
      };
    }

    const bindingId = generateSnowflake();
    await tx.insert(roleAgentBindings).values({
      id: bindingId,
      workspaceId: wsId,
      roleId,
      workspaceAgentId: agentId,
      isPrimary: input.isPrimary ?? false,
      createdBy: actorId,
    });

    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      actorId,
      command: "bindRoleAgent",
      targetKind: "ROLE",
      targetRef: { roleId: input.roleId, workspaceAgentId: input.workspaceAgentId },
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: bindingId.toString(),
      workspaceId: wsId.toString(),
      roleId: input.roleId,
      workspaceAgentId: input.workspaceAgentId,
      isPrimary: input.isPrimary ?? false,
    };
  });
}

export async function deployRoleToProject(
  ctx: TenantContext,
  input: {
    projectId: string;
    roleId: string;
    expectedVersion?: number;
    policyOverride?: Record<string, any>;
    budgetLimit?: Record<string, any>;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<ProjectRoleDeploymentDto> {
  assertHumanFounder(ctx, "deployRoleToProject");
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(input.projectId);
  const roleId = BigInt(input.roleId);
  const actorId = BigInt(ctx.userId);

  await validateProjectInWorkspace(wsId, projId);

  return db.transaction(async (tx) => {
    const [role] = await tx
      .select()
      .from(workspaceOperatingRoles)
      .where(and(eq(workspaceOperatingRoles.id, roleId), eq(workspaceOperatingRoles.workspaceId, wsId)))
      .limit(1);

    if (!role || role.state !== "ACTIVE") {
      throw APIError.invalidArgument("Active operating role required");
    }

    const [existing] = await tx
      .select()
      .from(projectRoleDeployments)
      .where(
        and(
          eq(projectRoleDeployments.workspaceId, wsId),
          eq(projectRoleDeployments.projectId, projId),
          eq(projectRoleDeployments.roleId, roleId)
        )
      )
      .limit(1);

    if (existing) {
      if (input.expectedVersion !== undefined && existing.version !== input.expectedVersion) {
        throw APIError.aborted("Stale expectedVersion for project role deployment");
      }

      const nextVersion = existing.version + 1;
      await tx
        .update(projectRoleDeployments)
        .set({
          state: "ACTIVE",
          policyOverride: input.policyOverride ?? existing.policyOverride,
          budgetLimit: input.budgetLimit !== undefined ? input.budgetLimit : existing.budgetLimit,
          version: nextVersion,
          updatedAt: new Date(),
        })
        .where(eq(projectRoleDeployments.id, existing.id));

      const eventId = generateSnowflake();
      await tx.insert(founderAssetEvents).values({
        id: eventId,
        workspaceId: wsId,
        projectId: projId,
        actorId,
        command: "updateProjectRoleDeployment",
        targetKind: "DEPLOYMENT",
        targetRef: { deploymentId: existing.id.toString(), roleId: input.roleId },
        reason: input.reason,
        correlationId: ctx.correlationId || generateSnowflake().toString(),
        metadata: { idempotencyKey: input.idempotencyKey },
      });

      return {
        id: existing.id.toString(),
        workspaceId: wsId.toString(),
        projectId: projId.toString(),
        roleId: input.roleId,
        state: "ACTIVE",
        policyOverride: (input.policyOverride ?? existing.policyOverride) as Record<string, any>,
        budgetLimit: input.budgetLimit !== undefined ? input.budgetLimit : (existing.budgetLimit as Record<string, any> | null),
        version: nextVersion,
      };
    }

    const deploymentId = generateSnowflake();
    await tx.insert(projectRoleDeployments).values({
      id: deploymentId,
      workspaceId: wsId,
      projectId: projId,
      roleId,
      state: "ACTIVE",
      policyOverride: input.policyOverride ?? {},
      budgetLimit: input.budgetLimit,
      version: 1,
      createdBy: actorId,
    });

    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      projectId: projId,
      actorId,
      command: "deployRoleToProject",
      targetKind: "DEPLOYMENT",
      targetRef: { deploymentId: deploymentId.toString(), roleId: input.roleId },
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: deploymentId.toString(),
      workspaceId: wsId.toString(),
      projectId: projId.toString(),
      roleId: input.roleId,
      state: "ACTIVE",
      policyOverride: input.policyOverride ?? {},
      budgetLimit: input.budgetLimit ?? null,
      version: 1,
    };
  });
}

export function validateCapabilityTighteningOnly(overrides: unknown[]): void {
  if (!Array.isArray(overrides)) {
    throw APIError.invalidArgument("capabilityOverrides must be an array");
  }

  const wideningKeywords = ["ALLOW", "GRANT", "PERMIT", "ENABLE", "WIDEN"];

  for (const override of overrides) {
    if (!override || typeof override !== "object") {
      throw APIError.invalidArgument("Each capability override must be a non-null object");
    }
    const o = override as Record<string, unknown>;

    // 1. Identify target capability
    const target = o.capabilityId ?? o.capability ?? o.target ?? o.id;
    if (!target || typeof target !== "string" || target.trim().length === 0) {
      throw APIError.invalidArgument(
        "Each capability override must specify a target capability (e.g. capabilityId)"
      );
    }

    // 2. Reject widening attempts
    const effect = typeof o.effect === "string" ? o.effect.trim().toUpperCase() : undefined;
    const action = typeof o.action === "string" ? o.action.trim().toUpperCase() : undefined;
    const mode = typeof o.mode === "string" ? o.mode.trim().toUpperCase() : undefined;

    for (const kw of wideningKeywords) {
      if (effect === kw || action === kw || mode === kw) {
        throw APIError.invalidArgument(
          `Capability override for '${target}' cannot grant or expand authority (${kw}). Control Plane may only restrict authority (DENY/RESTRICT).`
        );
      }
    }

    if (o.enabled === true || o.allow === true || o.grant === true) {
      throw APIError.invalidArgument(
        `Capability override for '${target}' cannot enable or grant capabilities. Control Plane may only restrict authority.`
      );
    }

    // 3. Must be a valid restriction
    const isDenyOrRestrict = effect === "DENY" || effect === "RESTRICT";
    const isDisabled = o.enabled === false;
    const hasTighteningConstraint =
      Boolean(o.rateLimit) ||
      Boolean(o.budgetLimit) ||
      Boolean(o.maxCalls) ||
      Boolean(o.restrictions) ||
      Boolean(o.paramRestrictions);

    if (!isDenyOrRestrict && !isDisabled && !hasTighteningConstraint) {
      throw APIError.invalidArgument(
        `Capability override for '${target}' must specify a tightening restriction (e.g. effect: 'DENY' | 'RESTRICT', enabled: false, or budget/rate limits).`
      );
    }
  }
}

export async function deployAgentToProject(
  ctx: TenantContext,
  input: {
    projectId: string;
    workspaceAgentId: string;
    projectRoleDeploymentId?: string;
    capabilityOverrides?: any[];
    expectedVersion?: number;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<ProjectAgentDeploymentDto> {
  assertHumanFounder(ctx, "deployAgentToProject");
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(input.projectId);
  const agentId = BigInt(input.workspaceAgentId);
  const actorId = BigInt(ctx.userId);

  if (input.capabilityOverrides && input.capabilityOverrides.length > 0) {
    validateCapabilityTighteningOnly(input.capabilityOverrides);
  }

  await validateProjectInWorkspace(wsId, projId);

  return db.transaction(async (tx) => {
    const [agent] = await tx
      .select()
      .from(workspaceAgents)
      .where(and(eq(workspaceAgents.id, agentId), eq(workspaceAgents.workspaceId, wsId)))
      .limit(1);

    if (!agent || agent.state !== "ACTIVE") {
      throw APIError.invalidArgument("Active workspace agent required");
    }

    let roleDepId: bigint | null = null;
    if (input.projectRoleDeploymentId) {
      roleDepId = BigInt(input.projectRoleDeploymentId);
      const [roleDep] = await tx
        .select()
        .from(projectRoleDeployments)
        .where(
          and(
            eq(projectRoleDeployments.id, roleDepId),
            eq(projectRoleDeployments.workspaceId, wsId),
            eq(projectRoleDeployments.projectId, projId)
          )
        )
        .limit(1);

      if (!roleDep || roleDep.state !== "ACTIVE") {
        throw APIError.invalidArgument("Active project role deployment required");
      }
    } else {
      // Xác nhận agent thuộc ít nhất 1 role đã deploy vào project này hoặc có binding
      const bindings = await tx
        .select({ roleId: roleAgentBindings.roleId })
        .from(roleAgentBindings)
        .innerJoin(
          projectRoleDeployments,
          and(
            eq(projectRoleDeployments.roleId, roleAgentBindings.roleId),
            eq(projectRoleDeployments.projectId, projId),
            eq(projectRoleDeployments.workspaceId, wsId),
            eq(projectRoleDeployments.state, "ACTIVE")
          )
        )
        .where(
          and(
            eq(roleAgentBindings.workspaceId, wsId),
            eq(roleAgentBindings.workspaceAgentId, agentId)
          )
        )
        .limit(1);

      // Nếu không có role deployment nào cho agent này, nhưng agent là standalone hợp lệ
      // thì vẫn cho phép deploy dưới dạng project-level agent
    }

    const [existing] = await tx
      .select()
      .from(projectAgentDeployments)
      .where(
        and(
          eq(projectAgentDeployments.workspaceId, wsId),
          eq(projectAgentDeployments.projectId, projId),
          eq(projectAgentDeployments.workspaceAgentId, agentId)
        )
      )
      .limit(1);

    if (existing) {
      if (input.expectedVersion !== undefined && existing.version !== input.expectedVersion) {
        throw APIError.aborted("Stale expectedVersion for project agent deployment");
      }

      const nextVersion = existing.version + 1;
      await tx
        .update(projectAgentDeployments)
        .set({
          state: "ACTIVE",
          projectRoleDeploymentId: roleDepId ?? existing.projectRoleDeploymentId,
          capabilityOverrides: input.capabilityOverrides ?? existing.capabilityOverrides,
          version: nextVersion,
          updatedAt: new Date(),
        })
        .where(eq(projectAgentDeployments.id, existing.id));

      const eventId = generateSnowflake();
      await tx.insert(founderAssetEvents).values({
        id: eventId,
        workspaceId: wsId,
        projectId: projId,
        actorId,
        command: "updateProjectAgentDeployment",
        targetKind: "DEPLOYMENT",
        targetRef: { deploymentId: existing.id.toString(), workspaceAgentId: input.workspaceAgentId },
        reason: input.reason,
        correlationId: ctx.correlationId || generateSnowflake().toString(),
        metadata: { idempotencyKey: input.idempotencyKey },
      });

      return {
        id: existing.id.toString(),
        workspaceId: wsId.toString(),
        projectId: projId.toString(),
        workspaceAgentId: input.workspaceAgentId,
        projectRoleDeploymentId: (roleDepId ?? existing.projectRoleDeploymentId)?.toString() ?? null,
        state: "ACTIVE",
        capabilityOverrides: (input.capabilityOverrides ?? existing.capabilityOverrides) as any[],
        version: nextVersion,
      };
    }

    const deploymentId = generateSnowflake();
    await tx.insert(projectAgentDeployments).values({
      id: deploymentId,
      workspaceId: wsId,
      projectId: projId,
      workspaceAgentId: agentId,
      projectRoleDeploymentId: roleDepId,
      state: "ACTIVE",
      capabilityOverrides: input.capabilityOverrides ?? [],
      version: 1,
      createdBy: actorId,
    });

    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      projectId: projId,
      actorId,
      command: "deployAgentToProject",
      targetKind: "DEPLOYMENT",
      targetRef: { deploymentId: deploymentId.toString(), workspaceAgentId: input.workspaceAgentId },
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: deploymentId.toString(),
      workspaceId: wsId.toString(),
      projectId: projId.toString(),
      workspaceAgentId: input.workspaceAgentId,
      projectRoleDeploymentId: roleDepId ? roleDepId.toString() : null,
      state: "ACTIVE",
      capabilityOverrides: input.capabilityOverrides ?? [],
      version: 1,
    };
  });
}

export async function bindWorkflowToProject(
  ctx: TenantContext,
  input: {
    projectId: string;
    workflowAssetId: string;
    workflowAssetVersion: string;
    workflowDefinitionHash: string;
    executionPolicy?: Record<string, any>;
    expectedVersion?: number;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<ProjectWorkflowBindingDto> {
  assertHumanFounder(ctx, "bindWorkflowToProject");
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(input.projectId);
  const actorId = BigInt(ctx.userId);

  await validateProjectInWorkspace(wsId, projId);

  return db.transaction(async (tx) => {
    const workflowReceipts = await tx
      .select()
      .from(founderAssetEvents)
      .where(
        and(
          eq(founderAssetEvents.workspaceId, wsId),
          eq(founderAssetEvents.command, "PUBLISH"),
          eq(founderAssetEvents.targetKind, "WORKFLOW"),
          eq(founderAssetEvents.afterHash, input.workflowDefinitionHash)
        )
      );
    const hasPublishedReceipt = workflowReceipts.some((event) =>
      isSuccessfulPublishedWorkflowReceipt(event, input)
    );
    if (!hasPublishedReceipt) {
      throw APIError.invalidArgument(
        "Workflow binding requires an exact successful workspace workflow publish receipt"
      );
    }

    const [existing] = await tx
      .select()
      .from(projectWorkflowBindings)
      .where(
        and(
          eq(projectWorkflowBindings.workspaceId, wsId),
          eq(projectWorkflowBindings.projectId, projId),
          eq(projectWorkflowBindings.workflowAssetId, input.workflowAssetId)
        )
      )
      .limit(1);

    if (existing) {
      if (input.expectedVersion !== undefined && existing.version !== input.expectedVersion) {
        throw APIError.aborted("Stale expectedVersion for project workflow binding");
      }

      const nextVersion = existing.version + 1;
      await tx
        .update(projectWorkflowBindings)
        .set({
          workflowAssetVersion: input.workflowAssetVersion,
          workflowDefinitionHash: input.workflowDefinitionHash,
          executionPolicy: input.executionPolicy ?? existing.executionPolicy,
          state: "ACTIVE",
          version: nextVersion,
          updatedAt: new Date(),
        })
        .where(eq(projectWorkflowBindings.id, existing.id));

      const eventId = generateSnowflake();
      await tx.insert(founderAssetEvents).values({
        id: eventId,
        workspaceId: wsId,
        projectId: projId,
        actorId,
        command: "updateProjectWorkflowBinding",
        targetKind: "WORKFLOW",
        targetRef: { bindingId: existing.id.toString(), workflowAssetId: input.workflowAssetId },
        afterHash: input.workflowDefinitionHash,
        reason: input.reason,
        correlationId: ctx.correlationId || generateSnowflake().toString(),
        metadata: { idempotencyKey: input.idempotencyKey },
      });

      return {
        id: existing.id.toString(),
        workspaceId: wsId.toString(),
        projectId: projId.toString(),
        workflowAssetId: input.workflowAssetId,
        workflowAssetVersion: input.workflowAssetVersion,
        workflowDefinitionHash: input.workflowDefinitionHash,
        state: "ACTIVE",
        executionPolicy: (input.executionPolicy ?? existing.executionPolicy) as Record<string, any>,
        version: nextVersion,
      };
    }

    const bindingId = generateSnowflake();
    await tx.insert(projectWorkflowBindings).values({
      id: bindingId,
      workspaceId: wsId,
      projectId: projId,
      workflowAssetId: input.workflowAssetId,
      workflowAssetVersion: input.workflowAssetVersion,
      workflowDefinitionHash: input.workflowDefinitionHash,
      state: "ACTIVE",
      executionPolicy: input.executionPolicy ?? {},
      version: 1,
      createdBy: actorId,
    });

    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      projectId: projId,
      actorId,
      command: "bindWorkflowToProject",
      targetKind: "WORKFLOW",
      targetRef: { bindingId: bindingId.toString(), workflowAssetId: input.workflowAssetId },
      afterHash: input.workflowDefinitionHash,
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: bindingId.toString(),
      workspaceId: wsId.toString(),
      projectId: projId.toString(),
      workflowAssetId: input.workflowAssetId,
      workflowAssetVersion: input.workflowAssetVersion,
      workflowDefinitionHash: input.workflowDefinitionHash,
      state: "ACTIVE",
      executionPolicy: input.executionPolicy ?? {},
      version: 1,
    };
  });
}

export async function pauseProjectDeployment(
  ctx: TenantContext,
  input: {
    deploymentId: string;
    kind: "ROLE" | "AGENT" | "WORKFLOW";
    expectedVersion: number;
    reason: string;
    idempotencyKey?: string;
  }
): Promise<{ id: string; state: "PAUSED"; version: number }> {
  assertHumanFounder(ctx, "pauseProjectDeployment");
  const wsId = BigInt(ctx.workspaceId);
  const depId = BigInt(input.deploymentId);
  const actorId = BigInt(ctx.userId);

  return db.transaction(async (tx) => {
    let currentVersion: number;
    let projId: bigint;

    if (input.kind === "ROLE") {
      const [roleDep] = await tx
        .select()
        .from(projectRoleDeployments)
        .where(and(eq(projectRoleDeployments.id, depId), eq(projectRoleDeployments.workspaceId, wsId)))
        .limit(1);

      if (!roleDep) {
        throw APIError.notFound("Project role deployment not found");
      }
      currentVersion = roleDep.version;
      projId = roleDep.projectId;

      if (currentVersion !== input.expectedVersion) {
        throw APIError.aborted(`Stale expectedVersion for project role deployment (current=${currentVersion}, expected=${input.expectedVersion})`);
      }

      await tx
        .update(projectRoleDeployments)
        .set({ state: "PAUSED", version: currentVersion + 1, updatedAt: new Date() })
        .where(eq(projectRoleDeployments.id, depId));
    } else if (input.kind === "AGENT") {
      const [agentDep] = await tx
        .select()
        .from(projectAgentDeployments)
        .where(and(eq(projectAgentDeployments.id, depId), eq(projectAgentDeployments.workspaceId, wsId)))
        .limit(1);

      if (!agentDep) {
        throw APIError.notFound("Project agent deployment not found");
      }
      currentVersion = agentDep.version;
      projId = agentDep.projectId;

      if (currentVersion !== input.expectedVersion) {
        throw APIError.aborted(`Stale expectedVersion for project agent deployment (current=${currentVersion}, expected=${input.expectedVersion})`);
      }

      await tx
        .update(projectAgentDeployments)
        .set({ state: "PAUSED", version: currentVersion + 1, updatedAt: new Date() })
        .where(eq(projectAgentDeployments.id, depId));
    } else {
      const [wfBinding] = await tx
        .select()
        .from(projectWorkflowBindings)
        .where(and(eq(projectWorkflowBindings.id, depId), eq(projectWorkflowBindings.workspaceId, wsId)))
        .limit(1);

      if (!wfBinding) {
        throw APIError.notFound("Project workflow binding not found");
      }
      currentVersion = wfBinding.version;
      projId = wfBinding.projectId;

      if (currentVersion !== input.expectedVersion) {
        throw APIError.aborted(`Stale expectedVersion for project workflow binding (current=${currentVersion}, expected=${input.expectedVersion})`);
      }

      await tx
        .update(projectWorkflowBindings)
        .set({ state: "PAUSED", version: currentVersion + 1, updatedAt: new Date() })
        .where(eq(projectWorkflowBindings.id, depId));
    }

    const nextVersion = currentVersion + 1;
    const eventId = generateSnowflake();
    await tx.insert(founderAssetEvents).values({
      id: eventId,
      workspaceId: wsId,
      projectId: projId,
      actorId,
      command: "pauseProjectDeployment",
      targetKind: "DEPLOYMENT",
      targetRef: { deploymentId: input.deploymentId, kind: input.kind },
      reason: input.reason,
      correlationId: ctx.correlationId || generateSnowflake().toString(),
      metadata: { idempotencyKey: input.idempotencyKey },
    });

    return {
      id: input.deploymentId,
      state: "PAUSED",
      version: nextVersion,
    };
  });
}

export async function getProjectDeploymentAuthority(
  ctx: TenantContext,
  input: {
    projectId: string;
    workspaceAgentId?: string;
    projectAgentDeploymentId?: string;
  }
): Promise<ProjectDeploymentAuthority> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(input.projectId);
  if (!input.workspaceAgentId && !input.projectAgentDeploymentId) {
    throw APIError.invalidArgument("workspaceAgentId or projectAgentDeploymentId is required");
  }
  if (input.workspaceAgentId && input.projectAgentDeploymentId) {
    throw APIError.invalidArgument("Provide exactly one deployment authority identifier");
  }
  const agentId = input.workspaceAgentId ? BigInt(input.workspaceAgentId) : null;
  const deploymentId = input.projectAgentDeploymentId ? BigInt(input.projectAgentDeploymentId) : null;

  await validateProjectInWorkspace(wsId, projId);

  const [deployment] = await db
    .select({
      deploymentId: projectAgentDeployments.id,
      state: projectAgentDeployments.state,
      capabilityOverrides: projectAgentDeployments.capabilityOverrides,
      workspaceAgentId: workspaceAgents.id,
      workforceMemberId: workspaceAgents.workforceMemberId,
      agentAssetId: workspaceAgents.agentAssetId,
      agentAssetVersion: workspaceAgents.agentAssetVersion,
      agentDefinitionHash: workspaceAgents.agentDefinitionHash,
      agentState: workspaceAgents.state,
    })
    .from(projectAgentDeployments)
    .innerJoin(
      workspaceAgents,
      and(
        eq(workspaceAgents.id, projectAgentDeployments.workspaceAgentId),
        eq(workspaceAgents.workspaceId, wsId)
      )
    )
    .where(
      and(
        eq(projectAgentDeployments.workspaceId, wsId),
        eq(projectAgentDeployments.projectId, projId),
        deploymentId
          ? eq(projectAgentDeployments.id, deploymentId)
          : eq(projectAgentDeployments.workspaceAgentId, agentId!)
      )
    )
    .limit(1);

  if (!deployment) {
    throw APIError.notFound("Project agent deployment not found");
  }

  // Lấy các role IDs mà agent này thuộc về trong project này
  const roleRows = await db
    .select({ roleId: projectRoleDeployments.roleId })
    .from(projectRoleDeployments)
    .innerJoin(
      roleAgentBindings,
      and(
        eq(roleAgentBindings.roleId, projectRoleDeployments.roleId),
        eq(roleAgentBindings.workspaceAgentId, deployment.workspaceAgentId),
        eq(roleAgentBindings.workspaceId, wsId)
      )
    )
    .where(
      and(
        eq(projectRoleDeployments.workspaceId, wsId),
        eq(projectRoleDeployments.projectId, projId)
      )
    );

  const effectiveState =
    deployment.agentState === "RETIRED" || deployment.state === "RETIRED"
      ? "RETIRED"
      : deployment.state === "PAUSED"
      ? "PAUSED"
      : "ACTIVE";

  return {
    workspaceId: ctx.workspaceId,
    projectAgentDeploymentId: deployment.deploymentId.toString(),
    workspaceAgentId: deployment.workspaceAgentId.toString(),
    workforceMemberId: deployment.workforceMemberId.toString(),
    agentSpec: {
      id: deployment.agentAssetId,
      version: deployment.agentAssetVersion,
      definitionHash: deployment.agentDefinitionHash,
    },
    roleIds: roleRows.map((r) => r.roleId.toString()),
    projectId: input.projectId,
    state: effectiveState,
    capabilityRestrictions: (deployment.capabilityOverrides as any[]) ?? [],
  };
}
