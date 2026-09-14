import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess, requireFounderCommand } from "../../shared/auth/workspace-access";
import {
  listFounderAssetLibrary,
  getProjectFounderDeployments,
  deployFounderAssetToProject,
  startWorkflowRun,
  getProjectAgentTimeline,
  type FounderAssetLibraryItemDto,
  type ProjectFounderDeploymentsView,
  type DeployFounderAssetToProjectInput,
  type StartWorkflowRunInput,
  type FounderWorkflowRunResult,
  type FounderTimelineEntryDto,
} from "../services/founder-asset-query.service";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
import type { ProjectRoleDeploymentDto, ProjectAgentDeploymentDto, ProjectWorkflowBindingDto } from "../services/founder-asset-deployment.service";

// Task 12 — 4 route đọc/lệnh cho Founder asset surface còn thiếu wiring (chỉ
// service tồn tại, chưa có handler). Cùng auth gate với
// `founder-asset-authoring.handler.ts::getFounderAssetEventsApi`
// (`requireFounderCommand`) — thư viện/timeline/deployment của asset thuộc
// quyền quản trị Founder, không phải dữ liệu công khai cho mọi member.

export interface ListFounderAssetLibraryParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const listFounderAssetLibraryApi = api(
  { expose: true, method: "GET", path: "/operations/founder-assets" },
  async (
    params: ListFounderAssetLibraryParams
  ): Promise<MvpSuccess<readonly FounderAssetLibraryItemDto[]>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "list_founder_asset_library");
    return listFounderAssetLibrary(tenantCtx);
  }
);

export interface GetProjectFounderDeploymentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export const getProjectFounderDeploymentsApi = api(
  { expose: true, method: "GET", path: "/operations/projects/:projectId/founder-deployments" },
  async (
    params: GetProjectFounderDeploymentsParams
  ): Promise<MvpSuccess<ProjectFounderDeploymentsView>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "get_project_founder_deployments");
    return getProjectFounderDeployments(tenantCtx, params.projectId);
  }
);

export interface DeployFounderAssetToProjectParams extends DeployFounderAssetToProjectInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

// Encore.ts static app-graph parser bắt buộc kiểu trả về của `api()` là một
// named interface — không chấp nhận union type trực tiếp
// (`ProjectRoleDeploymentDto | ProjectAgentDeploymentDto | ProjectWorkflowBindingDto`)
// dù `deployFounderAssetToProject()` (service layer, không phải boundary
// Encore) trả union đó. Bọc lại bằng discriminant `kind` khớp
// `input.kind` — client tự biết field nào có mặt.
export interface DeployFounderAssetToProjectResponse {
  kind: "ROLE" | "AGENT" | "WORKFLOW";
  role?: ProjectRoleDeploymentDto;
  agent?: ProjectAgentDeploymentDto;
  workflow?: ProjectWorkflowBindingDto;
}

export const deployFounderAssetToProjectApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/founder-deployments" },
  async (
    params: DeployFounderAssetToProjectParams
  ): Promise<DeployFounderAssetToProjectResponse> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "deploy_founder_asset_to_project");
    const result = await deployFounderAssetToProject(tenantCtx, params.projectId, params);
    switch (params.kind) {
      case "ROLE":
        return { kind: "ROLE", role: result as ProjectRoleDeploymentDto };
      case "AGENT":
        return { kind: "AGENT", agent: result as ProjectAgentDeploymentDto };
      case "WORKFLOW":
        return { kind: "WORKFLOW", workflow: result as ProjectWorkflowBindingDto };
    }
  }
);

export interface StartWorkflowRunParams extends Omit<StartWorkflowRunInput, "projectId" | "bindingId"> {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  bindingId: string;
}

export const startWorkflowRunApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/workflow-bindings/:bindingId/runs",
  },
  async (params: StartWorkflowRunParams): Promise<FounderWorkflowRunResult> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "start_workflow_run");
    return startWorkflowRun(tenantCtx, {
      projectId: params.projectId,
      bindingId: params.bindingId,
      reason: params.reason,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

export interface GetProjectAgentTimelineParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export const getProjectAgentTimelineApi = api(
  { expose: true, method: "GET", path: "/operations/projects/:projectId/agent-timeline" },
  async (
    params: GetProjectAgentTimelineParams
  ): Promise<MvpSuccess<readonly FounderTimelineEntryDto[]>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "get_project_agent_timeline");
    return getProjectAgentTimeline(tenantCtx, params.projectId);
  }
);
