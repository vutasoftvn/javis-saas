import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  createPilotDraft,
  approvePilot as approvePilotService,
  activatePilot as activatePilotService,
  closePilot as closePilotService,
  getPilotInWorkspace,
  listPilotsInWorkspace,
  PilotRunStatus,
} from "../services/pilot-run.service";
import { pilotRuns } from "../../../shared/db/schema/strategy";

export interface PilotRunDto {
  id: string;
  workspaceId: string;
  projectId: string;
  experimentId: string | null;
  status: PilotRunStatus;
  designPartnerEvidenceRefs: string[];
  metricContractArtifactRef: string | null;
  instrumentationArtifactRef: string | null;
  onboardingArtifactRef: string | null;
  supportEscalationArtifactRef: string | null;
  rollbackArtifactRef: string | null;
  releaseOwnerMemberId: string;
  approvedByMemberId: string | null;
  approvalRef: string | null;
  approvedAt: string | null;
  activatedByMemberId: string | null;
  activatedAt: string | null;
  completedAt: string | null;
  cancelledAt: string | null;
  cancellationReason: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
}

function toPilotRunDto(row: typeof pilotRuns.$inferSelect): PilotRunDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    experimentId: row.experimentId ? row.experimentId.toString() : null,
    status: row.status as PilotRunStatus,
    designPartnerEvidenceRefs: (row.designPartnerEvidenceRefs as string[]) || [],
    metricContractArtifactRef: row.metricContractArtifactRef ?? null,
    instrumentationArtifactRef: row.instrumentationArtifactRef ?? null,
    onboardingArtifactRef: row.onboardingArtifactRef ?? null,
    supportEscalationArtifactRef: row.supportEscalationArtifactRef ?? null,
    rollbackArtifactRef: row.rollbackArtifactRef ?? null,
    releaseOwnerMemberId: row.releaseOwnerMemberId.toString(),
    approvedByMemberId: row.approvedByMemberId ? row.approvedByMemberId.toString() : null,
    approvalRef: row.approvalRef ?? null,
    approvedAt: row.approvedAt ? row.approvedAt.toISOString() : null,
    activatedByMemberId: row.activatedByMemberId ? row.activatedByMemberId.toString() : null,
    activatedAt: row.activatedAt ? row.activatedAt.toISOString() : null,
    completedAt: row.completedAt ? row.completedAt.toISOString() : null,
    cancelledAt: row.cancelledAt ? row.cancelledAt.toISOString() : null,
    cancellationReason: row.cancellationReason ?? null,
    version: row.version,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export interface CreatePilotParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  experimentId?: string;
  designPartnerEvidenceRefs: string[];
  metricContractArtifactRef: string;
  instrumentationArtifactRef: string;
  onboardingArtifactRef: string;
  supportEscalationArtifactRef?: string;
  rollbackArtifactRef: string;
  releaseOwnerMemberId: string;
}

export interface ApprovePilotRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  approvalRef: string;
}

export interface ActivatePilotRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  approvalRef: string;
}

export interface ClosePilotRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  status: "COMPLETED" | "CANCELLED";
  cancellationReason?: string;
}

export interface ListPilotsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
}

export interface GetPilotParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export const createPilot = api(
  { method: "POST", path: "/operations/strategy/pilots", expose: true },
  async (params: CreatePilotParams): Promise<PilotRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    if (!params.releaseOwnerMemberId) {
      throw APIError.invalidArgument("releaseOwnerMemberId is required");
    }

    const row = await createPilotDraft({
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      experimentId: params.experimentId ? BigInt(params.experimentId) : undefined,
      designPartnerEvidenceRefs: params.designPartnerEvidenceRefs,
      metricContractArtifactRef: params.metricContractArtifactRef,
      instrumentationArtifactRef: params.instrumentationArtifactRef,
      onboardingArtifactRef: params.onboardingArtifactRef,
      supportEscalationArtifactRef: params.supportEscalationArtifactRef,
      rollbackArtifactRef: params.rollbackArtifactRef,
      releaseOwnerMemberId: BigInt(params.releaseOwnerMemberId),
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
    });

    return toPilotRunDto(row);
  }
);

export const approvePilot = api(
  { method: "POST", path: "/operations/strategy/pilots/:id/approve", expose: true },
  async (params: ApprovePilotRequestParams): Promise<PilotRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await approvePilotService({
      workspaceId: wsId,
      pilotId: BigInt(params.id),
      approvalRef: params.approvalRef,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toPilotRunDto(row);
  }
);

export const activatePilot = api(
  { method: "POST", path: "/operations/strategy/pilots/:id/activate", expose: true },
  async (params: ActivatePilotRequestParams): Promise<PilotRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await activatePilotService({
      workspaceId: wsId,
      pilotId: BigInt(params.id),
      approvalRef: params.approvalRef,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toPilotRunDto(row);
  }
);

export const closePilot = api(
  { method: "POST", path: "/operations/strategy/pilots/:id/close", expose: true },
  async (params: ClosePilotRequestParams): Promise<PilotRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await closePilotService({
      workspaceId: wsId,
      pilotId: BigInt(params.id),
      status: params.status,
      cancellationReason: params.cancellationReason,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toPilotRunDto(row);
  }
);

export const getPilot = api(
  { method: "GET", path: "/operations/strategy/pilots/:id", expose: true },
  async (params: GetPilotParams): Promise<PilotRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await getPilotInWorkspace(wsId, BigInt(params.id));
    return toPilotRunDto(row);
  }
);

export const listPilots = api(
  { method: "GET", path: "/operations/strategy/pilots", expose: true },
  async (params: ListPilotsParams): Promise<{ items: PilotRunDto[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const rows = await listPilotsInWorkspace(
      wsId,
      params.projectId ? BigInt(params.projectId) : undefined
    );
    return { items: rows.map(toPilotRunDto) };
  }
);
