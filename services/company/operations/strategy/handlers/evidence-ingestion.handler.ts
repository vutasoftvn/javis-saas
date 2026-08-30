import { api, Header, APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db } from "../../models/db";
import { evidenceIngestions, evidence } from "../../../shared/db/schema/strategy";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  ingestEvidenceSource,
  EvidenceIngestionReceipt,
  IngestClaimInput,
  SourceSystem,
} from "../services/evidence-ingestion.service";
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
    const wsId = BigInt(ctx.workspaceId);

    const conditions = [eq(evidenceIngestions.workspaceId, wsId)];
    if (params.projectId) {
      conditions.push(eq(evidenceIngestions.projectId, BigInt(params.projectId)));
    }

    const rows = await db
      .select()
      .from(evidenceIngestions)
      .where(and(...conditions))
      .orderBy(desc(evidenceIngestions.createdAt));

    const items: EvidenceIngestionReceipt[] = [];
    for (const r of rows) {
      const evCount = await db
        .select({ id: evidence.id })
        .from(evidence)
        .where(eq(evidence.evidenceIngestionId, r.id));

      items.push({
        id: r.id.toString(),
        workspaceId: r.workspaceId.toString(),
        projectId: r.projectId.toString(),
        sourceSystem: r.sourceSystem,
        sourceRecordId: r.sourceRecordId,
        sourcePayloadHash: r.sourcePayloadHash,
        artifactRef: r.artifactRef ?? null,
        sourceUrl: r.sourceUrl ?? null,
        observedAt: r.observedAt.toISOString(),
        ingestedByMemberId: r.ingestedByMemberId ? r.ingestedByMemberId.toString() : null,
        createdAt: r.createdAt.toISOString(),
        evidenceCount: evCount.length,
        isReplay: false,
      });
    }

    return { items };
  }
);
