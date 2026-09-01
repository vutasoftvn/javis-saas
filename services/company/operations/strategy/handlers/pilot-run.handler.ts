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
  PilotRunDto,
  toPilotRunDto,
} from "../services/pilot-run.service";

export type { PilotRunDto };

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
