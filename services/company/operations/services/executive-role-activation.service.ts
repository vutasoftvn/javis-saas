import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  EXECUTIVE_ROLE_CATALOG,
  STARTUP_CORE_PRESETS,
  ExecutiveRoleKey,
  StartupCorePresetKey,
  isExecutiveRoleKey,
  isStartupCorePresetKey,
} from "../../shared/contracts/executive-advisor-roles.generated";
import { verifyUnderlyingAgentActive } from "./founder-agent-compatibility.service";

const {
  projects,
  projectAgentAssignments,
  projectExecutiveBoardSettings,
  projectExecutiveRoleActivations,
  projectExecutiveRoleActivationEvents,
} = schema;

export type ExecutiveRoleDisplayState =
  | "UNAVAILABLE"
  | "AVAILABLE_NOT_ACTIVATED"
  | "ACTIVE"
  | "DISABLED";

export interface ProjectExecutiveRoleState {
  roleKey: ExecutiveRoleKey;
  label: string;
  advisoryRemit: string;
  displayState: ExecutiveRoleDisplayState;
  runtimeReadiness: string;
  requiredProfileKey: string;
  activationSource?: string;
  version: number;
  activatedAt?: string;
  actorId?: string;
  disabledReason?: string;
}

export interface ProjectExecutiveBoardState {
  projectId: string;
  settings?: {
    presetKey: StartupCorePresetKey;
    version: number;
    selectedBy: string;
    updatedAt: string;
  };
  roles: ProjectExecutiveRoleState[];
}

export interface SelectPresetInput {
  presetKey: StartupCorePresetKey;
  expectedVersion?: number;
  idempotencyKey?: string;
}

export interface RoleActivationOptions {
  expectedVersion?: number;
  idempotencyKey?: string;
}

export interface RoleDisableOptions {
  expectedVersion?: number;
  reason?: string;
  idempotencyKey?: string;
}

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
 * Lấy trạng thái hiển thị trung thực của toàn bộ Executive Roles theo Project.
 */
export async function getProjectExecutiveRoleStates(
  ctx: TenantContext,
  projectId: string
): Promise<ProjectExecutiveBoardState> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  // 1. Verify Project belongs to Workspace
  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }

  // 2. Fetch current settings
  const [settingsRow] = await db
    .select()
    .from(projectExecutiveBoardSettings)
    .where(
      and(
        eq(projectExecutiveBoardSettings.workspaceId, wsId),
        eq(projectExecutiveBoardSettings.projectId, projId)
      )
    )
    .limit(1);

  // 3. Fetch active startup team assignments
  const assignments = await db
    .select({
      profileKey: projectAgentAssignments.profileKey,
      state: projectAgentAssignments.state,
      specHash: projectAgentAssignments.specHash,
    })
    .from(projectAgentAssignments)
    .where(
      and(
        eq(projectAgentAssignments.workspaceId, wsId),
        eq(projectAgentAssignments.projectId, projId)
      )
    );

  const activeProfiles = new Set(
    assignments
      .filter((a) => a.state === "ACTIVE" && Boolean(a.specHash))
      .map((a) => a.profileKey)
  );

  // 4. Fetch existing executive role activations
  const activations = await db
    .select()
    .from(projectExecutiveRoleActivations)
    .where(
      and(
        eq(projectExecutiveRoleActivations.workspaceId, wsId),
        eq(projectExecutiveRoleActivations.projectId, projId)
      )
    );

  const activationMap = new Map(activations.map((a) => [a.roleKey, a]));

  // 5. Build role states
  const roleStates: ProjectExecutiveRoleState[] = Object.values(EXECUTIVE_ROLE_CATALOG).map(
    (roleDef) => {
      const isProfileEligible =
        roleDef.runtimeReadiness === "READY" &&
        activeProfiles.has(roleDef.requiredProfileKey);

      const existingAct = activationMap.get(roleDef.key);

      let displayState: ExecutiveRoleDisplayState = "UNAVAILABLE";
      let version = 1;
      let activationSource: string | undefined;
      let activatedAt: string | undefined;
      let actorId: string | undefined;
      let disabledReason: string | undefined;

      if (existingAct) {
        version = existingAct.version;
        activationSource = existingAct.activationSource;
        actorId = existingAct.actorId.toString();

        if (existingAct.state === "ACTIVE") {
          // If underlying assignment is no longer active, truth in display is UNAVAILABLE
          displayState = isProfileEligible ? "ACTIVE" : "UNAVAILABLE";
          if (!isProfileEligible) {
            disabledReason = "UNDERLYING_PROFILE_UNAVAILABLE";
          }
          activatedAt = existingAct.updatedAt.toISOString();
        } else if (existingAct.state === "DISABLED") {
          displayState = "DISABLED";
        }
      } else {
        displayState = isProfileEligible ? "AVAILABLE_NOT_ACTIVATED" : "UNAVAILABLE";
        if (!isProfileEligible) {
          disabledReason = "UNDERLYING_PROFILE_UNAVAILABLE";
        }
      }

      return {
        roleKey: roleDef.key,
        label: roleDef.label,
        advisoryRemit: roleDef.advisoryRemit,
        displayState,
        runtimeReadiness: roleDef.runtimeReadiness,
        requiredProfileKey: roleDef.requiredProfileKey,
        activationSource,
        version,
        activatedAt,
        actorId,
        disabledReason,
      };
    }
  );

  return {
    projectId,
    settings: settingsRow
      ? {
          presetKey: settingsRow.presetKey as StartupCorePresetKey,
          version: settingsRow.version,
          selectedBy: settingsRow.selectedBy.toString(),
          updatedAt: settingsRow.updatedAt.toISOString(),
        }
      : undefined,
    roles: roleStates,
  };
}

/**
 * Founder chọn Startup Core preset cho Project.
 * Chỉ kích hoạt các role default đủ điều kiện (underlying assignment đang ACTIVE).
 */
export async function selectStartupCorePreset(
  ctx: TenantContext,
  projectId: string,
  input: SelectPresetInput
): Promise<{ presetKey: StartupCorePresetKey; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  if (!isStartupCorePresetKey(input.presetKey)) {
    throw APIError.invalidArgument(`Invalid presetKey: ${input.presetKey}`);
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const actorId = BigInt(ctx.userId);
  const preset = STARTUP_CORE_PRESETS[input.presetKey];

  return await db.transaction(async (tx) => {
    // 1. Check existing settings
    const [existingSettings] = await tx
      .select()
      .from(projectExecutiveBoardSettings)
      .where(
        and(
          eq(projectExecutiveBoardSettings.workspaceId, wsId),
          eq(projectExecutiveBoardSettings.projectId, projId)
        )
      )
      .limit(1);

    if (
      existingSettings &&
      input.expectedVersion !== undefined &&
      existingSettings.version !== input.expectedVersion
    ) {
      throw APIError.aborted(
        `CAS_CONFLICT: Stale settings version (expected ${input.expectedVersion}, got ${existingSettings.version})`
      );
    }

    const nextSettingsVersion = existingSettings ? existingSettings.version + 1 : 1;

    if (existingSettings) {
      await tx
        .update(projectExecutiveBoardSettings)
        .set({
          presetKey: input.presetKey,
          version: nextSettingsVersion,
          selectedBy: actorId,
          updatedAt: new Date(),
        })
        .where(
          and(
            eq(projectExecutiveBoardSettings.workspaceId, wsId),
            eq(projectExecutiveBoardSettings.projectId, projId)
          )
        );
    } else {
      await tx.insert(projectExecutiveBoardSettings).values({
        workspaceId: wsId,
        projectId: projId,
        presetKey: input.presetKey,
        version: nextSettingsVersion,
        selectedBy: actorId,
      });
    }

    // 2. Fetch active assignments in startup team
    const assignments = await tx
      .select({
        profileKey: projectAgentAssignments.profileKey,
        state: projectAgentAssignments.state,
        specHash: projectAgentAssignments.specHash,
      })
      .from(projectAgentAssignments)
      .where(
        and(
          eq(projectAgentAssignments.workspaceId, wsId),
          eq(projectAgentAssignments.projectId, projId)
        )
      );

    const activeProfiles = new Set(
      assignments
        .filter((a) => a.state === "ACTIVE" && Boolean(a.specHash))
        .map((a) => a.profileKey)
    );

    // 3. Activate eligible default roles
    for (const roleKey of preset.defaultRoleKeys) {
      const roleDef = EXECUTIVE_ROLE_CATALOG[roleKey];
      if (
        roleDef &&
        roleDef.runtimeReadiness === "READY" &&
        activeProfiles.has(roleDef.requiredProfileKey)
      ) {
        const [existingAct] = await tx
          .select()
          .from(projectExecutiveRoleActivations)
          .where(
            and(
              eq(projectExecutiveRoleActivations.workspaceId, wsId),
              eq(projectExecutiveRoleActivations.projectId, projId),
              eq(projectExecutiveRoleActivations.roleKey, roleKey)
            )
          )
          .limit(1);

        if (!existingAct) {
          const actId = generateSnowflake();
          await tx.insert(projectExecutiveRoleActivations).values({
            id: actId,
            workspaceId: wsId,
            projectId: projId,
            roleKey,
            state: "ACTIVE",
            activationSource: "STARTUP_CORE_PRESET",
            version: 1,
            actorId,
          });

          await tx.insert(projectExecutiveRoleActivationEvents).values({
            id: generateSnowflake(),
            workspaceId: wsId,
            projectId: projId,
            roleKey,
            activationId: actId,
            fromState: null,
            toState: "ACTIVE",
            actorId,
            version: 1,
            payload: {
              source: "STARTUP_CORE_PRESET",
              presetKey: input.presetKey,
              idempotencyKey: input.idempotencyKey,
            },
          });
        } else if (existingAct.state !== "ACTIVE") {
          const nextVersion = existingAct.version + 1;
          await tx
            .update(projectExecutiveRoleActivations)
            .set({
              state: "ACTIVE",
              activationSource: "STARTUP_CORE_PRESET",
              version: nextVersion,
              actorId,
              updatedAt: new Date(),
            })
            .where(eq(projectExecutiveRoleActivations.id, existingAct.id));

          await tx.insert(projectExecutiveRoleActivationEvents).values({
            id: generateSnowflake(),
            workspaceId: wsId,
            projectId: projId,
            roleKey,
            activationId: existingAct.id,
            fromState: existingAct.state,
            toState: "ACTIVE",
            actorId,
            version: nextVersion,
            payload: {
              source: "STARTUP_CORE_PRESET",
              presetKey: input.presetKey,
              idempotencyKey: input.idempotencyKey,
            },
          });
        }
      }
    }

    return {
      presetKey: input.presetKey,
      version: nextSettingsVersion,
    };
  });
}

/**
 * Founder kích hoạt một Executive Role theo Project.
 * Bắt buộc profile nền phải ACTIVE và có spec pin.
 */
export async function activateExecutiveRole(
  ctx: TenantContext,
  projectId: string,
  roleKey: string,
  opts?: RoleActivationOptions
): Promise<{ id: string; roleKey: string; state: string; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  if (!isExecutiveRoleKey(roleKey)) {
    throw APIError.invalidArgument(`Invalid roleKey: ${roleKey}`);
  }

  const roleDef = EXECUTIVE_ROLE_CATALOG[roleKey];
  if (roleDef.runtimeReadiness !== "READY") {
    throw APIError.failedPrecondition(
      `EXECUTIVE_ROLE_NOT_AVAILABLE: Role ${roleKey} has readiness ${roleDef.runtimeReadiness}`
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const actorId = BigInt(ctx.userId);

  // Verify underlying profile assignment or V2 deployment is ACTIVE
  const isUnderlyingActive = await verifyUnderlyingAgentActive(
    ctx.workspaceId,
    projectId,
    roleDef.requiredProfileKey
  );

  if (!isUnderlyingActive) {
    throw APIError.failedPrecondition(
      `EXECUTIVE_ROLE_NOT_AVAILABLE: Required profile ${roleDef.requiredProfileKey} is not active in startup team`
    );
  }

  return await db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(projectExecutiveRoleActivations)
      .where(
        and(
          eq(projectExecutiveRoleActivations.workspaceId, wsId),
          eq(projectExecutiveRoleActivations.projectId, projId),
          eq(projectExecutiveRoleActivations.roleKey, roleKey)
        )
      )
      .limit(1);

    if (existing) {
      // Check CAS
      if (
        opts?.expectedVersion !== undefined &&
        existing.version !== opts.expectedVersion
      ) {
        throw APIError.aborted(
          `CAS_CONFLICT: Stale executive role version (expected ${opts.expectedVersion}, got ${existing.version})`
        );
      }

      if (existing.state === "ACTIVE") {
        return {
          id: existing.id.toString(),
          roleKey: existing.roleKey,
          state: existing.state,
          version: existing.version,
        };
      }

      const nextVersion = existing.version + 1;
      await tx
        .update(projectExecutiveRoleActivations)
        .set({
          state: "ACTIVE",
          activationSource: "FOUNDER",
          version: nextVersion,
          actorId,
          updatedAt: new Date(),
        })
        .where(eq(projectExecutiveRoleActivations.id, existing.id));

      await tx.insert(projectExecutiveRoleActivationEvents).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: projId,
        roleKey,
        activationId: existing.id,
        fromState: existing.state,
        toState: "ACTIVE",
        actorId,
        version: nextVersion,
        payload: { source: "FOUNDER", idempotencyKey: opts?.idempotencyKey },
      });

      return {
        id: existing.id.toString(),
        roleKey,
        state: "ACTIVE",
        version: nextVersion,
      };
    } else {
      // Creating new activation row
      if (
        opts?.expectedVersion !== undefined &&
        opts.expectedVersion > 1
      ) {
        throw APIError.aborted(
          `CAS_CONFLICT: Stale executive role version (expected ${opts.expectedVersion}, got 1)`
        );
      }

      const actId = generateSnowflake();
      await tx.insert(projectExecutiveRoleActivations).values({
        id: actId,
        workspaceId: wsId,
        projectId: projId,
        roleKey,
        state: "ACTIVE",
        activationSource: "FOUNDER",
        version: 1,
        actorId,
      });

      await tx.insert(projectExecutiveRoleActivationEvents).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: projId,
        roleKey,
        activationId: actId,
        fromState: null,
        toState: "ACTIVE",
        actorId,
        version: 1,
        payload: { source: "FOUNDER", idempotencyKey: opts?.idempotencyKey },
      });

      return {
        id: actId.toString(),
        roleKey,
        state: "ACTIVE",
        version: 1,
      };
    }
  });
}

/**
 * Founder vô hiệu hoá một Executive Role đang hoạt động.
 * Lưu lại lịch sử và đổi state sang DISABLED.
 */
export async function disableExecutiveRole(
  ctx: TenantContext,
  projectId: string,
  roleKey: string,
  opts?: RoleDisableOptions
): Promise<{ id: string; roleKey: string; state: string; version: number }> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId);

  if (!isExecutiveRoleKey(roleKey)) {
    throw APIError.invalidArgument(`Invalid roleKey: ${roleKey}`);
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const actorId = BigInt(ctx.userId);

  return await db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(projectExecutiveRoleActivations)
      .where(
        and(
          eq(projectExecutiveRoleActivations.workspaceId, wsId),
          eq(projectExecutiveRoleActivations.projectId, projId),
          eq(projectExecutiveRoleActivations.roleKey, roleKey)
        )
      )
      .limit(1);

    if (!existing) {
      throw APIError.notFound(`Executive role activation for ${roleKey} not found`);
    }

    if (
      opts?.expectedVersion !== undefined &&
      existing.version !== opts.expectedVersion
    ) {
      throw APIError.aborted(
        `CAS_CONFLICT: Stale executive role version (expected ${opts.expectedVersion}, got ${existing.version})`
      );
    }

    if (existing.state === "DISABLED") {
      return {
        id: existing.id.toString(),
        roleKey: existing.roleKey,
        state: existing.state,
        version: existing.version,
      };
    }

    const nextVersion = existing.version + 1;
    await tx
      .update(projectExecutiveRoleActivations)
      .set({
        state: "DISABLED",
        version: nextVersion,
        actorId,
        updatedAt: new Date(),
      })
      .where(eq(projectExecutiveRoleActivations.id, existing.id));

    await tx.insert(projectExecutiveRoleActivationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: projId,
      roleKey,
      activationId: existing.id,
      fromState: existing.state,
      toState: "DISABLED",
      actorId,
      version: nextVersion,
      payload: {
        reason: opts?.reason,
        idempotencyKey: opts?.idempotencyKey,
      },
    });

    return {
      id: existing.id.toString(),
      roleKey,
      state: "DISABLED",
      version: nextVersion,
    };
  });
}
