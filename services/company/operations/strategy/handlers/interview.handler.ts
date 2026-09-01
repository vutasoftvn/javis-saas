import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  Interview,
  CreateInterviewInput,
  ListInterviewsInput,
  UpdateInterviewInput,
  createInterviewInWorkspace,
  getInterviewInWorkspace,
  listInterviewsInWorkspace,
  updateInterviewInWorkspace,
  deleteInterviewInWorkspace,
} from "../services/interview.service";

export type { Interview };

export interface CreateInterviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  contactRef?: string | number;
  notes: string;
  conductedAt?: string;
}

export interface ListInterviewsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
}

export interface UpdateInterviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  contactRef?: string | number;
  notes?: string;
  conductedAt?: string;
}

export const createInterview = api(
  { method: "POST", path: "/operations/strategy/interviews", expose: true },
  async (params: CreateInterviewParams): Promise<Interview> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createInterviewInWorkspace(ctx, params);
  }
);

export const getInterview = api(
  { method: "GET", path: "/operations/strategy/interviews/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Interview> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getInterviewInWorkspace(ctx, id);
  }
);

export const listInterviews = api(
  { method: "GET", path: "/operations/strategy/interviews", expose: true },
  async (params: ListInterviewsParams): Promise<{ items: Interview[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listInterviewsInWorkspace(ctx, params);
  }
);

export const updateInterview = api(
  { method: "PATCH", path: "/operations/strategy/interviews/:id", expose: true },
  async (params: UpdateInterviewParams): Promise<Interview> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateInterviewInWorkspace(ctx, params.id, params);
  }
);

export const deleteInterview = api(
  { method: "DELETE", path: "/operations/strategy/interviews/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteInterviewInWorkspace(ctx, id);
  }
);
