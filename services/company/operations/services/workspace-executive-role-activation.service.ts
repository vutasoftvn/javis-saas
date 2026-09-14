import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  EXECUTIVE_ROLE_CATALOG,
  ExecutiveRoleKey,
  isExecutiveRoleKey,
} from "../../shared/contracts/executive-advisor-roles.generated";
import { verifyUnderlyingAgentActive } from "./founder-agent-compatibility.service";
import { requireExecutiveBoardFounderAuthorityForWorkspace } from "./executive-role-activation.service";

const {
  projects,
  workspaceExecutiveRoleActivations,
  workspaceExecutiveRoleActivationEvents,
} = schema;

export type ExecutiveRoleDisplayState =
  | "UNAVAILABLE"
  | "AVAILABLE_NOT_ACTIVATED"
  | "ACTIVE"
  | "DISABLED";

export interface WorkspaceExecutiveRoleState {
  roleKey: ExecutiveRoleKey;
  label: string;
  advisoryRemit: string;
  displayState: ExecutiveRoleDisplayState;
  runtimeReadiness: string;
  requiredProfileKey: string;
  version: number;
  activatedAt?: string;
  actorId?: string;
  disabledReason?: string;
}

export interface WorkspaceExecutiveBoardState {
  workspaceId: string;
  roles: WorkspaceExecutiveRoleState[];
}

export interface WorkspaceRoleActivationOptions {
  expectedVersion?: number;
  idempotencyKey?: string;
}

export interface WorkspaceRoleDisableOptions {
  expectedVersion?: number;
  reason?: string;
  idempotencyKey?: string;
}

/**
 * Tập `requiredProfileKey` có agent nền đang ACTIVE ở ÍT NHẤT 1 Project của
 * workspace (quyết định 2026-09-14 — gate UNAVAILABLE được giữ nhưng định
 * nghĩa lại thành aggregate OR trên toàn workspace, vì activation giờ dùng
 * chung cho mọi Project chứ không còn gắn 1 Project cụ thể).
 *
 * N+1 query có chủ đích: quy mô MVP hiện tại (ít Project/workspace) chưa cần
 * batch hoá, và `verifyUnderlyingAgentActive` là nguồn sự thật duy nhất cho
 * "agent nền có thật sự chạy không" — không nhân bản logic đó ở đây.
 */
async function resolveAvailableProfileKeys(ctx: TenantContext): Promise<Set<string>> {
  const wsId = BigInt(ctx.workspaceId);

  const workspaceProjects = await db
    .select({ id: projects.id })
    .from(projects)
    .where(eq(projects.workspaceId, wsId));

  const requiredProfileKeys = new Set(
    Object.values(EXECUTIVE_ROLE_CATALOG).map((def) => def.requiredProfileKey)
  );

  const available = new Set<string>();
  for (const profileKey of requiredProfileKeys) {
    for (const project of workspaceProjects) {
      const isActive = await verifyUnderlyingAgentActive(
        ctx.workspaceId,
        project.id.toString(),
        profileKey
      );
      if (isActive) {
        available.add(profileKey);
        break; // Chỉ cần 1 Project thoả — không cần quét tiếp.
      }
    }
  }

  return available;
}

/**
 * Đọc trạng thái cả 13 role Executive Board — activation cấp Workspace,
 * chia sẻ cho mọi Project trong cùng workspace (xem spec mục 6, 2026-09-14).
 * Luôn trả đủ 13 role kể cả khi chưa có activation nào.
 */
export async function getWorkspaceExecutiveRoleStates(
  ctx: TenantContext
): Promise<WorkspaceExecutiveBoardState> {
  const wsId = BigInt(ctx.workspaceId);

  const activations = await db
    .select()
    .from(workspaceExecutiveRoleActivations)
    .where(eq(workspaceExecutiveRoleActivations.workspaceId, wsId));

  const activationByRole = new Map(activations.map((a) => [a.roleKey, a]));
  const availableProfiles = await resolveAvailableProfileKeys(ctx);

  const roles: WorkspaceExecutiveRoleState[] = Object.values(EXECUTIVE_ROLE_CATALOG).map(
    (roleDef) => {
      const isProfileEligible =
        roleDef.runtimeReadiness === "READY" &&
        availableProfiles.has(roleDef.requiredProfileKey);

      const activation = activationByRole.get(roleDef.key);

      let displayState: ExecutiveRoleDisplayState = "UNAVAILABLE";
      let version = 1;
      let activatedAt: string | undefined;
      let actorId: string | undefined;
      let disabledReason: string | undefined;

      if (activation) {
        version = activation.version;
        actorId = activation.actorId.toString();

        if (activation.state === "ACTIVE") {
          // Trung thực trong hiển thị: nếu agent nền không còn chạy ở bất kỳ
          // Project nào thì role không thể coi là ACTIVE dù DB ghi ACTIVE.
          displayState = isProfileEligible ? "ACTIVE" : "UNAVAILABLE";
          if (!isProfileEligible) {
            disabledReason = "UNDERLYING_PROFILE_UNAVAILABLE";
          }
          activatedAt = activation.updatedAt.toISOString();
        } else {
          displayState = "DISABLED";
          disabledReason = activation.disabledReason ?? undefined;
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
        version,
        activatedAt,
        actorId,
        disabledReason,
      };
    }
  );

  return { workspaceId: wsId.toString(), roles };
}

/**
 * Founder kích hoạt một Executive Role cho cả Workspace.
 * KHÔNG bao giờ tự động chạy — chỉ khi con người có quyền Founder gọi tới
 * (CLAUDE.md quy tắc #5: governance là code xác định, không tự động).
 */
export async function activateWorkspaceExecutiveRole(
  ctx: TenantContext,
  roleKey: string,
  opts?: WorkspaceRoleActivationOptions
): Promise<{ id: string; roleKey: string; state: string; version: number }> {
  await requireExecutiveBoardFounderAuthorityForWorkspace(ctx);

  if (!isExecutiveRoleKey(roleKey)) {
    throw APIError.invalidArgument(`Invalid roleKey: ${roleKey}`);
  }

  const roleDef = EXECUTIVE_ROLE_CATALOG[roleKey];
  if (roleDef.runtimeReadiness !== "READY") {
    throw APIError.failedPrecondition(
      `EXECUTIVE_ROLE_NOT_AVAILABLE: Role ${roleKey} has readiness ${roleDef.runtimeReadiness}`
    );
  }

  const availableProfiles = await resolveAvailableProfileKeys(ctx);
  if (!availableProfiles.has(roleDef.requiredProfileKey)) {
    throw APIError.failedPrecondition(
      `EXECUTIVE_ROLE_NOT_AVAILABLE: Required profile ${roleDef.requiredProfileKey} is not active in any project of this workspace`
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.userId);

  return await db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(workspaceExecutiveRoleActivations)
      .where(
        and(
          eq(workspaceExecutiveRoleActivations.workspaceId, wsId),
          eq(workspaceExecutiveRoleActivations.roleKey, roleKey)
        )
      )
      .limit(1);

    if (existing) {
      if (opts?.expectedVersion !== undefined && existing.version !== opts.expectedVersion) {
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
        .update(workspaceExecutiveRoleActivations)
        .set({
          state: "ACTIVE",
          version: nextVersion,
          actorId,
          // Xoá lý do disable cũ để không rò rỉ sang lần bật lại này.
          disabledReason: null,
          updatedAt: new Date(),
        })
        .where(eq(workspaceExecutiveRoleActivations.id, existing.id));

      await tx.insert(workspaceExecutiveRoleActivationEvents).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        roleKey,
        activationId: existing.id,
        fromState: existing.state,
        toState: "ACTIVE",
        actorId,
        version: nextVersion,
        payload: { source: "FOUNDER", idempotencyKey: opts?.idempotencyKey ?? null },
      });

      return {
        id: existing.id.toString(),
        roleKey,
        state: "ACTIVE",
        version: nextVersion,
      };
    }

    // Lần activate đầu tiên: chưa có row nào. Board luôn báo version 1 cho role
    // chưa activate, nên caller đúng đắn chỉ có thể gửi 1 — khớp CHÍNH XÁC cho
    // đối xứng với nhánh update ở trên, thay vì chỉ chặn > 1 (giá trị 0 hay số
    // âm là dấu hiệu caller đang cầm state sai, không nên im lặng chấp nhận).
    if (opts?.expectedVersion !== undefined && opts.expectedVersion !== 1) {
      throw APIError.aborted(
        `CAS_CONFLICT: Stale executive role version (expected ${opts.expectedVersion}, got 1)`
      );
    }

    const actId = generateSnowflake();
    await tx.insert(workspaceExecutiveRoleActivations).values({
      id: actId,
      workspaceId: wsId,
      roleKey,
      state: "ACTIVE",
      version: 1,
      actorId,
    });

    await tx.insert(workspaceExecutiveRoleActivationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      roleKey,
      activationId: actId,
      fromState: null,
      toState: "ACTIVE",
      actorId,
      version: 1,
      payload: { source: "FOUNDER", idempotencyKey: opts?.idempotencyKey ?? null },
    });

    return { id: actId.toString(), roleKey, state: "ACTIVE", version: 1 };
  });
}

/**
 * Founder vô hiệu hoá một Executive Role ở phạm vi Workspace.
 * Giữ lại row + lịch sử append-only, chỉ đổi state sang DISABLED.
 */
export async function disableWorkspaceExecutiveRole(
  ctx: TenantContext,
  roleKey: string,
  opts?: WorkspaceRoleDisableOptions
): Promise<{ id: string; roleKey: string; state: string; version: number }> {
  await requireExecutiveBoardFounderAuthorityForWorkspace(ctx);

  if (!isExecutiveRoleKey(roleKey)) {
    throw APIError.invalidArgument(`Invalid roleKey: ${roleKey}`);
  }

  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.userId);

  return await db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(workspaceExecutiveRoleActivations)
      .where(
        and(
          eq(workspaceExecutiveRoleActivations.workspaceId, wsId),
          eq(workspaceExecutiveRoleActivations.roleKey, roleKey)
        )
      )
      .limit(1);

    if (!existing) {
      throw APIError.failedPrecondition(
        `Role ${roleKey} was never activated for this workspace`
      );
    }

    if (opts?.expectedVersion !== undefined && existing.version !== opts.expectedVersion) {
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
      .update(workspaceExecutiveRoleActivations)
      .set({
        state: "DISABLED",
        version: nextVersion,
        actorId,
        disabledReason: opts?.reason ?? null,
        updatedAt: new Date(),
      })
      .where(eq(workspaceExecutiveRoleActivations.id, existing.id));

    await tx.insert(workspaceExecutiveRoleActivationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      roleKey,
      activationId: existing.id,
      fromState: existing.state,
      toState: "DISABLED",
      actorId,
      version: nextVersion,
      payload: { reason: opts?.reason ?? null, idempotencyKey: opts?.idempotencyKey ?? null },
    });

    return { id: existing.id.toString(), roleKey, state: "DISABLED", version: nextVersion };
  });
}
