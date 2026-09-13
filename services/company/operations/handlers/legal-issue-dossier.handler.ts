import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  LegalApplicabilityStatus,
  LegalIssueCategory,
  LegalIssueReasonCode,
  LegalIssueSnapshot,
  LegalRecordRef,
  appendLegalIssueRevision,
  createLegalIssueDossier,
  readLegalIssueSnapshot,
} from "../services/legal-issue-dossier.service";

export const createLegalIssueDossierEndpoint = api(
  { method: "POST", path: "/operations/legal-issue-dossiers", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    projectId: string;
    issueCategory: LegalIssueCategory;
    legalRecordRefs?: LegalRecordRef[];
    applicabilityStatus?: LegalApplicabilityStatus;
    jurisdiction?: string;
    redactedQuestion: string;
    reasonCode: LegalIssueReasonCode;
  }): Promise<LegalIssueSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Chỉ forward field thuộc allowlist của service — không forward nguyên
    // `params` (có `workspaceId`/`authorization` từ Header) vì service này
    // dùng allowlist NGHIÊM NGẶT reject bất kỳ key lạ nào, nên forward thẳng
    // request params sẽ luôn bị LEGAL_DOSSIER_FIELD_REJECTED qua HTTP thật
    // (đúng bug đã xảy ra ở CHRO Task 1 — xem progress.md lesson #7).
    return createLegalIssueDossier(ctx, {
      projectId: params.projectId,
      issueCategory: params.issueCategory,
      legalRecordRefs: params.legalRecordRefs,
      applicabilityStatus: params.applicabilityStatus,
      jurisdiction: params.jurisdiction,
      redactedQuestion: params.redactedQuestion,
      reasonCode: params.reasonCode,
    });
  }
);

export const appendLegalIssueRevisionEndpoint = api(
  { method: "POST", path: "/operations/legal-issue-dossiers/:id/revisions", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    expectedVersion: number;
    issueCategory: LegalIssueCategory;
    legalRecordRefs?: LegalRecordRef[];
    applicabilityStatus?: LegalApplicabilityStatus;
    jurisdiction?: string;
    redactedQuestion: string;
    status?: "DRAFT" | "CONFIRMED";
    reasonCode: LegalIssueReasonCode;
  }): Promise<LegalIssueSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Xem ghi chú ở createLegalIssueDossierEndpoint — chỉ forward field thuộc
    // allowlist của service, không forward nguyên `params`.
    return appendLegalIssueRevision(ctx, params.id, params.expectedVersion, {
      issueCategory: params.issueCategory,
      legalRecordRefs: params.legalRecordRefs,
      applicabilityStatus: params.applicabilityStatus,
      jurisdiction: params.jurisdiction,
      redactedQuestion: params.redactedQuestion,
      status: params.status,
      reasonCode: params.reasonCode,
    });
  }
);

export const readLegalIssueSnapshotEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/legal-issue-dossier", expose: true },
  async (params: {
    projectId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<LegalIssueSnapshot> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return readLegalIssueSnapshot(ctx, params.projectId);
  }
);
