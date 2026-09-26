import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import { EvidenceRef } from "../services/product-decision-dossier.service";
import {
  CapacityBand,
  PeopleRiskReasonCode,
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
    reasonCode: PeopleRiskReasonCode;
  }): Promise<PeopleRiskSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Chỉ forward field thuộc allowlist của service — không forward nguyên
    // `params` (có `workspaceId`/`authorization` từ Header) vì service này
    // (khác product-decision-dossier) dùng allowlist NGHIÊM NGẶT reject bất
    // kỳ key lạ nào (headline privacy property), nên forward thẳng request
    // params sẽ luôn bị PEOPLE_DOSSIER_FIELD_REJECTED qua HTTP thật.
    return createPeopleRiskDossier(ctx, {
      projectId: params.projectId,
      capacityBands: params.capacityBands,
      riskSignals: params.riskSignals,
      sourceRefs: params.sourceRefs,
      reasonCode: params.reasonCode,
    });
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
    reasonCode: PeopleRiskReasonCode;
  }): Promise<PeopleRiskSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Xem ghi chú ở createPeopleRiskDossierEndpoint — chỉ forward field
    // thuộc allowlist của service, không forward nguyên `params`.
    return appendPeopleRiskRevision(ctx, params.id, params.expectedVersion, {
      capacityBands: params.capacityBands,
      riskSignals: params.riskSignals,
      sourceRefs: params.sourceRefs,
      status: params.status,
      reasonCode: params.reasonCode,
    });
  }
);

export const readPeopleRiskSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/people-risk-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<PeopleRiskSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId, { agentCapabilities: [AGENT_CAP.PEOPLE_RISK_READ] });
    return readPeopleRiskSnapshot(ctx, params.projectId);
  }
);
