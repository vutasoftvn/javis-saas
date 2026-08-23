import { api } from "encore.dev/api";
import {
  Project,
  CreateProjectRequest,
  Portfolio,
  CreatePortfolioRequest,
  createProjectService,
  getProjectService,
  listProjectsService,
  createPortfolioService,
  listPortfoliosService,
} from "../services/project.service";

export { Project, CreateProjectRequest, Portfolio, CreatePortfolioRequest };

// ─── Projects Endpoints ───

export const createProject = api(
  { expose: true, method: "POST", path: "/operations/projects" },
  async (req: CreateProjectRequest): Promise<Project> => {
    return createProjectService(req);
  }
);

export const getProject = api(
  { expose: true, method: "GET", path: "/operations/projects/:id" },
  async (params: { id: number }): Promise<Project> => {
    return getProjectService(params.id);
  }
);

export const listProjects = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/projects" },
  async (params: { workspaceId: number }): Promise<{ projects: Project[] }> => {
    const projects = await listProjectsService(params.workspaceId);
    return { projects };
  }
);

// ─── Portfolios Endpoints ───

export const createPortfolio = api(
  { expose: true, method: "POST", path: "/operations/portfolios" },
  async (req: CreatePortfolioRequest): Promise<Portfolio> => {
    return createPortfolioService(req);
  }
);

export const listPortfolios = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/portfolios" },
  async (params: { workspaceId: number }): Promise<{ portfolios: Portfolio[] }> => {
    const portfolios = await listPortfoliosService(params.workspaceId);
    return { portfolios };
  }
);
