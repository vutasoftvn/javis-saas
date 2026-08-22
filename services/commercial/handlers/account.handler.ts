import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { accounts } = schema;

export interface Account {
  id: number;
  workspaceId: number;
  name: string;
  domain: string | null;
  industry: string | null;
  sizeSegment: string | null;
  country: string | null;
  source: string | null;
  lifecycleStatus: string;
  ownerId: number | null;
  tags: string[] | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAccountParams {
  workspaceId: number;
  name: string;
  domain?: string;
  industry?: string;
  sizeSegment?: string;
  country?: string;
  source?: string;
  ownerId?: number;
  tags?: string[];
}

export const createAccount = api(
  { method: "POST", path: "/commercial/accounts", expose: true },
  async (params: CreateAccountParams): Promise<Account> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(accounts)
      .values({
        workspaceId: BigInt(params.workspaceId),
        name: params.name,
        domain: params.domain || null,
        industry: params.industry || null,
        sizeSegment: params.sizeSegment || null,
        country: params.country || null,
        source: params.source || null,
        ownerId: params.ownerId ? BigInt(params.ownerId) : null,
        tags: params.tags || null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create account");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      name: row.name,
      domain: row.domain,
      industry: row.industry,
      sizeSegment: row.sizeSegment,
      country: row.country,
      source: row.source,
      lifecycleStatus: row.lifecycleStatus,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      tags: row.tags as string[] | null,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getAccount = api(
  { method: "GET", path: "/commercial/accounts/:id", expose: true },
  async ({ id }: { id: number }): Promise<Account> => {
    const [row] = await db
      .select()
      .from(accounts)
      .where(eq(accounts.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`account ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      name: row.name,
      domain: row.domain,
      industry: row.industry,
      sizeSegment: row.sizeSegment,
      country: row.country,
      source: row.source,
      lifecycleStatus: row.lifecycleStatus,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      tags: row.tags as string[] | null,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);
