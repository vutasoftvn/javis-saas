import { api, Header } from "encore.dev/api";
import {
  Workspace,
  CreateWorkspaceParams,
  createWorkspaceRecord,
  getWorkspaceRecord,
  updateWorkspaceOrientationRecord,
  WorkspacePlatformCompanyResponse,
  getWorkspacePlatformCompany,
} from "../services/workspace.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { Workspace, CreateWorkspaceParams, WorkspacePlatformCompanyResponse };

export const createWorkspace = api(
  { method: "POST", path: "/identity/workspaces", expose: false },
  async (params: CreateWorkspaceParams): Promise<Workspace> => {
    return createWorkspaceRecord(params);
  }
);

export const getWorkspace = api(
  { method: "GET", path: "/identity/workspaces/:id", expose: true },
  async ({
    id,
    authorization,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
  }): Promise<Workspace> => {
    // Trước đây endpoint này public hoàn toàn (không kiểm tra ai đang gọi) dù
    // frontend (workspace_orientation_service.dart) đã gửi Bearer token —
    // giờ xác thực caller thực sự thuộc workspace này trước khi trả dữ liệu.
    await requireWorkspaceAccess(authorization, id);
    return getWorkspaceRecord(id);
  }
);

export const getWorkspacePlatformCompanyEndpoint = api(
  { method: "GET", path: "/identity/workspaces/:workspaceId/platform-company", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: string;
    authorization?: Header<"Authorization">;
  }): Promise<WorkspacePlatformCompanyResponse> => {
    return getWorkspacePlatformCompany({
      workspaceId,
      authorization,
    });
  }
);

export const updateWorkspaceCompanyIdentity = api(
  { method: "PATCH", path: "/identity/workspaces/:id/company-identity", expose: true },
  async ({
    id,
    authorization,
    vision,
    mission,
    coreValues,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    vision?: string | null;
    mission?: string | null;
    coreValues?: string | null;
  }): Promise<Workspace> => {
    return updateWorkspaceOrientationRecord({
      workspaceId: id,
      authorization,
      vision,
      mission,
      coreValues,
    });
  }
);

