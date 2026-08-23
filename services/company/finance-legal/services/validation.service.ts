import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { validationHypotheses, validationExperiments, evidenceItems } = schema;

export interface ValidationHypothesis {
  id: string;
  workspaceId: string;
  projectId?: string | null;
  title: string;
  statement: string;
  confidenceScore: number;
  status: string;
  createdAt: string;
}

export interface CreateHypothesisRequest {
  workspaceId: string | number;
  projectId?: string | number | null;
  title: string;
  statement: string;
  confidenceScore?: number;
}

export interface ValidationExperiment {
  id: string;
  workspaceId: string;
  hypothesisId: string;
  experimentType: string;
  title: string;
  status: string;
  startDate?: string | null;
  endDate?: string | null;
  createdAt: string;
}

export interface CreateExperimentRequest {
  workspaceId: string | number;
  hypothesisId: string | number;
  experimentType?: string;
  title: string;
  startDate?: string | null;
  endDate?: string | null;
}

export interface EvidenceItem {
  id: string;
  workspaceId: string;
  experimentId: string;
  evidenceType: string;
  title: string;
  content: string;
  strengthScore: number;
  createdAt: string;
}

export interface CreateEvidenceItemRequest {
  workspaceId: string | number;
  experimentId: string | number;
  evidenceType?: string;
  title: string;
  content: string;
  strengthScore?: number;
}

export async function createHypothesisService(
  req: CreateHypothesisRequest,
  authorization: string | undefined
): Promise<ValidationHypothesis> {
  if (!req.workspaceId || !req.title || !req.statement) {
    throw APIError.invalidArgument("workspaceId, title, and statement are required");
  }
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(validationHypotheses)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      projectId: req.projectId ? BigInt(req.projectId) : null,
      title: req.title,
      statement: req.statement,
      confidenceScore: req.confidenceScore ?? 0.5,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create validation hypothesis");
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: row.projectId ? String(row.projectId) : null,
    title: row.title,
    statement: row.statement,
    confidenceScore: row.confidenceScore,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function listHypothesesService(
  workspaceId: string | number,
  authorization: string | undefined
): Promise<ValidationHypothesis[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(validationHypotheses)
    .where(eq(validationHypotheses.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(validationHypotheses.id));

  return rows.map((row) => ({
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: row.projectId ? String(row.projectId) : null,
    title: row.title,
    statement: row.statement,
    confidenceScore: row.confidenceScore,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  }));
}

export async function createExperimentService(
  req: CreateExperimentRequest,
  authorization: string | undefined
): Promise<ValidationExperiment> {
  if (!req.workspaceId || !req.hypothesisId || !req.title) {
    throw APIError.invalidArgument("workspaceId, hypothesisId, and title are required");
  }
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(validationExperiments)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      hypothesisId: BigInt(req.hypothesisId),
      experimentType: req.experimentType || "INTERVIEW",
      title: req.title,
      startDate: req.startDate ? new Date(req.startDate) : null,
      endDate: req.endDate ? new Date(req.endDate) : null,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create validation experiment");
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    hypothesisId: String(row.hypothesisId),
    experimentType: row.experimentType,
    title: row.title,
    status: row.status,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createEvidenceService(
  req: CreateEvidenceItemRequest,
  authorization: string | undefined
): Promise<EvidenceItem> {
  if (!req.workspaceId || !req.experimentId || !req.title || !req.content) {
    throw APIError.invalidArgument("workspaceId, experimentId, title, and content are required");
  }
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(evidenceItems)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      experimentId: BigInt(req.experimentId),
      evidenceType: req.evidenceType || "QUOTE",
      title: req.title,
      content: req.content,
      strengthScore: req.strengthScore ?? 1.0,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create evidence item");
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    experimentId: String(row.experimentId),
    evidenceType: row.evidenceType,
    title: row.title,
    content: row.content,
    strengthScore: row.strengthScore,
    createdAt: row.createdAt.toISOString(),
  };
}
