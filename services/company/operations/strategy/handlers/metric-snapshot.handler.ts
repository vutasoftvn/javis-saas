import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  ingestMetricSnapshot,
  getMetricSnapshotInWorkspace,
  listMetricSnapshotsInWorkspace,
  MetricSnapshotQuality,
  QualityChecks,
} from "../services/metric-snapshot.service";
import { metricSnapshots } from "../../../shared/db/schema/strategy";

export interface MetricSnapshotDto {
  id: string;
  workspaceId: string;
  projectId: string;
  contractVersionId: string;
  sourceSystem: string;
  sourceWindow: string;
  sourceRecordId: string;
  payloadHash: string;
  observedAt: string;
  capturedAt: string;
  value: number;
  numerator: number | null;
  denominator: number | null;
  qualityStatus: MetricSnapshotQuality;
  qualityChecks: QualityChecks;
  evidenceIngestionId: string | null;
  createdAt: string;
}

function toMetricSnapshotDto(row: typeof metricSnapshots.$inferSelect): MetricSnapshotDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    contractVersionId: row.contractVersionId.toString(),
    sourceSystem: row.sourceSystem,
    sourceWindow: row.sourceWindow,
    sourceRecordId: row.sourceRecordId,
    payloadHash: row.payloadHash,
    observedAt: row.observedAt.toISOString(),
    capturedAt: row.capturedAt.toISOString(),
    value: row.value,
    numerator: row.numerator ?? null,
    denominator: row.denominator ?? null,
    qualityStatus: row.qualityStatus as MetricSnapshotQuality,
    qualityChecks: (row.qualityChecks as QualityChecks) || {},
    evidenceIngestionId: row.evidenceIngestionId ? row.evidenceIngestionId.toString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export interface IngestMetricSnapshotRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  contractVersionId: string;
  sourceSystem: string;
  sourceWindow: string;
  sourceRecordId: string;
  payloadHash: string;
  observedAt: string;
  value: number;
  numerator?: number;
  denominator?: number;
  qualityChecks?: QualityChecks;
  evidenceIngestionId?: string;
}

export interface GetMetricSnapshotParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface ListMetricSnapshotsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  contractVersionId?: string;
  projectId?: string;
}

export const ingestMetricSnapshotHandler = api(
  { method: "POST", path: "/operations/strategy/metric-snapshots", expose: true },
  async (params: IngestMetricSnapshotRequestParams): Promise<MetricSnapshotDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await ingestMetricSnapshot({
      workspaceId: wsId,
      contractVersionId: BigInt(params.contractVersionId),
      sourceSystem: params.sourceSystem,
      sourceWindow: params.sourceWindow,
      sourceRecordId: params.sourceRecordId,
      payloadHash: params.payloadHash,
      observedAt: new Date(params.observedAt),
      value: params.value,
      numerator: params.numerator,
      denominator: params.denominator,
      qualityChecks: params.qualityChecks,
      evidenceIngestionId: params.evidenceIngestionId ? BigInt(params.evidenceIngestionId) : undefined,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toMetricSnapshotDto(row);
  }
);

export const getMetricSnapshot = api(
  { method: "GET", path: "/operations/strategy/metric-snapshots/:id", expose: true },
  async (params: GetMetricSnapshotParams): Promise<MetricSnapshotDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await getMetricSnapshotInWorkspace(wsId, BigInt(params.id));
    return toMetricSnapshotDto(row);
  }
);

export const listMetricSnapshots = api(
  { method: "GET", path: "/operations/strategy/metric-snapshots", expose: true },
  async (params: ListMetricSnapshotsParams): Promise<{ items: MetricSnapshotDto[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const rows = await listMetricSnapshotsInWorkspace(
      wsId,
      params.contractVersionId ? BigInt(params.contractVersionId) : undefined,
      params.projectId ? BigInt(params.projectId) : undefined
    );

    return { items: rows.map(toMetricSnapshotDto) };
  }
);
