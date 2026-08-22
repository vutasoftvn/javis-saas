import { api, APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";

const { projects, portfolios } = schema;

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

    const [row] = await db
      .insert(projects)
      .values({
        workspaceId: BigInt(req.workspaceId),
        brainId: req.brainId ? BigInt(req.brainId) : null,
        title: req.title,
        description: req.description || null,
        phase: req.phase || "PLANNING",
        ownerId: req.ownerId ? BigInt(req.ownerId) : null,
        projectType: req.projectType || "STRATEGIC",
        strategicPriority: req.strategicPriority || "P1",
        portfolioId: req.portfolioId ? BigInt(req.portfolioId) : null,
        startDate: req.startDate ? new Date(req.startDate) : null,
        endDate: req.endDate ? new Date(req.endDate) : null,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create project");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      brainId: row.brainId ? Number(row.brainId) : null,
      title: row.title,
      description: row.description,
      phase: row.phase,
      status: row.status,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      projectType: row.projectType,
      strategicPriority: row.strategicPriority,
      portfolioId: row.portfolioId ? Number(row.portfolioId) : null,
      startDate: row.startDate ? row.startDate.toISOString() : null,
      endDate: row.endDate ? row.endDate.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const listProjects = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/projects" },
  async (params: { workspaceId: number }): Promise<{ projects: Project[] }> => {
    const rows = await db
      .select()
      .from(projects)
      .where(eq(projects.workspaceId, BigInt(params.workspaceId)))
      .orderBy(desc(projects.id));

    return {
      projects: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        brainId: row.brainId ? Number(row.brainId) : null,
        title: row.title,
        description: row.description,
        phase: row.phase,
        status: row.status,
        ownerId: row.ownerId ? Number(row.ownerId) : null,
        projectType: row.projectType,
        strategicPriority: row.strategicPriority,
        portfolioId: row.portfolioId ? Number(row.portfolioId) : null,
        startDate: row.startDate ? row.startDate.toISOString() : null,
        endDate: row.endDate ? row.endDate.toISOString() : null,
        createdAt: row.createdAt.toISOString(),
      })),
    };
  }
);

// ─── Portfolios Endpoints ───

export const createPortfolio = api(
  { expose: true, method: "POST", path: "/operations/portfolios" },
  async (req: CreatePortfolioRequest): Promise<Portfolio> => {
    if (!req.workspaceId || !req.name) {
      throw APIError.invalidArgument("workspaceId and name are required");
    }

    const [row] = await db
      .insert(portfolios)
      .values({
        workspaceId: BigInt(req.workspaceId),
        name: req.name,
        description: req.description || null,
        strategicFocus: req.strategicFocus || null,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create portfolio");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      name: row.name,
      description: row.description,
      strategicFocus: row.strategicFocus,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listPortfolios = api(
  { expose: true, method: "GET", path: "/operations/workspaces/:workspaceId/portfolios" },
  async (params: { workspaceId: number }): Promise<{ portfolios: Portfolio[] }> => {
    const rows = await db
      .select()
      .from(portfolios)
      .where(eq(portfolios.workspaceId, BigInt(params.workspaceId)))
      .orderBy(desc(portfolios.id));

    return {
      portfolios: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        name: row.name,
        description: row.description,
        strategicFocus: row.strategicFocus,
        status: row.status,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);
