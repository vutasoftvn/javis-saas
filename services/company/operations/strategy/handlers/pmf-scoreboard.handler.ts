import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  calculatePmfScoreboard,
  getPmfScoreboardRunInWorkspace,
  listPmfScoreboardRunsInWorkspace,
  PmfScoreboardResult,
  ScoreComponent,
} from "../services/pmf-scoreboard.service";
import { pmfScoreboardRuns } from "../../../shared/db/schema/strategy";

export interface PmfScoreboardRunDto {
  id: string;
  workspaceId: string;
  projectId: string;
  contractVersionIds: string[];
  inputSnapshotIds: string[];
  reviewedEvidenceIds: string[];
  policyVersion: string;
  scoreComponents: ScoreComponent[];
  missingDataFlags: string[];
  reliabilityFlags: string[];
  calculationHash: string;
  result: PmfScoreboardResult;
  humanReviewState: Record<string, any>;
  calculatedAt: string;
  createdAt: string;
}

function toPmfScoreboardRunDto(row: typeof pmfScoreboardRuns.$inferSelect): PmfScoreboardRunDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    contractVersionIds: (row.contractVersionIds as string[]) || [],
    inputSnapshotIds: (row.inputSnapshotIds as string[]) || [],
    reviewedEvidenceIds: (row.reviewedEvidenceIds as string[]) || [],
    policyVersion: row.policyVersion,
    scoreComponents: (row.scoreComponents as ScoreComponent[]) || [],
    missingDataFlags: (row.missingDataFlags as string[]) || [],
    reliabilityFlags: (row.reliabilityFlags as string[]) || [],
    calculationHash: row.calculationHash,
    result: row.result as PmfScoreboardResult,
    humanReviewState: (row.humanReviewState as Record<string, any>) || {},
    calculatedAt: row.calculatedAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
  };
}

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
