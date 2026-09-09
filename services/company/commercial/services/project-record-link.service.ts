import { APIError } from "encore.dev/api";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { contacts, salesLeads, contactProjects } = schema;

// Founder Trial R1 — Node B/C: liên kết typed per-entity giữa record commercial
// và project. KHÔNG polymorphic; mỗi cặp có FK thật + workspace guard.

/** Xác nhận project thuộc workspace của caller (cùng Postgres DB, khác schema). */
async function assertProjectInWorkspace(ctx: TenantContext, projectId: string | number): Promise<void> {
  const [row] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(
      and(
        eq(projects.id, BigInt(projectId)),
        eq(projects.workspaceId, BigInt(ctx.workspaceId)),
        isNull(projects.deletedAt)
      )
    )
    .limit(1);
  if (!row) throw APIError.notFound("Project không tồn tại trong workspace này");
}

async function assertContactInWorkspace(ctx: TenantContext, contactId: string | number): Promise<void> {
  const [row] = await db
    .select({ id: contacts.id })
    .from(contacts)
    .where(
      and(
        eq(contacts.id, BigInt(contactId)),
        eq(contacts.workspaceId, BigInt(ctx.workspaceId)),
        isNull(contacts.deletedAt)
      )
    )
    .limit(1);
  if (!row) throw APIError.notFound("Contact không tồn tại trong workspace này");
}

export async function linkContactToProject(
  ctx: TenantContext,
  contactId: string,
  projectId: string
): Promise<void> {
  await assertContactInWorkspace(ctx, contactId);
  await assertProjectInWorkspace(ctx, projectId);
  await db
    .insert(contactProjects)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      contactId: BigInt(contactId),
      projectId: BigInt(projectId),
      linkedByMemberId: ctx.userId ? BigInt(ctx.userId) : null,
      createdAt: new Date(),
    })
    .onConflictDoNothing();
}

export async function unlinkContactFromProject(
  ctx: TenantContext,
  contactId: string,
  projectId: string
): Promise<void> {
  await db
    .delete(contactProjects)
    .where(
      and(
        eq(contactProjects.workspaceId, BigInt(ctx.workspaceId)),
        eq(contactProjects.contactId, BigInt(contactId)),
        eq(contactProjects.projectId, BigInt(projectId))
      )
    );
}

export async function listContactIdsByProject(
  ctx: TenantContext,
  projectId: string
): Promise<string[]> {
  const rows = await db
    .select({ contactId: contactProjects.contactId })
    .from(contactProjects)
    .where(
      and(
        eq(contactProjects.workspaceId, BigInt(ctx.workspaceId)),
        eq(contactProjects.projectId, BigInt(projectId))
      )
    );
  return rows.map((r) => r.contactId.toString());
}

export async function listProjectIdsForContact(
  ctx: TenantContext,
  contactId: string
): Promise<string[]> {
  const rows = await db
    .select({ projectId: contactProjects.projectId })
    .from(contactProjects)
    .where(
      and(
        eq(contactProjects.workspaceId, BigInt(ctx.workspaceId)),
        eq(contactProjects.contactId, BigInt(contactId))
      )
    );
  return rows.map((r) => r.projectId.toString());
}

/** Gán lead vào tối đa 1 project (cột project_id nullable). */
export async function setLeadProject(
  ctx: TenantContext,
  leadId: string,
  projectId: string | null
): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const [lead] = await db
    .select({ id: salesLeads.id })
    .from(salesLeads)
    .where(and(eq(salesLeads.id, BigInt(leadId)), eq(salesLeads.workspaceId, wsId), isNull(salesLeads.deletedAt)))
    .limit(1);
  if (!lead) throw APIError.notFound("Lead không tồn tại trong workspace này");

  if (projectId != null) {
    await assertProjectInWorkspace(ctx, projectId);
  }

  await db
    .update(salesLeads)
    .set({ projectId: projectId != null ? BigInt(projectId) : null, updatedAt: new Date() })
    .where(and(eq(salesLeads.id, BigInt(leadId)), eq(salesLeads.workspaceId, wsId)));
}

// Re-export cho consumer khác nếu cần một helper project-guard chung.
export { assertProjectInWorkspace as assertCommercialProjectInWorkspace };
