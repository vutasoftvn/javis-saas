import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  Project,
  CreateProjectRequest,
  createProjectService,
  getProjectService,
  listProjectsService,
} from "../services/project.service";

export { Project, CreateProjectRequest };

export interface CreateProjectParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  title: string;
  description?: string | null;
  lifecycleStage?: string | null;
  ownerMemberId?: string | number | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: string | number | null;
  startDate?: string | null;
  endDate?: string | null;
}

export interface GetProjectParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export interface ListProjectsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

// ─── Projects Endpoints ───

export const createProject = api(
  { expose: true, method: "POST", path: "/operations/projects" },
  async (params: CreateProjectParams): Promise<Project> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createProjectService(ctx, {
      title: params.title,
      description: params.description,
      lifecycleStage: params.lifecycleStage,
      ownerMemberId: params.ownerMemberId,
      projectType: params.projectType,
      strategicPriority: params.strategicPriority,
      portfolioId: params.portfolioId,
      startDate: params.startDate,
      endDate: params.endDate,
    });
  }
);

export const getProject = api(
  { expose: true, method: "GET", path: "/operations/projects/:id" },
  async (params: GetProjectParams): Promise<Project> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getProjectService(ctx, params.id);
  }
);

export const listProjects = api(
  { expose: true, method: "GET", path: "/operations/projects" },
  async (params: ListProjectsParams): Promise<{ projects: Project[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const projects = await listProjectsService(ctx);
    return { projects };
  }
);
