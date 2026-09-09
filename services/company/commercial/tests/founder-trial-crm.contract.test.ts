import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createContactService } from "../services/contact.service";
import { createSalesLeadService } from "../services/lead.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { listProjectIdsForContact } from "../services/project-record-link.service";

function ctxOf(s: { workspaceId: string; userId: string }): TenantContext {
  return {
    workspaceId: s.workspaceId,
    userId: s.userId,
    membershipRole: "admin",
    permissions: [],
    correlationId: "test",
  };
}

async function makeProject(workspaceId: string): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title: "P" });
  return id.toString();
}

describe("Founder Trial CRM contract", () => {
  it("creating a contact with projectId links it in the same call", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    const contact = await createContactService(
      { workspaceId: s.workspaceId, name: "Ada", projectId },
      s.accessToken
    );

    expect(await listProjectIdsForContact(ctxOf(s), contact.id)).toEqual([projectId]);
  });

  it("creating a lead with a cross-workspace projectId is rejected", async () => {
    const s = await createTestSession();
    const other = await createTestSession();
    const foreignProject = await makeProject(other.workspaceId);

    await expect(
      createSalesLeadService(
        { workspaceId: s.workspaceId, name: "Deal", projectId: foreignProject },
        s.accessToken
      )
    ).rejects.toThrow();
  });

  it("creating a lead with an owned projectId persists project_id", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);
    const lead = await createSalesLeadService(
      { workspaceId: s.workspaceId, name: "Deal", projectId },
      s.accessToken
    );
    // toSalesLead doesn't surface projectId; assert on the row.
    const { salesLeads } = await import("../../shared/db/schema/commercial");
    const [row] = await db
      .select({ projectId: salesLeads.projectId })
      .from(salesLeads)
      .where(eq(salesLeads.id, BigInt(lead.id)));
    expect(row!.projectId!.toString()).toBe(projectId);
  });
});
