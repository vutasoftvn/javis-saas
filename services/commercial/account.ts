import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface AccountRow {
  id: number;
  workspace_id: number;
  name: string;
  domain: string | null;
  industry: string | null;
  size_segment: string | null;
  country: string | null;
  source: string | null;
  lifecycle_status: string;
  owner_id: number | null;
  tags: string[] | null;
  created_at: Date;
  updated_at: Date;
}

function rowToAccount(row: AccountRow): Account {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    name: row.name,
    domain: row.domain,
    industry: row.industry,
    sizeSegment: row.size_segment,
    country: row.country,
    source: row.source,
    lifecycleStatus: row.lifecycle_status,
    ownerId: row.owner_id,
    tags: row.tags,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createAccount = api(
  { method: "POST", path: "/commercial/accounts", expose: true },
  async (params: CreateAccountParams): Promise<Account> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<AccountRow>`
      INSERT INTO sales.accounts (
        workspace_id, name, domain, industry, size_segment, country, source, owner_id, tags
      )
      VALUES (
        ${params.workspaceId}, ${params.name}, ${params.domain ?? null}, ${params.industry ?? null},
        ${params.sizeSegment ?? null}, ${params.country ?? null}, ${params.source ?? null},
        ${params.ownerId ?? null}, ${params.tags ? JSON.stringify(params.tags) : null}
      )
      RETURNING id, workspace_id, name, domain, industry, size_segment, country, source,
        lifecycle_status, owner_id, tags, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create account");
    return rowToAccount(row);
  }
);

export const getAccount = api(
  { method: "GET", path: "/commercial/accounts/:id", expose: true },
  async ({ id }: { id: number }): Promise<Account> => {
    const row = await commercialDB.queryRow<AccountRow>`
      SELECT id, workspace_id, name, domain, industry, size_segment, country, source,
        lifecycle_status, owner_id, tags, created_at, updated_at
      FROM sales.accounts WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`account ${id} not found`);
    return rowToAccount(row);
  }
);
