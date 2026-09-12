import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  EvidenceRef,
  ProductDecisionSnapshot,
  appendProductDecisionRevision,
  createProductDecisionDossier,
  readProductDecisionSnapshot,
} from "../services/product-decision-dossier.service";

export const createProductDecisionDossierEndpoint = api(
  { method: "POST", path: "/operations/product-decision-dossiers", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectId: string;
    title: string;
    assumptions?: unknown[];
    evidenceRefs?: EvidenceRef[];
    reasonCode?: string;
    narrative?: string;
  }): Promise<ProductDecisionSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createProductDecisionDossier(ctx, params);
  }
);

export const appendProductDecisionRevisionEndpoint = api(
  { method: "POST", path: "/operations/product-decision-dossiers/:id/revisions", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    expectedVersion: number;
    assumptions?: unknown[];
    evidenceRefs?: EvidenceRef[];
    status?: "DRAFT" | "CONFIRMED";
    reasonCode: string;
    narrative?: string;
  }): Promise<ProductDecisionSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return appendProductDecisionRevision(ctx, params.id, params.expectedVersion, params);
  }
);

export const readProductDecisionSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/product-decision-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<ProductDecisionSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return readProductDecisionSnapshot(ctx, params.projectId);
  }
);
