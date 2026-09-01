import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  ingestMetricSnapshot,
  getMetricSnapshotInWorkspace,
  listMetricSnapshotsInWorkspace,
  MetricSnapshotQuality,
  QualityChecks,
  MetricSnapshotDto,
  toMetricSnapshotDto,
} from "../services/metric-snapshot.service";

export type { MetricSnapshotDto, MetricSnapshotQuality, QualityChecks };

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
