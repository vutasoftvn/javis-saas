import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { legalObligations } = schema;

export interface LegalObligation {
  id: number;
  workspaceId: number;
  title: string;
  description: string | null;
  dueAt: string | null;
  status: string;
  createdAt: string;
}

export interface CreateObligationParams {
  workspaceId: number;
  title: string;
  description?: string;
  dueAt?: string;
}

export const createObligation = api(
  { method: "POST", path: "/finance-legal/obligations", expose: true },
  async (params: CreateObligationParams): Promise<LegalObligation> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(legalObligations)
      .values({
        workspaceId: BigInt(params.workspaceId),
        title: params.title,
        description: params.description || null,
        dueAt: params.dueAt ? new Date(params.dueAt) : null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create obligation");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      description: row.description,
      dueAt: row.dueAt ? row.dueAt.toISOString() : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getObligation = api(
  { method: "GET", path: "/finance-legal/obligations/:id", expose: true },
  async ({ id }: { id: number }): Promise<LegalObligation> => {
    const [row] = await db
      .select()
      .from(legalObligations)
      .where(eq(legalObligations.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`obligation ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      description: row.description,
      dueAt: row.dueAt ? row.dueAt.toISOString() : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const fulfillObligation = api(
  { method: "POST", path: "/finance-legal/obligations/:id/fulfill", expose: true },
  async ({ id }: { id: number }): Promise<LegalObligation> => {
    const [row] = await db
      .update(legalObligations)
      .set({ status: "FULFILLED" })
      .where(eq(legalObligations.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`obligation ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      title: row.title,
      description: row.description,
      dueAt: row.dueAt ? row.dueAt.toISOString() : null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
