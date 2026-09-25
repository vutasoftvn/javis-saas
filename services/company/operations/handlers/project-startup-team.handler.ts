import { api, Header, APIError } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../../shared/auth/worker-service-auth";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  listProjectStartupTeam,
  activateProjectStartupTeamMember,
  pauseProjectStartupTeamMember,
  getProjectAgentRunAuthority,
  ProjectAgentRunAuthority,
} from "../services/project-startup-team.service";
import { ProjectStartupTeamMember } from "../../shared/contracts/startup-team-profiles.generated";



interface ListProjectStartupTeamParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export const listProjectStartupTeamApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/startup-team",
  },
  async (
    params: ListProjectStartupTeamParams
  ): Promise<{ items: ProjectStartupTeamMember[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const items = await listProjectStartupTeam({
      workspaceId: ctx.workspaceId,
      projectId: params.projectId,
      actorId: ctx.workforceMemberId ?? undefined,
    });
    return { items };
  }
);

interface ActivateProjectStartupTeamMemberParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  profileKey: string;
  expectedVersion: number;
  idempotencyKey?: string;
}

export const activateProjectStartupTeamMemberApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/startup-team/:profileKey/activate",
  },
  async (
    params: ActivateProjectStartupTeamMemberParams
  ): Promise<ProjectStartupTeamMember> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return activateProjectStartupTeamMember(
      ctx,
      params.projectId,
      params.profileKey,
      {
        expectedVersion: params.expectedVersion,
        idempotencyKey: params.idempotencyKey,
      }
    );
  }
);

interface PauseProjectStartupTeamMemberParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  profileKey: string;
  expectedVersion: number;
  reason?: string;
  idempotencyKey?: string;
}

export const pauseProjectStartupTeamMemberApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/startup-team/:profileKey/pause",
  },
  async (
    params: PauseProjectStartupTeamMemberParams
  ): Promise<ProjectStartupTeamMember> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return pauseProjectStartupTeamMember(
      ctx,
      params.projectId,
      params.profileKey,
      {
        expectedVersion: params.expectedVersion,
        reason: params.reason,
        idempotencyKey: params.idempotencyKey,
      }
    );
  }
);

interface GetProjectAgentRunAuthorityParams {
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  profileKey: string;
}

export const getProjectAgentRunAuthorityApi = api(
  {
    expose: true,
    method: "GET",
    path: "/internal/operations/projects/:projectId/startup-team/:profileKey/run-authority",
  },
  async (
    params: GetProjectAgentRunAuthorityParams
  ): Promise<ProjectAgentRunAuthority> => {
    await requireWorkerServiceAuth({
      serviceToken: params.serviceToken,
      authorization: params.authorization,
    });
    if (!params.workspaceId) {
      throw APIError.invalidArgument("X-Workspace-Id header is required");
    }
    return getProjectAgentRunAuthority(
      params.workspaceId,
      params.projectId,
      params.profileKey
    );
  }
);
