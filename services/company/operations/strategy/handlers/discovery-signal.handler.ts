import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  DiscoverySignal,
  CreateDiscoverySignalInput,
  ListDiscoverySignalsInput,
  UpdateDiscoverySignalInput,
  createDiscoverySignalInWorkspace,
  getDiscoverySignalInWorkspace,
  listDiscoverySignalsInWorkspace,
  updateDiscoverySignalInWorkspace,
  deleteDiscoverySignalInWorkspace,
} from "../services/discovery-signal.service";

export type { DiscoverySignal };

export interface CreateDiscoverySignalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  signalType: string;
  payload?: Record<string, any>;
  source: string;
}

export interface ListDiscoverySignalsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  signalType?: string;
}

export interface UpdateDiscoverySignalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  signalType?: string;
  payload?: Record<string, any>;
  source?: string;
}

export const createDiscoverySignal = api(
  { method: "POST", path: "/operations/strategy/discovery-signals", expose: true },
  async (params: CreateDiscoverySignalParams): Promise<DiscoverySignal> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createDiscoverySignalInWorkspace(ctx, params);
  }
);

export const getDiscoverySignal = api(
  { method: "GET", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<DiscoverySignal> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getDiscoverySignalInWorkspace(ctx, id);
  }
);

export const listDiscoverySignals = api(
  { method: "GET", path: "/operations/strategy/discovery-signals", expose: true },
  async (params: ListDiscoverySignalsParams): Promise<{ items: DiscoverySignal[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listDiscoverySignalsInWorkspace(ctx, params);
  }
);

export const updateDiscoverySignal = api(
  { method: "PATCH", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async (params: UpdateDiscoverySignalParams): Promise<DiscoverySignal> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateDiscoverySignalInWorkspace(ctx, params.id, params);
  }
);

export const deleteDiscoverySignal = api(
  { method: "DELETE", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteDiscoverySignalInWorkspace(ctx, id);
  }
);
