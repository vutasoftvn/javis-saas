import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

const { initiatives } = schema;

export interface Initiative {
  id: number;
  workspaceId: number;
  brainId: number | null;
  projectId: number | null;
  offeringId: number | null;
  title: string;
  status: string;
  ownerId: number | null;
  createdAt: string;
}

export interface CreateInitiativeParams {
  workspaceId: number;
  title: string;
  ownerId?: number;
}

function toInitiative(row: typeof initiatives.$inferSelect): Initiative {
  return {
    id: Number(row.id),
    workspaceId: Number(row.workspaceId),
    brainId: row.brainId ? Number(row.brainId) : null,
    projectId: row.projectId ? Number(row.projectId) : null,
    offeringId: row.offeringId ? Number(row.offeringId) : null,
    title: row.title,
    status: row.status,
    ownerId: row.ownerId ? Number(row.ownerId) : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createInitiativeService(
  params: CreateInitiativeParams,
  authorization: string | undefined
): Promise<Initiative> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const [row] = await db
    .insert(initiatives)
    .values({
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
      ownerId: params.ownerId ? BigInt(params.ownerId) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create initiative");
  return toInitiative(row);
}

export async function getInitiativeService(id: number, authorization: string | undefined): Promise<Initiative> {
  const [row] = await db
    .select()
    .from(initiatives)
    .where(eq(initiatives.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`initiative ${id} not found`);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toInitiative(row);
}
