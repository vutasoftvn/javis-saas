import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import {
  DataAsset,
  DataGovernanceReasonCode,
  DataGovernanceSnapshot,
  DataSourceRef,
  appendDataGovernanceRevision,
  createDataGovernanceDossier,
  readDataGovernanceSnapshot,
} from "../services/data-governance-dossier.service";

export const createDataGovernanceDossierEndpoint = api(
  { method: "POST", path: "/operations/data-governance-dossiers", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectId: string;
    assets?: DataAsset[];
    sourceRefs?: DataSourceRef[];
    reasonCode: DataGovernanceReasonCode;
  }): Promise<DataGovernanceSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Chỉ forward field thuộc allowlist của service — không forward nguyên
    // `params` (có `workspaceId`/`authorization` từ Header) vì service này
    // dùng allowlist NGHIÊM NGẶT reject bất kỳ key lạ nào, nên forward thẳng
    // request params sẽ luôn bị DATA_DOSSIER_FIELD_REJECTED qua HTTP thật
    // (đúng bug đã xảy ra ở CHRO Task 1 — xem progress.md lesson #7).
    return createDataGovernanceDossier(ctx, {
      projectId: params.projectId,
      assets: params.assets,
      sourceRefs: params.sourceRefs,
      reasonCode: params.reasonCode,
    });
  }
);

export const appendDataGovernanceRevisionEndpoint = api(
  { method: "POST", path: "/operations/data-governance-dossiers/:id/revisions", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    expectedVersion: number;
    assets?: DataAsset[];
    sourceRefs?: DataSourceRef[];
    status?: "DRAFT" | "CONFIRMED";
    reasonCode: DataGovernanceReasonCode;
  }): Promise<DataGovernanceSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Xem ghi chú ở createDataGovernanceDossierEndpoint — chỉ forward field
    // thuộc allowlist của service, không forward nguyên `params`.
    return appendDataGovernanceRevision(ctx, params.id, params.expectedVersion, {
      assets: params.assets,
      sourceRefs: params.sourceRefs,
      status: params.status,
      reasonCode: params.reasonCode,
    });
  }
);

export const readDataGovernanceSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/data-governance-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<DataGovernanceSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId, { agentCapabilities: [AGENT_CAP.DATA_GOVERNANCE_READ] });
    return readDataGovernanceSnapshot(ctx, params.projectId);
  }
);
