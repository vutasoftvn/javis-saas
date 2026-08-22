import { api, APIError } from "encore.dev/api";
import { SQLDatabase } from "encore.dev/storage/sqldb";

const db = SQLDatabase.named("operations");

export interface Project {
  id: number;
  workspaceId: number;
  brainId?: number | null;
  title: string;
  description?: string | null;
  phase?: string | null;
  status: string;
  ownerId?: number | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: number | null;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
}

export interface CreateProjectRequest {
  workspaceId: number;
  brainId?: number | null;
  title: string;
  description?: string | null;
  phase?: string | null;
  ownerId?: number | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: number | null;
  startDate?: string | null;
  endDate?: string | null;
}

export interface Portfolio {
  id: number;
  workspaceId: number;
  name: string;
  description?: string | null;
  strategicFocus?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreatePortfolioRequest {
  workspaceId: number;
  name: string;
  description?: string | null;
  strategicFocus?: string | null;
}

// ─── Projects Endpoints ───

export const createProject = api(
  { expose: true, method: "POST", path: "/operations/projects" },
  async (req: CreateProjectRequest): Promise<Project> => {
    if (!req.workspaceId || !req.title) {
      throw APIError.invalidArgument("workspaceId and title are required");
    }

    const row = await db.queryRow<Project>`
      INSERT INTO strategy.projects (
        workspace_id, brain_id, title, description, phase,
        owner_id, project_type, strategic_priority, portfolio_id,
        start_date, end_date
      ) VALUES (
        ${req.workspaceId}, ${req.brainId ?? null}, ${req.title},
        ${req.description ?? null}, ${req.phase ?? "PLANNING"},
        ${req.ownerId ?? null}, ${req.projectType ?? "STRATEGIC"},
        ${req.strategicPriority ?? "P1"}, ${req.portfolioId ?? null},
        ${req.startDate ?? null}, ${req.endDate ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", brain_id as "brainId",
        title, description, phase, status,
        owner_id as "ownerId", project_type as "projectType",
        strategic_priority as "strategicPriority", portfolio_id as "portfolioId",
        start_date as "startDate", end_date as "endDate", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create project");
    return row;
  }
);

export const listProjects = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/projects" },
  async (params: { workspaceId: number }): Promise<{ projects: Project[] }> => {
    const rows = db.query<Project>`
      SELECT
        id, workspace_id as "workspaceId", brain_id as "brainId",
        title, description, phase, status,
        owner_id as "ownerId", project_type as "projectType",
        strategic_priority as "strategicPriority", portfolio_id as "portfolioId",
        start_date as "startDate", end_date as "endDate", created_at as "createdAt"
      FROM strategy.projects
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY id DESC
    `;
    const projects: Project[] = [];
    for await (const row of rows) projects.push(row);
    return { projects };
  }
);

// ─── Portfolios Endpoints ───

export const createPortfolio = api(
  { expose: true, method: "POST", path: "/operations/portfolios" },
  async (req: CreatePortfolioRequest): Promise<Portfolio> => {
    if (!req.workspaceId || !req.name) {
      throw APIError.invalidArgument("workspaceId and name are required");
    }

    const row = await db.queryRow<Portfolio>`
      INSERT INTO strategy.portfolios (
        workspace_id, name, description, strategic_focus
      ) VALUES (
        ${req.workspaceId}, ${req.name}, ${req.description ?? null},
        ${req.strategicFocus ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", name, description,
        strategic_focus as "strategicFocus", status,
        created_at as "createdAt", updated_at as "updatedAt"
    `;
    if (!row) throw APIError.internal("Failed to create portfolio");
    return row;
  }
);

export const listPortfolios = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/portfolios" },
  async (params: { workspaceId: number }): Promise<{ portfolios: Portfolio[] }> => {
    const rows = db.query<Portfolio>`
      SELECT
        id, workspace_id as "workspaceId", name, description,
        strategic_focus as "strategicFocus", status,
        created_at as "createdAt", updated_at as "updatedAt"
      FROM strategy.portfolios
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY id DESC
    `;
    const portfolios: Portfolio[] = [];
    for await (const row of rows) portfolios.push(row);
    return { portfolios };
  }
);
