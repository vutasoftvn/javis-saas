import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  AiGovernanceDossierSnapshot,
  AiGovernanceReasonCode,
  AiGovernanceSnapshotDraft,
  AiGovernanceSourceRef,
  RiskSignal,
  appendAiGovernanceRevision,
  createAiGovernanceDossier,
  readAiGovernanceSnapshot,
} from "../services/ai-governance-dossier.service";

export const createAiGovernanceDossierEndpoint = api(
  { method: "POST", path: "/operations/ai-governance-dossiers", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectId: string;
    snapshot: AiGovernanceSnapshotDraft;
    riskSignals?: RiskSignal[];
    sourceRefs?: AiGovernanceSourceRef[];
    reasonCode: AiGovernanceReasonCode;
  }): Promise<AiGovernanceDossierSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Chỉ forward field thuộc allowlist của service — không forward nguyên
    // `params` (có `workspaceId`/`authorization` từ Header) vì service này
    // dùng allowlist NGHIÊM NGẶT reject bất kỳ key lạ nào (xem progress.md
    // lesson #7 — bug thật đã xảy ra khi forward thẳng raw Encore params).
    return createAiGovernanceDossier(ctx, {
      projectId: params.projectId,
      snapshot: params.snapshot,
      riskSignals: params.riskSignals,
      sourceRefs: params.sourceRefs,
      reasonCode: params.reasonCode,
    });
  }
);

export const appendAiGovernanceRevisionEndpoint = api(
  { method: "POST", path: "/operations/ai-governance-dossiers/:id/revisions", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    expectedVersion: number;
    snapshot: AiGovernanceSnapshotDraft;
    riskSignals?: RiskSignal[];
    sourceRefs?: AiGovernanceSourceRef[];
    status?: "DRAFT" | "CONFIRMED";
    reasonCode: AiGovernanceReasonCode;
  }): Promise<AiGovernanceDossierSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Xem ghi chú ở createAiGovernanceDossierEndpoint — chỉ forward field
    // thuộc allowlist của service, không forward nguyên `params`.
    return appendAiGovernanceRevision(ctx, params.id, params.expectedVersion, {
      snapshot: params.snapshot,
      riskSignals: params.riskSignals,
      sourceRefs: params.sourceRefs,
      status: params.status,
      reasonCode: params.reasonCode,
    });
  }
);

export const readAiGovernanceSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/ai-governance-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<AiGovernanceDossierSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return readAiGovernanceSnapshot(ctx, params.projectId);
  }
);
