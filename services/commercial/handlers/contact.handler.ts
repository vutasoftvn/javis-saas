import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { contacts } = schema;

export interface Contact {
  id: number;
  workspaceId: number;
  accountId: number | null;
  name: string;
  title: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  consentStatus: string | null;
  doNotContact: boolean;
  ownerId: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateContactParams {
  workspaceId: number;
  name: string;
  accountId?: number;
  title?: string;
  phone?: string;
  email?: string;
  source?: string;
  ownerId?: number;
}

export const createContact = api(
  { method: "POST", path: "/commercial/contacts", expose: true },
  async (params: CreateContactParams): Promise<Contact> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(contacts)
      .values({
        workspaceId: BigInt(params.workspaceId),
        accountId: params.accountId ? BigInt(params.accountId) : null,
        name: params.name,
        title: params.title || null,
        phone: params.phone || null,
        email: params.email || null,
        source: params.source || null,
        ownerId: params.ownerId ? BigInt(params.ownerId) : null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create contact");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      accountId: row.accountId ? Number(row.accountId) : null,
      name: row.name,
      title: row.title,
      phone: row.phone,
      email: row.email,
      source: row.source,
      consentStatus: row.consentStatus,
      doNotContact: row.doNotContact,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getContact = api(
  { method: "GET", path: "/commercial/contacts/:id", expose: true },
  async ({ id }: { id: number }): Promise<Contact> => {
    const [row] = await db
      .select()
      .from(contacts)
      .where(eq(contacts.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`contact ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      accountId: row.accountId ? Number(row.accountId) : null,
      name: row.name,
      title: row.title,
      phone: row.phone,
      email: row.email,
      source: row.source,
      consentStatus: row.consentStatus,
      doNotContact: row.doNotContact,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);
