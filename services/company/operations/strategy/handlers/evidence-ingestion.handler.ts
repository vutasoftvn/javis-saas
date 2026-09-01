import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  ingestEvidenceSource,
  EvidenceIngestionReceipt,
  IngestClaimInput,
  SourceSystem,
} from "../services/evidence-ingestion.service";
import { listEvidenceIngestionsInWorkspace } from "../services/evidence-lifecycle.service";
import { assertNotAcademyReference } from "../../../academy/contracts";

export interface IngestEvidenceSourceRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  sourceSystem: SourceSystem;
  sourceRecordId: string;
  observedAt: string;
  artifactRef?: string;
  sourceUrl?: string;
  sourcePayloadHash: string;
  claims: IngestClaimInput[];
}

export interface ListEvidenceIngestionsRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
}

export const ingestEvidenceSourceEndpoint = api(
  { method: "POST", path: "/operations/strategy/evidence-ingestions", expose: true },
  async (params: IngestEvidenceSourceRequest): Promise<EvidenceIngestionReceipt> => {
    // Academy firewall: reject synthetic artifact refs before source ingestion
    assertNotAcademyReference(params.artifactRef, "artifactRef");
    assertNotAcademyReference(params.sourceRecordId, "sourceRecordId");

    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return ingestEvidenceSource(ctx, {
      projectId: params.projectId,
      sourceSystem: params.sourceSystem,
      sourceRecordId: params.sourceRecordId,
      observedAt: params.observedAt,
      artifactRef: params.artifactRef,
      sourceUrl: params.sourceUrl,
      sourcePayloadHash: params.sourcePayloadHash,
      claims: params.claims,
    });
  }
);

export const listEvidenceIngestionsEndpoint = api(
  { method: "GET", path: "/operations/strategy/evidence-ingestions", expose: true },
  async (
    params: ListEvidenceIngestionsRequest
  ): Promise<{ items: EvidenceIngestionReceipt[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listEvidenceIngestionsInWorkspace(ctx, params);
  }
);
