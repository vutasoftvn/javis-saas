import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  captureComplianceSnapshot,
  verifySnapshotIntegrity,
  listSnapshots,
} from "../services/ai-compliance-snapshot.service";

export interface CaptureSnapshotRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface VerifySnapshotRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  id: string;
}

export interface ListSnapshotsRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

// Non-exposed internal snapshot route as required by plan
export const captureComplianceSnapshotApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/snapshots", expose: false },
  async (req: CaptureSnapshotRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return captureComplianceSnapshot(ctx.workspaceId, ctx.workforceMemberId || ctx.userId);
  }
);

export const listComplianceSnapshotsApi = api(
  { method: "GET", path: "/finance-legal/ai-compliance/snapshots", expose: true },
  async (req: ListSnapshotsRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return listSnapshots(ctx.workspaceId);
  }
);

export const verifyComplianceSnapshotApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/snapshots/:id/verify", expose: true },
  async (req: VerifySnapshotRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const valid = await verifySnapshotIntegrity(ctx.workspaceId, req.id);
    return { valid };
  }
);
