import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

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
  ownerId: string | null;
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
  ownerId?: string;
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
    ownerId: row.ownerId ? String(row.ownerId) : null,
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
      ownerId: params.ownerId ? BigInt(String(params.ownerId)) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create contact");
  return toContact(row);
}

export async function getContactService(id: string, authorization: string | undefined): Promise<Contact> {
  const [row] = await db
    .select()
    .from(contacts)
    .where(eq(contacts.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`contact ${id} not found`);
  await requireWorkspaceAccess(authorization, String(row.workspaceId));
  return toContact(row);
}
