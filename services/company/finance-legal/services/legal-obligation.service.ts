import { APIError } from "encore.dev/api";
import { eq, and, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { legalObligations } = schema;

export interface LegalObligation {
  id: string;
  workspaceId: string;
  title: string;
  description: string | null;
  dueAt: string | null;
  status: string;
  createdAt: string;
}

export interface CreateObligationParams {
  workspaceId: string;
  title: string;
  description?: string;
  dueAt?: string;
}

function toObligation(row: typeof legalObligations.$inferSelect): LegalObligation {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    title: row.title,
    description: row.description,
    dueAt: row.dueAt ? row.dueAt.toISOString() : null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createObligationService(
  params: CreateObligationParams,
  authorization: string | undefined
): Promise<LegalObligation> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(legalObligations)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
      description: params.description || null,
      dueAt: params.dueAt ? new Date(params.dueAt) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create obligation");
  return toObligation(row);
}

export async function getObligationService(
  id: string,
  ctx: TenantContext
): Promise<LegalObligation> {
  const [row] = await db
    .select()
    .from(legalObligations)
    .where(and(eq(legalObligations.id, BigInt(id)), eq(legalObligations.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`obligation ${id} not found`);
  return toObligation(row);
}

export async function fulfillObligationService(
  id: string,
  ctx: TenantContext
): Promise<LegalObligation> {
  const [row] = await db
    .update(legalObligations)
    .set({ status: "FULFILLED" })
    .where(and(eq(legalObligations.id, BigInt(id)), eq(legalObligations.workspaceId, BigInt(ctx.workspaceId))))
    .returning();

  if (!row) throw APIError.notFound(`obligation ${id} not found`);
  return toObligation(row);
}

const { legalObligationInstances } = schema;

export interface LegalObligationInstanceView {
  id: string;
  workspaceId: string;
  legalEntityProfileId: string | null;
  templateId: string | null;
  regulationVersionId: string | null;
  source: "REGULATION_TEMPLATE" | "USER_CREATED" | "AI_PROPOSAL";
  title: string;
  dueDate: string | null;
  status: string;
  evidenceArtifactId: string | null;
  reviewStatus: string;
  createdAt: string;
  updatedAt: string;
}

export async function listObligationInstancesService(
  workspaceId: bigint,
  status?: string
): Promise<LegalObligationInstanceView[]> {
  const rows = await db
    .select()
    .from(legalObligationInstances)
    .where(eq(legalObligationInstances.workspaceId, workspaceId));

  let filtered = rows;
  if (status) {
    filtered = rows.filter((r) => r.status.toLowerCase() === status.toLowerCase());
  }

  return filtered.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    legalEntityProfileId: r.legalEntityProfileId ? String(r.legalEntityProfileId) : null,
    templateId: r.templateId ? String(r.templateId) : null,
    regulationVersionId: r.regulationVersionId ? String(r.regulationVersionId) : null,
    source: r.source as any,
    title: r.title,
    dueDate: r.dueDate ? String(r.dueDate) : null,
    status: r.status,
    evidenceArtifactId: r.evidenceArtifactId ? String(r.evidenceArtifactId) : null,
    reviewStatus: r.reviewStatus,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

export interface OpenObligationView extends LegalObligationInstanceView {
  isOverdue: boolean;
  overdueDays: number;
}

export async function listOpenObligations(
  ctx: { workspaceId: string },
  params?: {
    projectId?: bigint;
    legalEntityId?: bigint;
    at?: string;
  }
): Promise<OpenObligationView[]> {
  const wsId = BigInt(ctx.workspaceId);
  const atDate = params?.at ? new Date(params.at) : new Date();

  const conditions = [
    eq(legalObligationInstances.workspaceId, wsId),
    inArray(legalObligationInstances.status, ["OPEN", "IN_PROGRESS", "PENDING"]),
  ];

  if (params?.legalEntityId) {
    conditions.push(eq(legalObligationInstances.legalEntityProfileId, params.legalEntityId));
  }

  const rows = await db
    .select()
    .from(legalObligationInstances)
    .where(and(...conditions));

  return rows.map((r) => {
    let isOverdue = false;
    let overdueDays = 0;
    if (r.dueDate) {
      const dueTime = new Date(r.dueDate).getTime();
      const diffMs = atDate.getTime() - dueTime;
      if (diffMs > 0) {
        isOverdue = true;
        overdueDays = Math.floor(diffMs / (24 * 60 * 60 * 1000));
      }
    }

    return {
      id: String(r.id),
      workspaceId: String(r.workspaceId),
      legalEntityProfileId: r.legalEntityProfileId ? String(r.legalEntityProfileId) : null,
      templateId: r.templateId ? String(r.templateId) : null,
      regulationVersionId: r.regulationVersionId ? String(r.regulationVersionId) : null,
      source: r.source as any,
      title: r.title,
      dueDate: r.dueDate ? String(r.dueDate) : null,
      status: r.status === "PENDING" ? "OPEN" : r.status,
      evidenceArtifactId: r.evidenceArtifactId ? String(r.evidenceArtifactId) : null,
      reviewStatus: r.reviewStatus,
      isOverdue,
      overdueDays,
      createdAt: r.createdAt.toISOString(),
      updatedAt: r.updatedAt.toISOString(),
    };
  });
}

export async function createObligationInstanceService(p: {
  workspaceId: bigint;
  templateId?: bigint;
  regulationVersionId?: bigint;
  source: "REGULATION_TEMPLATE" | "USER_CREATED" | "AI_PROPOSAL";
  title: string;
  dueDate?: string;
  evidenceArtifactId?: bigint;
  ownerMemberId?: bigint;
}): Promise<LegalObligationInstanceView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(legalObligationInstances)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      templateId: p.templateId ?? null,
      regulationVersionId: p.regulationVersionId ?? null,
      source: p.source,
      title: p.title,
      dueDate: p.dueDate ? (p.dueDate as any) : null,
      evidenceArtifactId: p.evidenceArtifactId ?? null,
      ownerMemberId: p.ownerMemberId ?? null,
      status: "OPEN",
      reviewStatus: p.source === "AI_PROPOSAL" ? "PENDING_REVIEW" : "ACCEPTED",
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    legalEntityProfileId: created.legalEntityProfileId ? String(created.legalEntityProfileId) : null,
    templateId: created.templateId ? String(created.templateId) : null,
    regulationVersionId: created.regulationVersionId ? String(created.regulationVersionId) : null,
    source: created.source as any,
    title: created.title,
    dueDate: created.dueDate ? String(created.dueDate) : null,
    status: created.status,
    evidenceArtifactId: created.evidenceArtifactId ? String(created.evidenceArtifactId) : null,
    reviewStatus: created.reviewStatus,
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}


