import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  RuntimeItem,
  RuntimeItemDetail,
  SourceStatus,
  getNeedsYouService,
  getBlockersService,
  getWorkInspectorService,
  snoozeRuntimeItemService,
  getSourceStatusService,
} from "../services/workspace-runtime.service";

export interface RuntimeAuthParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface RuntimeItemParams extends RuntimeAuthParams {
  sourceKind: string;
  sourceId: string;
}

export interface SnoozeParams extends RuntimeItemParams {
  snoozedUntil: string;
}

// ─── Workspace Runtime Handlers ───

export const listNeedsYou = api(
  { expose: true, method: "GET", path: "/operations/workspace-runtime/needs-you" },
  async (params: RuntimeAuthParams): Promise<MvpSuccess<readonly RuntimeItem[]>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getNeedsYouService(ctx);
  }
);

export const listBlockers = api(
  { expose: true, method: "GET", path: "/operations/workspace-runtime/blockers" },
  async (params: RuntimeAuthParams): Promise<MvpSuccess<readonly RuntimeItem[]>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getBlockersService(ctx);
  }
);

export const getWorkInspector = api(
  { expose: true, method: "GET", path: "/operations/workspace-runtime/items/:sourceKind/:sourceId" },
  async (params: RuntimeItemParams): Promise<MvpSuccess<RuntimeItemDetail>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getWorkInspectorService(ctx, params.sourceKind, params.sourceId);
  }
);

export const snoozeRuntimeItem = api(
  { expose: true, method: "POST", path: "/operations/workspace-runtime/items/:sourceKind/:sourceId/snooze" },
  async (params: SnoozeParams): Promise<MvpSuccess<{ snoozed: boolean }>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return snoozeRuntimeItemService(ctx, params.sourceKind, params.sourceId, params.snoozedUntil);
  }
);

export const getSourceStatus = api(
  { expose: true, method: "GET", path: "/operations/workspace-runtime/source-status" },
  async (params: RuntimeAuthParams): Promise<MvpSuccess<readonly SourceStatus[]>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getSourceStatusService(ctx);
  }
);
