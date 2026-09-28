import { api, Header, APIError } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../../shared/auth/worker-service-auth";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getProjectDeploymentAuthority,
  ProjectDeploymentAuthority,
  deployAgentToProject,
  ProjectAgentDeploymentDto,
  createWorkspaceAgent,
  WorkspaceAgentDto,
  WORKSPACE_CLONE_ORIGIN,
} from "../services/founder-asset-deployment.service";



interface GetProjectDeploymentAuthorityParams {
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  workspaceAgentId: string;
}

interface GetProjectDeploymentAuthorityByDeploymentParams {
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  projectAgentDeploymentId: string;
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
    const claims = await requireWorkerServiceAuth({
      serviceToken: params.serviceToken,
      authorization: params.authorization,
    });
    if (!params.workspaceId) {
      throw APIError.invalidArgument("X-Workspace-Id header is required");
    }

    const tenantCtx = {
      workspaceId: params.workspaceId,
      userId: claims.sub,
      membershipRole: "worker_service",
      permissions: ["*"],
      correlationId: `auth-${Date.now()}`,
    };

    return getProjectDeploymentAuthority(tenantCtx, {
      projectId: params.projectId,
      workspaceAgentId: params.workspaceAgentId,
    });
  }
);

interface DeployAgentToProjectParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  workspaceAgentId: string;
  capabilityOverrides?: any[];
  idempotencyKey?: string;
}

/**
 * Founder deploy một Workspace Agent hiện hữu vào Project (2026-09-14).
 * Đây là lệnh public DUY NHẤT phía Project cho Executive Board — Role thuộc
 * Workspace, Project chỉ deploy Agent với scope/policy hẹp (không có Role bind
 * theo Project). Không gửi `roleKey`, không gửi spec hash do client tự chọn:
 * server resolve Workspace Agent và pin config của nó.
 */
export const deployAgentToProjectApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/agent-deployments",
  },
  async (
    params: DeployAgentToProjectParams
  ): Promise<ProjectAgentDeploymentDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    if (!params.workspaceAgentId) {
      throw APIError.invalidArgument("workspaceAgentId is required");
    }
    return await deployAgentToProject(ctx, {
      projectId: params.projectId,
      workspaceAgentId: params.workspaceAgentId,
      capabilityOverrides: params.capabilityOverrides,
      reason: "Deploy workspace agent to project",
      idempotencyKey: params.idempotencyKey,
    });
  }
);

export const getProjectDeploymentAuthorityByDeploymentApi = api(
  {
    expose: true,
    method: "GET",
    path: "/internal/operations/projects/:projectId/agent-deployments/:projectAgentDeploymentId/deployment-authority",
  },
  async (
    params: GetProjectDeploymentAuthorityByDeploymentParams
  ): Promise<ProjectDeploymentAuthority> => {
    const claims = await requireWorkerServiceAuth({
      serviceToken: params.serviceToken,
      authorization: params.authorization,
    });
    if (!params.workspaceId) {
      throw APIError.invalidArgument("X-Workspace-Id header is required");
    }
    return getProjectDeploymentAuthority(
      {
        workspaceId: params.workspaceId,
        userId: claims.sub,
        membershipRole: "worker_service",
        permissions: ["*"],
        correlationId: `auth-${Date.now()}`,
      },
      {
        projectId: params.projectId,
        projectAgentDeploymentId: params.projectAgentDeploymentId,
      }
    );
  }
);

interface CreateWorkspaceCloneAgentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  agentAssetId: string;
  agentAssetVersion: string;
  agentDefinitionHash: string;
  idempotencyKey?: string;
}

/**
 * Founder tạo Workspace Agent từ agent clone ĐÃ PUBLISH (C1). Server đòi biên nhận publish khớp
 * tuyệt đối và tự tạo AI member riêng — client không chọn member, không chọn grant.
 * Bước kế tiếp: POST /operations/projects/:projectId/agent-deployments.
 */
export const createWorkspaceCloneAgentApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/founder/assets/workspace-agents",
  },
  async (params: CreateWorkspaceCloneAgentParams): Promise<WorkspaceAgentDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await createWorkspaceAgent(ctx, {
      agentAssetId: params.agentAssetId,
      agentAssetVersion: params.agentAssetVersion,
      agentDefinitionHash: params.agentDefinitionHash,
      originKind: WORKSPACE_CLONE_ORIGIN,
      reason: "Create workspace agent from published clone",
      idempotencyKey: params.idempotencyKey,
    });
  }
);
