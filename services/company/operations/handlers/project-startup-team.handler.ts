import { api, Header, APIError } from "encore.dev/api";
import jwt from "jsonwebtoken";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  listProjectStartupTeam,
  activateProjectStartupTeamMember,
  pauseProjectStartupTeamMember,
  getProjectAgentRunAuthority,
  ProjectAgentRunAuthority,
} from "../services/project-startup-team.service";
import { ProjectStartupTeamMember } from "../../shared/contracts/startup-team-profiles.generated";

const DEV_WORKER_JWT_SECRET = "cosa-worker-service-jwt-key-change-in-prod-min32chars";

function requireWorkerServiceToken(
  serviceTokenHeader?: string,
  authorizationHeader?: string
): void {
  const token =
    serviceTokenHeader ||
    (authorizationHeader ? authorizationHeader.replace(/^Bearer\s+/i, "") : "");
  if (!token) {
    throw APIError.unauthenticated("missing service token");
  }
  const sharedExpected =
    process.env.COSA_WORKER_SERVICE_TOKEN ?? "dev-worker-service-token";
  if (token === sharedExpected) return;

  const secret =
    process.env.WORKER_SERVICE_JWT_SECRET ||
    DEV_WORKER_JWT_SECRET;
  try {
    const payload = jwt.verify(token, secret, { audience: "control_plane" }) as {
      role?: string;
      aud?: string;
    };
    if (payload.role === "worker_service" && payload.aud === "control_plane") return;
  } catch {
    // fall through
  }
  throw APIError.unauthenticated("invalid or missing service token");
}

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
    requireWorkerServiceToken(params.serviceToken, params.authorization);
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
