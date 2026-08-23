import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { accounts } = schema;

export interface Account {
  id: string;
  workspaceId: string;
  name: string;
  domain: string | null;
  industry: string | null;
  sizeSegment: string | null;
  country: string | null;
  source: string | null;
  lifecycleStatus: string;
  ownerMemberId: string | null;
  tags: string[] | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAccountParams {
  workspaceId: string;
  name: string;
  domain?: string;
  industry?: string;
  sizeSegment?: string;
  country?: string;
  source?: string;
  ownerMemberId?: string;
  tags?: string[];
}

function toAccount(row: typeof accounts.$inferSelect): Account {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    name: row.name,
    domain: row.domain,
    industry: row.industry,
    sizeSegment: row.sizeSegment,
    country: row.country,
    source: row.source,
    lifecycleStatus: row.lifecycleStatus,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
    tags: row.tags as string[] | null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createAccountService(
  params: CreateAccountParams,
  authorization: string | undefined
): Promise<Account> {
  await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(accounts)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(params.workspaceId)),
      name: params.name,
      domain: params.domain || null,
      industry: params.industry || null,
      sizeSegment: params.sizeSegment || null,
      country: params.country || null,
      source: params.source || null,
      ownerMemberId: params.ownerMemberId ? BigInt(String(params.ownerMemberId)) : null,
      tags: params.tags || null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create account");
  return toAccount(row);
}

export async function getAccountService(id: string, authorization: string | undefined): Promise<Account> {
  const [row] = await db
    .select()
    .from(accounts)
    .where(eq(accounts.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`account ${id} not found`);
  await requireWorkspaceAccess(authorization, String(row.workspaceId));
  return toAccount(row);
}
