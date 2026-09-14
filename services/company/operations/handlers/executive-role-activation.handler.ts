import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getProjectExecutiveRoleStates,
  getStageSuggestion,
  ProjectExecutiveBoardState,
  StageSuggestion,
} from "../services/executive-role-activation.service";
import {
  activateWorkspaceExecutiveRole,
  disableWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";
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

/**
 * DEPRECATED 2026-09-14. Startup Core preset không còn điều khiển Executive
 * Board — activation là hành động tường minh cấp Workspace. Endpoint được GIỮ
 * (không xoá) để client cũ nhận lỗi hướng dẫn rõ ràng thay vì 404 mù.
 */
export const selectProjectExecutivePresetApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-preset",
  },
  async (
    _params: SelectProjectExecutivePresetParams
  ): Promise<{ presetKey: StartupCorePresetKey; version: number }> => {
    throw APIError.invalidArgument(
      "This endpoint is deprecated. Executive Board presets have been removed — activation is now workspace-scoped and explicit. Use POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/activate for each role instead."
    );
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

/**
 * DEPRECATED 2026-09-14 — activation chuyển sang cấp Workspace. Giữ endpoint để
 * client cũ nhận lỗi chỉ đường, không phải 404.
 */
export const activateProjectExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-roles/:roleKey/activate",
  },
  async (
    _params: ActivateProjectExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    throw APIError.invalidArgument(
      "This endpoint is deprecated. Executive Board activation is now workspace-scoped — use POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/activate instead."
    );
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

/**
 * DEPRECATED 2026-09-14 — xem ghi chú ở activateProjectExecutiveRoleApi.
 */
export const disableProjectExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-roles/:roleKey/disable",
  },
  async (
    _params: DisableProjectExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    throw APIError.invalidArgument(
      "This endpoint is deprecated. Executive Board activation is now workspace-scoped — use POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/disable instead."
    );
  }
);

interface ActivateWorkspaceExecutiveRoleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  roleKey: string;
  expectedVersion?: number;
  idempotencyKey?: string;
}

export const activateWorkspaceExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/workspaces/:workspaceId/executive-roles/:roleKey/activate",
  },
  async (
    params: ActivateWorkspaceExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await activateWorkspaceExecutiveRole(ctx, params.roleKey, {
      expectedVersion: params.expectedVersion,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

interface DisableWorkspaceExecutiveRoleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  roleKey: string;
  expectedVersion?: number;
  reason?: string;
  idempotencyKey?: string;
}

export const disableWorkspaceExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/workspaces/:workspaceId/executive-roles/:roleKey/disable",
  },
  async (
    params: DisableWorkspaceExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await disableWorkspaceExecutiveRole(ctx, params.roleKey, {
      expectedVersion: params.expectedVersion,
      reason: params.reason,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

export const getProjectExecutiveStageSuggestionApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/executive-board/stage-suggestion",
  },
  async (params: ListProjectExecutiveRolesParams): Promise<StageSuggestion> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await getStageSuggestion(ctx, params.projectId);
  }
);
