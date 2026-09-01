import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  Evidence,
  RecordEvidenceInput,
  ListEvidenceInput,
  UpdateEvidenceInput,
  recordEvidenceInWorkspace,
  getEvidenceInWorkspace,
  listEvidenceInWorkspace,
  updateEvidenceInWorkspace,
  deleteEvidenceInWorkspace,
} from "../services/evidence-lifecycle.service";
import { EvidenceSourceType } from "../services/evidence-scoring.service";

export type { Evidence };

export interface RecordEvidenceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  experimentId?: string | number;
  sourceType: EvidenceSourceType;
  claim: string;
  rawStrength?: number;
  rawConfidence?: number;
  sampleSize?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
  status?: "candidate" | "approved";
  artifactRef?: string;
  artifactKind?: string;
}

export interface ListEvidenceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  experimentId?: string | number;
  status?: string;
}

export interface UpdateEvidenceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  claim?: string;
  strength?: number;
  confidence?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral";
}

export const recordEvidence = api(
  { method: "POST", path: "/operations/strategy/evidence", expose: true },
  async (params: RecordEvidenceParams): Promise<Evidence> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return recordEvidenceInWorkspace(ctx, params);
  }
);

export const getEvidence = api(
  { method: "GET", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<Evidence> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getEvidenceInWorkspace(ctx, id);
  }
);

export const listEvidence = api(
  { method: "GET", path: "/operations/strategy/evidence", expose: true },
  async (params: ListEvidenceParams): Promise<{ items: Evidence[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listEvidenceInWorkspace(ctx, params);
  }
);

export const updateEvidence = api(
  { method: "PATCH", path: "/operations/strategy/evidence/:id", expose: true },
  async (params: UpdateEvidenceParams): Promise<Evidence> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateEvidenceInWorkspace(ctx, params.id, params);
  }
);

export const deleteEvidence = api(
  { method: "DELETE", path: "/operations/strategy/evidence/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteEvidenceInWorkspace(ctx, id);
  }
);
