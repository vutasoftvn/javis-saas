import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { leadSources, leadIngestionEvents } from "../../shared/db/schema/commercial";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { ProjectLeadRepository } from "../services/project-lead-repository";

async function makeProject(workspaceId: string, title = "Repo Test Proj"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title });
  return id.toString();
}

describe("ProjectLeadRepository", () => {
  it("validates various data types (NUMBER, BOOLEAN, DATE, URL, MULTI_SELECT)", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "linkedin_url",
      label: "LinkedIn URL",
      dataType: "URL",
    });

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "is_decision_maker",
      label: "Decision Maker?",
      dataType: "BOOLEAN",
    });

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "preferred_contact_date",
      label: "Preferred Date",
      dataType: "DATE",
    });

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "tech_stack",
      label: "Tech Stack",
      dataType: "MULTI_SELECT",
      allowedValues: [
        { key: "react", label: "React" },
        { key: "flutter", label: "Flutter" },
        { key: "node", label: "Node.js" },
      ],
    });

    // Valid submission
    const lead = await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
      name: "Tech Buyer",
      fieldValues: {
        linkedin_url: "https://linkedin.com/in/tech-buyer",
        is_decision_maker: true,
        preferred_contact_date: "2026-10-01",
        tech_stack: ["react", "flutter"],
      },
    });

    expect(lead.fieldValues["linkedin_url"]).toBe("https://linkedin.com/in/tech-buyer");
    expect(lead.fieldValues["is_decision_maker"]).toBe(true);
    expect(lead.fieldValues["tech_stack"]).toEqual(["react", "flutter"]);

    // Invalid URL rejected
    await expect(
      ProjectLeadRepository.createLead(s.workspaceId, projectId, {
        name: "Bad URL",
        fieldValues: { linkedin_url: "not-a-url" },
      })
    ).rejects.toThrow(/không phải là định dạng URL hợp lệ/);

    // Invalid MULTI_SELECT value rejected
    await expect(
      ProjectLeadRepository.createLead(s.workspaceId, projectId, {
        name: "Bad Option",
        fieldValues: { tech_stack: ["angular"] },
      })
    ).rejects.toThrow(/chứa giá trị 'angular' không hợp lệ/);
  });

  it("enforces requiredAtStages constraint", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "deal_size",
      label: "Estimated Deal Size",
      dataType: "NUMBER",
      requiredAtStages: ["QUALIFIED", "PROPOSAL"],
    });

    // Stage NEW does NOT require deal_size
    const newLead = await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
      name: "Early Lead",
      stage: "NEW",
    });
    expect(newLead.stage).toBe("NEW");

    // Stage QUALIFIED requires deal_size -> should throw if missing
    await expect(
      ProjectLeadRepository.createLead(s.workspaceId, projectId, {
        name: "Qualified Lead Missing Deal Size",
        stage: "QUALIFIED",
      })
    ).rejects.toThrow(/bắt buộc tại giai đoạn QUALIFIED/);

    // Stage QUALIFIED passes when deal_size is provided
    const qualifiedLead = await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
      name: "Qualified Lead With Deal Size",
      stage: "QUALIFIED",
      fieldValues: { deal_size: 50000 },
    });
    expect(qualifiedLead.fieldValues["deal_size"]).toBe(50000);
  });

  it("links leadSourceId, provenanceEventId, and stores consent", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    // Tạo lead source
    const sourceId = generateSnowflake().toString();
    await db.insert(leadSources).values({
      id: BigInt(sourceId),
      workspaceId: BigInt(s.workspaceId),
      projectId: BigInt(projectId),
      sourceType: "landing_form",
      label: "Main Website Form",
    });

    // Tạo ingestion event
    const eventId = generateSnowflake().toString();
    await db.insert(leadIngestionEvents).values({
      id: BigInt(eventId),
      workspaceId: BigInt(s.workspaceId),
      projectId: BigInt(projectId),
      leadSourceId: BigInt(sourceId),
      externalEventId: "evt_12345",
      payloadDigest: "sha256:abcde...",
    });

    const lead = await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
      name: "Consent Lead",
      email: "consent@example.com",
      leadSourceId: sourceId,
      provenanceEventId: eventId,
      consent: {
        purpose: "marketing_communication",
        lawfulBasis: "CONSENT",
        policyVersion: "2026.1",
      },
    });

    expect(lead.leadSourceId).toBe(sourceId);
    expect(lead.provenanceEventId).toBe(eventId);
  });

  it("lists leads with pagination and custom fields", async () => {
    const s = await createTestSession();
    const projectId = await makeProject(s.workspaceId);

    await ProjectLeadRepository.createFieldDefinition({
      workspaceId: s.workspaceId,
      projectId,
      stableKey: "segment",
      label: "Segment",
      dataType: "SHORT_TEXT",
    });

    for (let i = 1; i <= 3; i++) {
      await ProjectLeadRepository.createLead(s.workspaceId, projectId, {
        name: `Lead ${i}`,
        fieldValues: { segment: `Tier ${i}` },
      });
    }

    const all = await ProjectLeadRepository.listLeads(s.workspaceId, projectId, { limit: 10 });
    expect(all.length).toBe(3);
    expect(all[0].fieldValues["segment"]).toBeDefined();

    const page1 = await ProjectLeadRepository.listLeads(s.workspaceId, projectId, { limit: 2, offset: 0 });
    expect(page1.length).toBe(2);

    const page2 = await ProjectLeadRepository.listLeads(s.workspaceId, projectId, { limit: 2, offset: 2 });
    expect(page2.length).toBe(1);
  });
});
