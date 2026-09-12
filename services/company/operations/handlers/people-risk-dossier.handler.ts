import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { EvidenceRef } from "../services/product-decision-dossier.service";
import {
  CapacityBand,
  PeopleRiskSnapshot,
  RiskSignal,
  appendPeopleRiskRevision,
  createPeopleRiskDossier,
  readPeopleRiskSnapshot,
} from "../services/people-risk-dossier.service";

export const createPeopleRiskDossierEndpoint = api(
  { method: "POST", path: "/operations/people-risk-dossiers", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectId: string;
    capacityBands?: CapacityBand[];
    riskSignals?: RiskSignal[];
    sourceRefs?: EvidenceRef[];
    reasonCode?: string;
    narrative?: string;
  }): Promise<PeopleRiskSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createPeopleRiskDossier(ctx, params);
  }
);

export const appendPeopleRiskRevisionEndpoint = api(
  { method: "POST", path: "/operations/people-risk-dossiers/:id/revisions", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    expectedVersion: number;
    capacityBands?: CapacityBand[];
    riskSignals?: RiskSignal[];
    sourceRefs?: EvidenceRef[];
    status?: "DRAFT" | "CONFIRMED";
    reasonCode: string;
    narrative?: string;
  }): Promise<PeopleRiskSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return appendPeopleRiskRevision(ctx, params.id, params.expectedVersion, params);
  }
);

export const readPeopleRiskSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/people-risk-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<PeopleRiskSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return readPeopleRiskSnapshot(ctx, params.projectId);
  }
);
