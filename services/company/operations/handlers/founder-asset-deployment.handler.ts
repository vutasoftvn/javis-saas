import { api, Header, APIError } from "encore.dev/api";
import jwt from "jsonwebtoken";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getProjectDeploymentAuthority,
  ProjectDeploymentAuthority,
} from "../services/founder-asset-deployment.service";

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
    process.env.PLATFORM_JWT_SECRET ||
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

interface GetProjectDeploymentAuthorityParams {
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  workspaceAgentId: string;
}

export const getProjectDeploymentAuthorityApi = api(
  {
    expose: true,
    method: "GET",
    path: "/internal/operations/projects/:projectId/agents/:workspaceAgentId/deployment-authority",
  },
  async (
    params: GetProjectDeploymentAuthorityParams
  ): Promise<ProjectDeploymentAuthority> => {
    requireWorkerServiceToken(params.serviceToken, params.authorization);
    if (!params.workspaceId) {
      throw APIError.invalidArgument("X-Workspace-Id header is required");
    }

    const tenantCtx = {
      workspaceId: params.workspaceId,
      userId: "0",
      membershipRole: "system",
      permissions: ["*"],
      correlationId: `auth-${Date.now()}`,
    };

    return getProjectDeploymentAuthority(tenantCtx, {
      projectId: params.projectId,
      workspaceAgentId: params.workspaceAgentId,
    });
  }
);
