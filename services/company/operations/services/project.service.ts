import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { projects, portfolios } = schema;

export interface Project {
  id: string;
  workspaceId: string;
  title: string;
  description?: string | null;
  phase?: string | null;
  status: string;
  ownerMemberId?: string | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
}

export interface CreateProjectRequest {
  workspaceId: string | number;
  title: string;
  description?: string | null;
  phase?: string | null;
  ownerMemberId?: string | number | null;
  projectType?: string | null;
  strategicPriority?: string | null;
  portfolioId?: string | number | null;
  startDate?: string | null;
  endDate?: string | null;
}

export interface Portfolio {
  id: string;
  workspaceId: string;
  name: string;
  description?: string | null;
  strategicFocus?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreatePortfolioRequest {
  workspaceId: string | number;
  name: string;
  description?: string | null;
  strategicFocus?: string | null;
}

function toProject(row: typeof projects.$inferSelect): Project {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    description: row.description,
    phase: row.phase,
    status: row.status,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    projectType: row.projectType,
    strategicPriority: row.strategicPriority,
    portfolioId: row.portfolioId ? row.portfolioId.toString() : null,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

function toPortfolio(row: typeof portfolios.$inferSelect): Portfolio {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    name: row.name,
    description: row.description,
    strategicFocus: row.strategicFocus,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createProjectService(req: CreateProjectRequest): Promise<Project> {
  if (!req.workspaceId || !req.title) {
    throw APIError.invalidArgument("workspaceId and title are required");
  }

  const [row] = await db
    .insert(projects)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      title: req.title,
      description: req.description || null,
      phase: req.phase || "PLANNING",
      ownerMemberId: req.ownerMemberId ? BigInt(req.ownerMemberId) : null,
      projectType: req.projectType || "STRATEGIC",
      strategicPriority: req.strategicPriority || "P1",
      portfolioId: req.portfolioId ? BigInt(req.portfolioId) : null,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create project");
  return toProject(row);
}

export async function getProjectService(id: string | number): Promise<Project> {
  const [row] = await db.select().from(projects).where(eq(projects.id, BigInt(id)));
  if (!row) throw APIError.notFound(`Project not found: ${id}`);
  return toProject(row);
}

export async function listProjectsService(workspaceId: string | number): Promise<Project[]> {
  const rows = await db
    .select()
    .from(projects)
    .where(eq(projects.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(projects.id));

  return rows.map(toProject);
}

export async function createPortfolioService(req: CreatePortfolioRequest): Promise<Portfolio> {
  if (!req.workspaceId || !req.name) {
    throw APIError.invalidArgument("workspaceId and name are required");
  }

  const [row] = await db
    .insert(portfolios)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      name: req.name,
      description: req.description || null,
      strategicFocus: req.strategicFocus || null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create portfolio");
  return toPortfolio(row);
}

export async function listPortfoliosService(workspaceId: string | number): Promise<Portfolio[]> {
  const rows = await db
    .select()
    .from(portfolios)
    .where(eq(portfolios.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(portfolios.id));

  return rows.map(toPortfolio);
}
