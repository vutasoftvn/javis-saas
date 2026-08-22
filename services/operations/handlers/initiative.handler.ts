import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

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

export const createInitiative = api(
  { method: "POST", path: "/operations/initiatives", expose: true },
  async (params: CreateInitiativeParams): Promise<Initiative> => {
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
);

export const getInitiative = api(
  { method: "GET", path: "/operations/initiatives/:id", expose: true },
  async ({ id }: { id: number }): Promise<Initiative> => {
    const [row] = await db
      .select()
      .from(initiatives)
      .where(eq(initiatives.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`initiative ${id} not found`);
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
);
