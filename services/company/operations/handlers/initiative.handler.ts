import { api, APIError, Header } from "encore.dev/api";
import {
  Initiative,
  InitiativeMilestone,
  createInitiativeService,
  updateInitiativeService,
  approveInitiativeService,
  getInitiativeService,
  listInitiativesService,
} from "../services/initiative.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { Initiative, InitiativeMilestone };

export interface CreateInitiativeParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
  strategicObjectiveId?: string;
  sourceTowsOptionId?: string;
  title: string;
  description?: string;
  intendedOutcome?: string;
  startDate?: string;
  targetDate?: string;
  milestones?: InitiativeMilestone[];
  ownerMemberId?: string;
  keyResultIds?: string[];
  status?: string;
}

export interface UpdateInitiativeParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  projectId?: string;
  strategicObjectiveId?: string;
  sourceTowsOptionId?: string;
  title?: string;
  description?: string;
  intendedOutcome?: string;
  startDate?: string;
  targetDate?: string;
  milestones?: InitiativeMilestone[];
  status?: string;
  ownerMemberId?: string;
  keyResultIds?: string[];
  expectedRevision?: number;
}

export interface ApproveInitiativeParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  reason?: string;
}

export interface ListInitiativesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
  strategicObjectiveId?: string;
  approvalStatus?: string;
}

export const createInitiative = api(
  { method: "POST", path: "/operations/initiatives", expose: true },
  async (params: CreateInitiativeParams): Promise<Initiative> => {
    return createInitiativeService(params, params.authorization);
  }
);

export const getInitiative = api(
  { method: "GET", path: "/operations/initiatives/:id", expose: true },
  async ({
    id,
    authorization,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
  }): Promise<Initiative> => {
    return getInitiativeService(id, authorization);
  }
);

export const updateInitiative = api(
  { method: "PUT", path: "/operations/initiatives/:id", expose: true },
  async (params: UpdateInitiativeParams): Promise<Initiative> => {
    if ("approvalStatus" in params) {
      throw APIError.invalidArgument(
        "approvalStatus may only be changed through the initiative approval command"
      );
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateInitiativeService(params, ctx);
  }
);

export const approveInitiative = api(
  { method: "POST", path: "/operations/initiatives/:id/approve", expose: true },
  async (params: ApproveInitiativeParams): Promise<Initiative> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return approveInitiativeService(params, ctx);
  }
);

export const listInitiatives = api(
  { method: "GET", path: "/operations/initiatives", expose: true },
  async (params: ListInitiativesParams): Promise<{ items: Initiative[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listInitiativesService(params, ctx);
  }
);
