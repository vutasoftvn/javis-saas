import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { contacts } = schema;

export interface Contact {
  id: string;
  workspaceId: string;
  accountId: string | null;
  name: string;
  title: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  consentStatus: string | null;
  doNotContact: boolean;
  ownerMemberId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateContactParams {
  workspaceId: string;
  name: string;
  accountId?: string;
  title?: string;
  phone?: string;
  email?: string;
  source?: string;
  ownerMemberId?: string;
}

function toContact(row: typeof contacts.$inferSelect): Contact {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: row.accountId ? String(row.accountId) : null,
    name: row.name,
    title: row.title,
    phone: row.phone,
    email: row.email,
    source: row.source,
    consentStatus: row.consentStatus,
    doNotContact: row.doNotContact,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createContactService(
  params: CreateContactParams,
  authorization: string | undefined
): Promise<Contact> {
  await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(contacts)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(params.workspaceId)),
      accountId: params.accountId ? BigInt(String(params.accountId)) : null,
      name: params.name,
      title: params.title || null,
      phone: params.phone || null,
      email: params.email || null,
      source: params.source || null,
      ownerMemberId: params.ownerMemberId ? BigInt(String(params.ownerMemberId)) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create contact");
  return toContact(row);
}

export async function getContactService(id: string, ctx: TenantContext): Promise<Contact> {
  const [row] = await db
    .select()
    .from(contacts)
    .where(and(eq(contacts.id, BigInt(id)), eq(contacts.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`contact ${id} not found`);
  return toContact(row);
}

