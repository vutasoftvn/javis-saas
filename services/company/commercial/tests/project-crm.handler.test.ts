import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  getProjectCrmSchema,
  createProjectLeadFieldDefinition,
  patchProjectLeadFieldDefinition,
  retireProjectLeadFieldDefinition,
  listProjectLeadSources,
  createProjectLeadSource,
  listProjectLeads,
  createProjectLead,
} from "../handlers/project-crm.handler";

async function makeProject(workspaceId: string, title = "Handler Test Proj"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title });
  return id.toString();
}

describe("project-crm.handler", () => {
  it("enforces schema authority: non-founder/admin is rejected for schema modifications", async () => {
    const s = await createTestSession({ role: "member" });
    const projectId = await makeProject(s.workspaceId);

    await expect(
      createProjectLeadFieldDefinition({
        projectId,
        workspaceId: s.workspaceId,
        authorization: `Bearer ${s.accessToken}`,
        stableKey: "custom_key",
        label: "Custom Key",
        dataType: "SHORT_TEXT",
      })
    ).rejects.toThrow(/Chỉ Founder hoặc Admin/);

    await expect(
      createProjectLeadSource({
        projectId,
        workspaceId: s.workspaceId,
        authorization: `Bearer ${s.accessToken}`,
        sourceType: "manual",
        label: "Manual Source",
      })
    ).rejects.toThrow(/Chỉ Founder hoặc Admin/);
  });

  it("prevents cross-tenant access", async () => {
    const s1 = await createTestSession({ role: "admin" });
    const s2 = await createTestSession({ role: "admin" });
    const p1 = await makeProject(s1.workspaceId);

    // s2 tries to access s1's project CRM schema
    await expect(
      getProjectCrmSchema({
        projectId: p1,
        workspaceId: s2.workspaceId,
        authorization: `Bearer ${s2.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("returns standard fields when custom schema is empty", async () => {
    const s = await createTestSession({ role: "admin" });
    const projectId = await makeProject(s.workspaceId);

    const schemaView = await getProjectCrmSchema({
      projectId,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
    });

    expect(schemaView.projectId).toBe(projectId);
    expect(schemaView.standardFields.length).toBeGreaterThan(0);
    expect(schemaView.customFields.length).toBe(0);
  });

  it("rejects collision with standard field keys", async () => {
    const s = await createTestSession({ role: "admin" });
    const projectId = await makeProject(s.workspaceId);

    await expect(
      createProjectLeadFieldDefinition({
        projectId,
        workspaceId: s.workspaceId,
        authorization: `Bearer ${s.accessToken}`,
        stableKey: "email", // standard field!
        label: "My Email",
        dataType: "SHORT_TEXT",
      })
    ).rejects.toThrow(/trùng với trường tiêu chuẩn/);
  });

  it("manages field lifecycle: create, patch, and retire with CAS version check", async () => {
    const s = await createTestSession({ role: "admin" });
    const projectId = await makeProject(s.workspaceId);

    const created = await createProjectLeadFieldDefinition({
      projectId,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
      stableKey: "customer_priority",
      label: "Customer Priority",
      dataType: "SINGLE_SELECT",
      allowedValues: [
        { key: "high", label: "High" },
        { key: "low", label: "Low" },
      ],
    });

    expect(created.version).toBe(1);
    expect(created.status).toBe("ACTIVE");

    // Patch label and allowedValues
    const patched = await patchProjectLeadFieldDefinition({
      projectId,
      fieldId: created.id,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
      label: "Priority Tier",
      allowedValues: [
        { key: "high", label: "High" },
        { key: "medium", label: "Medium" },
        { key: "low", label: "Low" },
      ],
    });
    expect(patched.label).toBe("Priority Tier");

    // Retire with wrong expected version throws conflict
    await expect(
      retireProjectLeadFieldDefinition({
        projectId,
        fieldId: created.id,
        workspaceId: s.workspaceId,
        authorization: `Bearer ${s.accessToken}`,
        expectedVersion: 999,
      })
    ).rejects.toThrow(/Version conflict/);

    // Retire with correct expected version succeeds
    const retired = await retireProjectLeadFieldDefinition({
      projectId,
      fieldId: created.id,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
      expectedVersion: 1,
    });
    expect(retired.status).toBe("RETIRED");
  });

  it("manages lead sources and creates project leads", async () => {
    const s = await createTestSession({ role: "admin" });
    const projectId = await makeProject(s.workspaceId);

    const source = await createProjectLeadSource({
      projectId,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
      sourceType: "manual",
      label: "Direct Outbound",
    });

    expect(source.sourceType).toBe("manual");

    const { sources } = await listProjectLeadSources({
      projectId,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
    });
    expect(sources.map((src) => src.id)).toContain(source.id);

    // Create lead
    const lead = await createProjectLead({
      projectId,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
      name: "Alice Founder",
      leadSourceId: source.id,
      company: "Wonderland Corp",
    });

    expect(lead.id).toBeDefined();
    expect(lead.leadSourceId).toBe(source.id);

    const { leads } = await listProjectLeads({
      projectId,
      workspaceId: s.workspaceId,
      authorization: `Bearer ${s.accessToken}`,
    });
    expect(leads.map((l) => l.id)).toContain(lead.id);
  });
});
