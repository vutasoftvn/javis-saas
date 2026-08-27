import { api, Header, APIError } from "encore.dev/api";
import { verifyPlatformToken, requireWorkerServiceAuth } from "../services/token.service";
import * as ingestionSvc from "../services/document-ingestion.service";
import { verifyWorkspaceMembership } from "../services/workspace-connector.service";

export interface CreateDocumentIngestionParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  originalFilename: string;
  declaredMediaType: string;
  idempotencyKey: string;
}

export interface GetDocumentIngestionParams {
  authorization?: Header<"Authorization">;
  ingestionId: string;
  workspaceId: string;
}

export interface TransitionForWorkerParams {
  authorization?: Header<"Authorization">;
  ingestionId: string;
  claimToken: string;
  nextState: string;
  patch?: Record<string, unknown>;
}

export interface ReviewDocumentIngestionParams {
  authorization?: Header<"Authorization">;
  ingestionId: string;
  workspaceId: string;
  decision: "PUBLISHED" | "REJECTED";
  reason: string;
}

export interface CompleteDocumentIngestionUploadParams {
  authorization?: Header<"Authorization">;
  ingestionId: string;
  detectedMediaType: string;
  sizeBytes: number;
  sourceSha256: string;
  objectKey: string;
}

// Public endpoint: create a new document ingestion record
// Requires workspace membership
export const createDocumentIngestionEndpoint = api(
  { method: "POST", path: "/cosa/document-ingestions", expose: true },
  async (params: CreateDocumentIngestionParams) => {
    if (!params.authorization) {
      throw APIError.unauthenticated("missing authorization header");
    }

    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    // Verify caller is a member of the workspace
    await verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const record = await ingestionSvc.createDocumentIngestion({
      workspaceId: params.workspaceId,
      createdBy: claims.sub,
      originalFilename: params.originalFilename,
      declaredMediaType: params.declaredMediaType,
      idempotencyKey: params.idempotencyKey,
    });

    return sanitizeRecordForPublic(record);
  }
);

// Public endpoint: get document ingestion record
// Requires workspace membership
export const getDocumentIngestionEndpoint = api(
  { method: "GET", path: "/cosa/document-ingestions/:ingestionId", expose: true },
  async (params: GetDocumentIngestionParams) => {
    if (!params.authorization) {
      throw APIError.unauthenticated("missing authorization header");
    }

    const token = params.authorization.replace(/^Bearer\s+/i, "");
    verifyPlatformToken(token);

    // Verify caller is a member of the workspace
    await verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const record = await ingestionSvc.getDocumentIngestion(params.ingestionId);
    if (!record) {
      throw APIError.notFound("ingestion not found");
    }

    // Verify ownership: ingestion must belong to requested workspace
    if (record.workspaceId !== params.workspaceId) {
      throw APIError.permissionDenied("ingestion does not belong to this workspace");
    }

    return sanitizeRecordForPublic(record);
  }
);

// Worker-only endpoint: transition state via claim token
// Requires worker service authentication
export const transitionDocumentIngestionForWorkerEndpoint = api(
  { method: "POST", path: "/cosa/document-ingestions/:ingestionId/transition", expose: true },
  async (params: TransitionForWorkerParams) => {
    // Worker authentication (not platform JWT)
    requireWorkerServiceAuth(params.authorization);

    const nextState = params.nextState as ingestionSvc.DocumentIngestionState;
    const record = await ingestionSvc.transitionDocumentIngestionForWorker(
      params.ingestionId,
      params.claimToken,
      [],
      nextState,
      params.patch || {}
    );

    return sanitizeRecordForPublic(record);
  }
);

// Public endpoint: review document (member only)
// Allows transition from REVIEW_PENDING → PUBLISHED/REJECTED
export const reviewDocumentIngestionEndpoint = api(
  { method: "POST", path: "/cosa/document-ingestions/:ingestionId/review", expose: true },
  async (params: ReviewDocumentIngestionParams) => {
    if (!params.authorization) {
      throw APIError.unauthenticated("missing authorization header");
    }

    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    // Verify caller is a member of the workspace
    await verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const record = await ingestionSvc.reviewDocumentIngestion({
      ingestionId: params.ingestionId,
      reviewerId: claims.sub,
      decision: params.decision,
      reason: params.reason,
    });

    return sanitizeRecordForPublic(record);
  }
);

// Worker-only endpoint: complete file upload after server-side validation
// Requires worker service authentication (broker is trusted internal caller)
// Transitions UPLOADING → QUARANTINED → QUEUED and schedules validation task
export const completeDocumentIngestionUploadEndpoint = api(
  { method: "POST", path: "/cosa/document-ingestions/:ingestionId/complete", expose: true },
  async (params: CompleteDocumentIngestionUploadParams) => {
    // Worker authentication (not platform JWT)
    requireWorkerServiceAuth(params.authorization);

    const record = await ingestionSvc.completeUpload({
      ingestionId: params.ingestionId,
      actorId: "worker:broker",  // Audit: internal broker service
      detectedMediaType: params.detectedMediaType,
      sizeBytes: params.sizeBytes,
      sourceSha256: params.sourceSha256,
      objectKey: params.objectKey,
    });

    return sanitizeRecordForPublic(record);
  }
);

// Internal helper to sanitize records before returning to public callers
// NEVER expose originalObjectKey to public callers
function sanitizeRecordForPublic(record: ingestionSvc.DocumentIngestionRecord): any {
  return {
    id: record.id,
    workspaceId: record.workspaceId,
    createdBy: record.createdBy,
    originalFilename: record.originalFilename,
    declaredMediaType: record.declaredMediaType,
    detectedMediaType: record.detectedMediaType,
    sizeBytes: record.sizeBytes ? Number(record.sizeBytes) : null,
    sourceSha256: record.sourceSha256,
    state: record.state,
    idempotencyKey: record.idempotencyKey,
    knowledgeSourceId: record.knowledgeSourceId,
    converterSpecId: record.converterSpecId,
    manifestJson: record.manifestJson,
    failureCode: record.failureCode,
    claimToken: record.claimToken,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    // NOTE: originalObjectKey is intentionally NOT included
  };
}
