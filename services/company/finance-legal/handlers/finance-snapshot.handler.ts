import { api, Header } from "encore.dev/api";
import {
  FinanceManagementSnapshot,
  RecordFinanceSnapshotParams as BaseRecordFinanceSnapshotParams,
  recordFinanceSnapshotService,
  getLatestFinanceSnapshotService,
} from "../services/finance-snapshot.service";

export { FinanceManagementSnapshot };

export interface RecordFinanceSnapshotParams extends BaseRecordFinanceSnapshotParams {
  authorization?: Header<"Authorization">;
}

export const recordFinanceSnapshot = api(
  { method: "POST", path: "/finance-legal/snapshots", expose: true },
  async (params: RecordFinanceSnapshotParams): Promise<FinanceManagementSnapshot> => {
    return recordFinanceSnapshotService(params, params.authorization);
  }
);

export const getLatestFinanceSnapshot = api(
  { method: "GET", path: "/finance-legal/snapshots/latest", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: number;
    authorization?: Header<"Authorization">;
  }): Promise<FinanceManagementSnapshot> => {
    return getLatestFinanceSnapshotService(workspaceId, authorization);
  }
);
