import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  calculatePmfScoreboard,
  getPmfScoreboardRunInWorkspace,
  listPmfScoreboardRunsInWorkspace,
  PmfScoreboardResult,
  ScoreComponent,
  PmfScoreboardRunDto,
  toPmfScoreboardRunDto,
} from "../services/pmf-scoreboard.service";

export type { PmfScoreboardRunDto, PmfScoreboardResult, ScoreComponent };

export interface CalculatePmfScoreboardRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  contractVersionIds: string[];
  inputSnapshotIds: string[];
  reviewedEvidenceIds: string[];
  policyVersion?: string;
}

export interface GetPmfScoreboardRunParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface ListPmfScoreboardRunsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
}

export const calculatePmfScoreboardHandler = api(
  { method: "POST", path: "/operations/strategy/pmf-scoreboards/calculate", expose: true },
  async (params: CalculatePmfScoreboardRequestParams): Promise<PmfScoreboardRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await calculatePmfScoreboard({
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      contractVersionIds: params.contractVersionIds || [],
      inputSnapshotIds: params.inputSnapshotIds || [],
      reviewedEvidenceIds: params.reviewedEvidenceIds || [],
      policyVersion: params.policyVersion,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toPmfScoreboardRunDto(row);
  }
);

export const getPmfScoreboardRun = api(
  { method: "GET", path: "/operations/strategy/pmf-scoreboards/:id", expose: true },
  async (params: GetPmfScoreboardRunParams): Promise<PmfScoreboardRunDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await getPmfScoreboardRunInWorkspace(wsId, BigInt(params.id));
    return toPmfScoreboardRunDto(row);
  }
);

export const listPmfScoreboardRuns = api(
  { method: "GET", path: "/operations/strategy/pmf-scoreboards", expose: true },
  async (params: ListPmfScoreboardRunsParams): Promise<{ items: PmfScoreboardRunDto[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const rows = await listPmfScoreboardRunsInWorkspace(
      wsId,
      params.projectId ? BigInt(params.projectId) : undefined
    );

    return { items: rows.map(toPmfScoreboardRunDto) };
  }
);
