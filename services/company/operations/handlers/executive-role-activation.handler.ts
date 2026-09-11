import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getProjectExecutiveRoleStates,
  selectStartupCorePreset,
  activateExecutiveRole,
  disableExecutiveRole,
  ProjectExecutiveBoardState,
} from "../services/executive-role-activation.service";
import {
  StartupCorePresetKey,
} from "../../shared/contracts/executive-advisor-roles.generated";

interface ListProjectExecutiveRolesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export const listProjectExecutiveRolesApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/executive-roles",
  },
  async (
    params: ListProjectExecutiveRolesParams
  ): Promise<ProjectExecutiveBoardState> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await getProjectExecutiveRoleStates(ctx, params.projectId);
  }
);

interface SelectProjectExecutivePresetParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  presetKey: StartupCorePresetKey;
  expectedVersion?: number;
  idempotencyKey?: string;
}

export const selectProjectExecutivePresetApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-preset",
  },
  async (
    params: SelectProjectExecutivePresetParams
  ): Promise<{ presetKey: StartupCorePresetKey; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await selectStartupCorePreset(ctx, params.projectId, {
      presetKey: params.presetKey,
      expectedVersion: params.expectedVersion,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

interface ActivateProjectExecutiveRoleParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  roleKey: string;
  expectedVersion?: number;
  idempotencyKey?: string;
}

export const activateProjectExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-roles/:roleKey/activate",
  },
  async (
    params: ActivateProjectExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await activateExecutiveRole(ctx, params.projectId, params.roleKey, {
      expectedVersion: params.expectedVersion,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

interface DisableProjectExecutiveRoleParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  roleKey: string;
  expectedVersion?: number;
  reason?: string;
  idempotencyKey?: string;
}

export const disableProjectExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-roles/:roleKey/disable",
  },
  async (
    params: DisableProjectExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await disableExecutiveRole(ctx, params.projectId, params.roleKey, {
      expectedVersion: params.expectedVersion,
      reason: params.reason,
      idempotencyKey: params.idempotencyKey,
    });
  }
);
