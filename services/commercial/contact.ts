import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface ContactRow {
  id: number;
  workspace_id: number;
  account_id: number | null;
  name: string;
  title: string | null;
  phone: string | null;
  email: string | null;
  source: string | null;
  consent_status: string | null;
  do_not_contact: boolean;
  owner_id: number | null;
  created_at: Date;
  updated_at: Date;
}

function rowToContact(row: ContactRow): Contact {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    accountId: row.account_id,
    name: row.name,
    title: row.title,
    phone: row.phone,
    email: row.email,
    source: row.source,
    consentStatus: row.consent_status,
    doNotContact: row.do_not_contact,
    ownerId: row.owner_id,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createContact = api(
  { method: "POST", path: "/commercial/contacts", expose: true },
  async (params: CreateContactParams): Promise<Contact> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<ContactRow>`
      INSERT INTO sales.contacts (workspace_id, account_id, name, title, phone, email, source, owner_id)
      VALUES (
        ${params.workspaceId}, ${params.accountId ?? null}, ${params.name}, ${params.title ?? null},
        ${params.phone ?? null}, ${params.email ?? null}, ${params.source ?? null}, ${params.ownerId ?? null}
      )
      RETURNING id, workspace_id, account_id, name, title, phone, email, source,
        consent_status, do_not_contact, owner_id, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create contact");
    return rowToContact(row);
  }
);

export const getContact = api(
  { method: "GET", path: "/commercial/contacts/:id", expose: true },
  async ({ id }: { id: number }): Promise<Contact> => {
    const row = await commercialDB.queryRow<ContactRow>`
      SELECT id, workspace_id, account_id, name, title, phone, email, source,
        consent_status, do_not_contact, owner_id, created_at, updated_at
      FROM sales.contacts WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`contact ${id} not found`);
    return rowToContact(row);
  }
);
