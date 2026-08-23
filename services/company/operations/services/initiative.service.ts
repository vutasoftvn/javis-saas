import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { initiatives } = schema;

export interface Initiative {
  id: string;
  workspaceId: string;
  projectId: string | null;
  title: string;
  status: string;
  ownerId: string | null;
  createdAt: string;
}

export interface CreateInitiativeParams {
  workspaceId: string | number;
  title: string;
  ownerId?: string | number;
}

function toInitiative(row: typeof initiatives.$inferSelect): Initiative {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId ? row.projectId.toString() : null,
    title: row.title,
    status: row.status,
    ownerId: row.ownerId ? row.ownerId.toString() : null,
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
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      title: params.title,
      ownerId: params.ownerId ? BigInt(params.ownerId) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create initiative");
  return toInitiative(row);
}

export async function getInitiativeService(id: string | number, authorization: string | undefined): Promise<Initiative> {
  const [row] = await db
    .select()
    .from(initiatives)
    .where(eq(initiatives.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`initiative ${id} not found`);
  await requireWorkspaceAccess(authorization, row.workspaceId);
  return toInitiative(row);
}
