import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  createMetricContractDraft,
  updateMetricContractDraft,
  publishMetricContract,
  reviseMetricContract,
  getMetricContractInWorkspace,
  listMetricContractsInWorkspace,
  MetricContractStatus,
  SourceMapping,
} from "../services/metric-contract.service";
import { metricContracts } from "../../../shared/db/schema/strategy";

export interface MetricContractDto {
  id: string;
  workspaceId: string;
  projectId: string;
  metricKey: string;
  displayName: string;
  unit: string;
  numeratorDefinition: string;
  denominatorDefinition: string;
  cohortDefinition: string;
  sourceMapping: SourceMapping;
  cadence: string;
  freshUntil: string | null;
  guardrail: string | null;
  ownerMemberId: string | null;
  decisionUse: string;
  status: MetricContractStatus;
  version: number;
  approvalRef: string | null;
  changeRationale: string | null;
  createdByMemberId: string | null;
  publishedByMemberId: string | null;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

function toMetricContractDto(row: typeof metricContracts.$inferSelect): MetricContractDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    metricKey: row.metricKey,
    displayName: row.displayName,
    unit: row.unit,
    numeratorDefinition: row.numeratorDefinition,
    denominatorDefinition: row.denominatorDefinition,
    cohortDefinition: row.cohortDefinition,
    sourceMapping: row.sourceMapping as SourceMapping,
    cadence: row.cadence,
    freshUntil: row.freshUntil ? row.freshUntil.toISOString() : null,
    guardrail: row.guardrail ?? null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    decisionUse: row.decisionUse,
    status: row.status as MetricContractStatus,
    version: row.version,
    approvalRef: row.approvalRef ?? null,
    changeRationale: row.changeRationale ?? null,
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    publishedByMemberId: row.publishedByMemberId ? row.publishedByMemberId.toString() : null,
    publishedAt: row.publishedAt ? row.publishedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export interface CreateMetricContractParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  metricKey: string;
  displayName: string;
  unit: string;
  numeratorDefinition: string;
  denominatorDefinition: string;
  cohortDefinition: string;
  sourceMapping: SourceMapping;
  cadence: string;
  freshUntil?: string;
  guardrail?: string;
  ownerMemberId: string;
  decisionUse: string;
  changeRationale?: string;
}

export interface UpdateMetricContractParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  displayName?: string;
  unit?: string;
  numeratorDefinition?: string;
  denominatorDefinition?: string;
  cohortDefinition?: string;
  sourceMapping?: SourceMapping;
  cadence?: string;
  freshUntil?: string;
  guardrail?: string;
  ownerMemberId?: string;
  decisionUse?: string;
  changeRationale?: string;
}

export interface PublishMetricContractRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  approvalRef: string;
}

export interface ReviseMetricContractRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  displayName?: string;
  unit?: string;
  numeratorDefinition?: string;
  denominatorDefinition?: string;
  cohortDefinition?: string;
  sourceMapping?: SourceMapping;
  cadence?: string;
  freshUntil?: string;
  guardrail?: string;
  ownerMemberId?: string;
  decisionUse?: string;
  changeRationale?: string;
}

export interface GetMetricContractParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface ListMetricContractsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
}

export const createMetricContract = api(
  { method: "POST", path: "/operations/strategy/metric-contracts", expose: true },
  async (params: CreateMetricContractParams): Promise<MetricContractDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await createMetricContractDraft({
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      metricKey: params.metricKey,
      displayName: params.displayName,
      unit: params.unit,
      numeratorDefinition: params.numeratorDefinition,
      denominatorDefinition: params.denominatorDefinition,
      cohortDefinition: params.cohortDefinition,
      sourceMapping: params.sourceMapping,
      cadence: params.cadence,
      freshUntil: params.freshUntil ? new Date(params.freshUntil) : undefined,
      guardrail: params.guardrail,
      ownerMemberId: BigInt(params.ownerMemberId),
      decisionUse: params.decisionUse,
      changeRationale: params.changeRationale,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toMetricContractDto(row);
  }
);

export const updateMetricContract = api(
  { method: "PATCH", path: "/operations/strategy/metric-contracts/:id", expose: true },
  async (params: UpdateMetricContractParams): Promise<MetricContractDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await updateMetricContractDraft({
      workspaceId: wsId,
      id: BigInt(params.id),
      displayName: params.displayName,
      unit: params.unit,
      numeratorDefinition: params.numeratorDefinition,
      denominatorDefinition: params.denominatorDefinition,
      cohortDefinition: params.cohortDefinition,
      sourceMapping: params.sourceMapping,
      cadence: params.cadence,
      freshUntil: params.freshUntil ? new Date(params.freshUntil) : undefined,
      guardrail: params.guardrail,
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : undefined,
      decisionUse: params.decisionUse,
      changeRationale: params.changeRationale,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toMetricContractDto(row);
  }
);

export const publishMetricContractHandler = api(
  { method: "POST", path: "/operations/strategy/metric-contracts/:id/publish", expose: true },
  async (params: PublishMetricContractRequestParams): Promise<MetricContractDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await publishMetricContract({
      workspaceId: wsId,
      id: BigInt(params.id),
      approvalRef: params.approvalRef,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toMetricContractDto(row);
  }
);

export const reviseMetricContractHandler = api(
  { method: "POST", path: "/operations/strategy/metric-contracts/:id/revise", expose: true },
  async (params: ReviseMetricContractRequestParams): Promise<MetricContractDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await reviseMetricContract({
      workspaceId: wsId,
      id: BigInt(params.id),
      displayName: params.displayName,
      unit: params.unit,
      numeratorDefinition: params.numeratorDefinition,
      denominatorDefinition: params.denominatorDefinition,
      cohortDefinition: params.cohortDefinition,
      sourceMapping: params.sourceMapping,
      cadence: params.cadence,
      freshUntil: params.freshUntil ? new Date(params.freshUntil) : undefined,
      guardrail: params.guardrail,
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : undefined,
      decisionUse: params.decisionUse,
      changeRationale: params.changeRationale,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toMetricContractDto(row);
  }
);

export const getMetricContract = api(
  { method: "GET", path: "/operations/strategy/metric-contracts/:id", expose: true },
  async (params: GetMetricContractParams): Promise<MetricContractDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await getMetricContractInWorkspace(wsId, BigInt(params.id));
    return toMetricContractDto(row);
  }
);

export const listMetricContracts = api(
  { method: "GET", path: "/operations/strategy/metric-contracts", expose: true },
  async (params: ListMetricContractsParams): Promise<{ items: MetricContractDto[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const rows = await listMetricContractsInWorkspace(
      wsId,
      params.projectId ? BigInt(params.projectId) : undefined
    );
    return { items: rows.map(toMetricContractDto) };
  }
);
