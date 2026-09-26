import { APIError } from "encore.dev/api";
import { eq, and, desc, type SQL } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspaceRecord } from "../../identity/services/workspace.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { CRM_LIST_LIMIT } from "./account.service";
import { linkContactToProject } from "./project-record-link.service";

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
  /** Founder Trial R1 — gắn contact vào project qua typed link (sales.contact_projects). */
  projectId?: string;
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
  const ctx = await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspaceRecord(String(params.workspaceId));

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

  // Founder Trial R1 — Node B: nếu request gắn projectId thì tạo link typed
  // ngay (project được xác thực thuộc workspace trong link service).
  if (params.projectId) {
    await linkContactToProject(ctx, row.id.toString(), String(params.projectId));
  }

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

export async function listContactsService(
  workspaceId: string, authorization: string | undefined, filters: { accountId?: string } = {}
): Promise<Contact[]> {
  await requireWorkspaceAccess(authorization, String(workspaceId));
  const conditions: SQL[] = [eq(contacts.workspaceId, BigInt(workspaceId))];
  if (filters.accountId) conditions.push(eq(contacts.accountId, BigInt(filters.accountId)));
  const rows = await db
    .select()
    .from(contacts)
    .where(and(...conditions))
    .orderBy(desc(contacts.createdAt))
    .limit(CRM_LIST_LIMIT);
  return rows.map(toContact);
}
