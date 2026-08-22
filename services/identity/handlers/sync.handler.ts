import { api } from "encore.dev/api";
import {
  SyncFromPlatformParams,
  SyncFromPlatformResult,
  syncFromPlatformService,
} from "../services/sync.service";

export { SyncFromPlatformParams, SyncFromPlatformResult };

export const syncFromPlatform = api(
  { method: "POST", path: "/identity/sync-from-platform", expose: true, auth: false },
  async (params: SyncFromPlatformParams): Promise<SyncFromPlatformResult> => {
    return syncFromPlatformService(params);
  }
);
