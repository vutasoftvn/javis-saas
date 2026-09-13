import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { EvidenceRef } from "../services/product-decision-dossier.service";
import {
  SecurityControl,
  SecurityFinding,
  SecurityPostureReasonCode,
  SecurityPostureSnapshot,
  appendSecurityPostureRevision,
  createSecurityPostureDossier,
  readSecurityPostureSnapshot,
} from "../services/security-posture.service";

export const createSecurityPostureDossierEndpoint = api(
  { method: "POST", path: "/operations/security-posture-dossiers", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectId: string;
    controls?: SecurityControl[];
    findings?: SecurityFinding[];
    evidenceRefs?: EvidenceRef[];
    reasonCode: SecurityPostureReasonCode;
  }): Promise<SecurityPostureSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Chỉ forward field thuộc allowlist của service — không forward nguyên
    // `params` (có `workspaceId`/`authorization` từ Header) vì service này
    // dùng allowlist NGHIÊM NGẶT reject bất kỳ key lạ nào (headline
    // secret-free property), nên forward thẳng request params sẽ luôn bị
    // SECURITY_DOSSIER_FIELD_REJECTED qua HTTP thật (đúng bug đã xảy ra ở
    // People Risk Dossier Task 1 — xem progress.md lesson #7).
    return createSecurityPostureDossier(ctx, {
      projectId: params.projectId,
      controls: params.controls,
      findings: params.findings,
      evidenceRefs: params.evidenceRefs,
      reasonCode: params.reasonCode,
    });
  }
);

export const appendSecurityPostureRevisionEndpoint = api(
  { method: "POST", path: "/operations/security-posture-dossiers/:id/revisions", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    expectedVersion: number;
    controls?: SecurityControl[];
    findings?: SecurityFinding[];
    evidenceRefs?: EvidenceRef[];
    status?: "DRAFT" | "CONFIRMED";
    reasonCode: SecurityPostureReasonCode;
  }): Promise<SecurityPostureSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Xem ghi chú ở createSecurityPostureDossierEndpoint — chỉ forward field
    // thuộc allowlist của service, không forward nguyên `params`.
    return appendSecurityPostureRevision(ctx, params.id, params.expectedVersion, {
      controls: params.controls,
      findings: params.findings,
      evidenceRefs: params.evidenceRefs,
      status: params.status,
      reasonCode: params.reasonCode,
    });
  }
);

export const readSecurityPostureSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/security-posture-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<SecurityPostureSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return readSecurityPostureSnapshot(ctx, params.projectId);
  }
);
