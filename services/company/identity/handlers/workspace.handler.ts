import { api } from "encore.dev/api";
import {
  Workspace,
  CreateWorkspaceParams,
  createWorkspaceRecord,
  getWorkspaceRecord,
} from "../services/workspace.service";

export { Workspace, CreateWorkspaceParams };

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
