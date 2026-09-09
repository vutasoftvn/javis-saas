import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { salesLeads } from "../../shared/db/schema/commercial";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { TenantContext } from "../../shared/types/tenant_context";
import { createContactService } from "../services/contact.service";
import { createSalesLeadService } from "../services/lead.service";
import {
  linkContactToProject,
  unlinkContactFromProject,
  listContactIdsByProject,
  listProjectIdsForContact,
  setLeadProject,
} from "../services/project-record-link.service";

function ctxOf(s: { workspaceId: string; userId: string }): TenantContext {
  return {
    workspaceId: s.workspaceId,
    userId: s.userId,
    membershipRole: "admin",
    permissions: [],
    correlationId: "test",
  };
}

async function makeProject(workspaceId: string, title = "P"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title });
  return id.toString();
}

describe("project-record-link.service (typed per-entity links)", () => {
  it("links an owned contact to an owned project and lists both directions", async () => {
    const s = await createTestSession();
    const ctx = ctxOf(s);
    const projectId = await makeProject(s.workspaceId);
    const contact = await createContactService(
      { workspaceId: s.workspaceId, name: "Ada" },
      s.accessToken
    );

    await linkContactToProject(ctx, contact.id, projectId);

    expect(await listContactIdsByProject(ctx, projectId)).toEqual([contact.id]);
    expect(await listProjectIdsForContact(ctx, contact.id)).toEqual([projectId]);
  });

  it("is idempotent on a duplicate link", async () => {
    const s = await createTestSession();
    const ctx = ctxOf(s);
    const projectId = await makeProject(s.workspaceId);
    const contact = await createContactService(
      { workspaceId: s.workspaceId, name: "Grace" },
      s.accessToken
    );
    await linkContactToProject(ctx, contact.id, projectId);
    await linkContactToProject(ctx, contact.id, projectId);
    expect(await listContactIdsByProject(ctx, projectId)).toHaveLength(1);
  });

  it("rejects a project from another workspace", async () => {
    const s = await createTestSession();
    const other = await createTestSession();
    const ctx = ctxOf(s);
    const foreignProject = await makeProject(other.workspaceId);
    const contact = await createContactService(
      { workspaceId: s.workspaceId, name: "Lin" },
      s.accessToken
    );
    await expect(linkContactToProject(ctx, contact.id, foreignProject)).rejects.toThrow();
  });

  it("rejects a contact from another workspace", async () => {
    const s = await createTestSession();
    const other = await createTestSession();
    const ctx = ctxOf(s);
    const projectId = await makeProject(s.workspaceId);
    const foreignContact = await createContactService(
      { workspaceId: other.workspaceId, name: "Kay" },
      other.accessToken
    );
    await expect(linkContactToProject(ctx, foreignContact.id, projectId)).rejects.toThrow();
  });

  it("unlink removes the pair", async () => {
    const s = await createTestSession();
    const ctx = ctxOf(s);
    const projectId = await makeProject(s.workspaceId);
    const contact = await createContactService(
      { workspaceId: s.workspaceId, name: "Mae" },
      s.accessToken
    );
    await linkContactToProject(ctx, contact.id, projectId);
    await unlinkContactFromProject(ctx, contact.id, projectId);
    expect(await listContactIdsByProject(ctx, projectId)).toEqual([]);
  });

  it("setLeadProject persists and rejects a cross-workspace project", async () => {
    const s = await createTestSession();
    const other = await createTestSession();
    const ctx = ctxOf(s);
    const projectId = await makeProject(s.workspaceId);
    const foreignProject = await makeProject(other.workspaceId);
    const lead = await createSalesLeadService(
      { workspaceId: s.workspaceId, name: "Deal 1" },
      s.accessToken
    );

    await setLeadProject(ctx, lead.id, projectId);
    const [row] = await db
      .select({ projectId: salesLeads.projectId })
      .from(salesLeads)
      .where(eq(salesLeads.id, BigInt(lead.id)));
    expect(row!.projectId!.toString()).toBe(projectId);

    await expect(setLeadProject(ctx, lead.id, foreignProject)).rejects.toThrow();

    await setLeadProject(ctx, lead.id, null);
    const [cleared] = await db
      .select({ projectId: salesLeads.projectId })
      .from(salesLeads)
      .where(eq(salesLeads.id, BigInt(lead.id)));
    expect(cleared!.projectId).toBeNull();
  });
});
