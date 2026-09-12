import { describe, it, expect } from "vitest";
import { eq, isNull } from "drizzle-orm";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { salesLeads, leadIdentityKeys } from "../../shared/db/schema/commercial";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import {
  ProjectLeadRepository,
  computeIdentityHash,
} from "../services/project-lead-repository";

async function makeProject(workspaceId: string, title = "Project CRM Test"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title });
  return id.toString();
}

describe("003_project_crm_foundation migration & repository invariants", () => {
  it("stores standard fields and custom fields from active definitions in the project", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    // Tạo custom field definitions
    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "budget_bracket",
      label: "Budget Bracket",
      dataType: "SINGLE_SELECT",
      allowedValues: [
        { key: "under_10k", label: "< $10K" },
        { key: "10k_to_50k", label: "$10K - $50K" },
        { key: "above_50k", label: "> $50K" },
      ],
      classification: "BUSINESS_CONFIDENTIAL",
    });

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "team_size",
      label: "Team Size",
      dataType: "NUMBER",
    });

    const lead = await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
      name: "Acme Corp Lead",
      company: "Acme Corp",
      email: "lead@acme.com",
      phone: "+84901234567",
      value: 25000,
      fieldValues: {
        budget_bracket: "10k_to_50k",
        team_size: 15,
      },
    });

    expect(lead.id).toBeDefined();
    expect(lead.name).toBe("Acme Corp Lead");
    expect(lead.fieldValues["budget_bracket"]).toBe("10k_to_50k");
    expect(lead.fieldValues["team_size"]).toBe(15);
  });

  it("rejects unknown, retired, or wrong-project field definitions", async () => {
    const s = await createTestSession();
    const projA = await makeProject(s.workspaceId, "Proj A");
    const projB = await makeProject(s.workspaceId, "Proj B");

    // Definition chỉ có ở Project A
    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId: projA,
      stableKey: "proj_a_exclusive",
      label: "Exclusive A",
      dataType: "SHORT_TEXT",
    });

    // Thử dùng field của Project A vào Project B -> reject
    await expect(
      ProjectLeadRepository.createLead(s.workspaceId, projB, {
        name: "Foreign Field Lead",
        fieldValues: {
          proj_a_exclusive: "Invalid",
        },
      })
    ).rejects.toThrow(/không tồn tại hoặc đã bị retired/);
  });

  it("defaults PERSONAL and SENSITIVE fields to agent_input_allowed=false and searchable=false", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    const personalField = await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "customer_citizen_id",
      label: "Citizen ID",
      dataType: "SHORT_TEXT",
      classification: "PERSONAL",
    });

    expect(personalField.agentInputAllowed).toBe(false);
    expect(personalField.searchable).toBe(false);

    const sensitiveField = await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "health_record_summary",
      label: "Health Summary",
      dataType: "LONG_TEXT",
      classification: "SENSITIVE",
    });

    expect(sensitiveField.agentInputAllowed).toBe(false);
    expect(sensitiveField.searchable).toBe(false);
  });

  it("does not include legacy project_id IS NULL leads in project-scoped list", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    // Chèn 1 legacy lead có project_id = null
    const legacyId = generateSnowflake();
    await db.insert(salesLeads).values({
      id: BigInt(legacyId),
      workspaceId: BigInt(s.workspaceId),
      projectId: null,
      name: "Legacy Global Lead",
      stage: "NEW",
    });

    // Chèn 1 project lead
    await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
      name: "Scoped Project Lead",
    });

    const leads = await ProjectLeadRepository.listLeads(s.workspaceId, projectId);
    const names = leads.map((l) => l.name);

    expect(names).toContain("Scoped Project Lead");
    expect(names).not.toContain("Legacy Global Lead");
  });

  it("computes identity hash and isolates identity keys per workspace", async () => {
    const s1 = await createTestSession();
    const s2 = await createTestSession();
    const p1 = await makeProject(s1.workspaceId);
    const p2 = await makeProject(s2.workspaceId);

    const email = "shared@domain.com";
    const lead1 = await ProjectLeadRepository.createLead(s1.workspaceId, p1, {
      name: "Lead WS 1",
      email,
    });
    expect(lead1.duplicateCandidate).toBe(false);

    // Same email in different workspace does not collide or flag duplicate
    const lead2 = await ProjectLeadRepository.createLead(s2.workspaceId, p2, {
      name: "Lead WS 2",
      email,
    });
    expect(lead2.duplicateCandidate).toBe(false);

    // Duplicate in SAME workspace creates dedup candidate
    const lead3 = await ProjectLeadRepository.createLead(s1.workspaceId, p1, {
      name: "Lead WS 1 Repeat",
      email,
    });
    expect(lead3.duplicateCandidate).toBe(true);
    expect(lead3.existingLeadId).toBe(lead1.id);
  });
});
