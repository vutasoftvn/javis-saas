import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  assessMaturity,
  getMaturityAssessmentInWorkspace,
  listMaturityAssessmentsInWorkspace,
  MaturityDimensions,
  MaturityAssessmentDto,
  toMaturityAssessmentDto,
} from "../services/maturity-assessment.service";

export type { MaturityAssessmentDto, MaturityDimensions };

export interface AssessMaturityRequestParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  scoreboardRunId?: string;
}

export interface GetMaturityAssessmentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface ListMaturityAssessmentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string;
}

export const assessMaturityHandler = api(
  { method: "POST", path: "/operations/strategy/maturity-assessments", expose: true },
  async (params: AssessMaturityRequestParams): Promise<MaturityAssessmentDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await assessMaturity({
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      scoreboardRunId: params.scoreboardRunId ? BigInt(params.scoreboardRunId) : undefined,
      actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
      actorRole: ctx.membershipRole,
    });

    return toMaturityAssessmentDto(row);
  }
);

export const getMaturityAssessment = api(
  { method: "GET", path: "/operations/strategy/maturity-assessments/:id", expose: true },
  async (params: GetMaturityAssessmentParams): Promise<MaturityAssessmentDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const row = await getMaturityAssessmentInWorkspace(wsId, BigInt(params.id));
    return toMaturityAssessmentDto(row);
  }
);

export const listMaturityAssessments = api(
  { method: "GET", path: "/operations/strategy/maturity-assessments", expose: true },
  async (params: ListMaturityAssessmentsParams): Promise<{ items: MaturityAssessmentDto[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const rows = await listMaturityAssessmentsInWorkspace(
      wsId,
      params.projectId ? BigInt(params.projectId) : undefined
    );

    return { items: rows.map(toMaturityAssessmentDto) };
  }
);
