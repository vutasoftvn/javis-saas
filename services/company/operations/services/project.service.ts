import { APIError } from "encore.dev/api";
import { eq, desc, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { projects, portfolios } = schema;

export interface Project {
  id: string;
  workspaceId: string;
  title: string;
  description?: string | null;
  lifecycleStage: string;
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
    lifecycleStage: row.lifecycleStage,
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

export async function createProjectService(ctx: TenantContext, req: CreateProjectRequest): Promise<Project> {
  if (!req.title) {
    throw APIError.invalidArgument("title is required");
  }

  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .insert(projects)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      title: req.title,
      description: req.description || null,
      // M4 §3 — default P0_DISCOVERY (không phải "PLANNING"); Project stage độc lập Workspace.
      lifecycleStage: req.lifecycleStage || "P0_DISCOVERY",
      stageEnteredAt: new Date(),
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

export async function getProjectService(ctx: TenantContext, id: string | number): Promise<Project> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, BigInt(id)), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!row) throw APIError.notFound("Project not found");
  return toProject(row);
}

export async function listProjectsService(ctx: TenantContext): Promise<Project[]> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(projects)
    .where(eq(projects.workspaceId, wsId))
    .orderBy(desc(projects.id));

  return rows.map(toProject);
}

export async function createPortfolioService(ctx: TenantContext, req: CreatePortfolioRequest): Promise<Portfolio> {
  if (!req.name) {
    throw APIError.invalidArgument("name is required");
  }

  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .insert(portfolios)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      name: req.name,
      description: req.description || null,
      strategicFocus: req.strategicFocus || null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create portfolio");
  return toPortfolio(row);
}

export async function listPortfoliosService(ctx: TenantContext): Promise<Portfolio[]> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(portfolios)
    .where(eq(portfolios.workspaceId, wsId))
    .orderBy(desc(portfolios.id));

  return rows.map(toPortfolio);
}
