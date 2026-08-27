import { api, Header } from "encore.dev/api";
import {
  Workspace,
  CreateWorkspaceParams,
  createWorkspaceRecord,
  getWorkspaceRecord,
  WorkspacePlatformCompanyResponse,
  getWorkspacePlatformCompany,
} from "../services/workspace.service";

export { Workspace, CreateWorkspaceParams, WorkspacePlatformCompanyResponse };

export const createWorkspace = api(
  { method: "POST", path: "/identity/workspaces", expose: false },
  async (params: CreateWorkspaceParams): Promise<Workspace> => {
    return createWorkspaceRecord(params);
  }
);

export const getWorkspace = api(
  { method: "GET", path: "/identity/workspaces/:id", expose: true },
  async ({ id }: { id: string }): Promise<Workspace> => {
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
