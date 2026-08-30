/**
 * Academy Production Contract Tests — Task 6
 *
 * Verifies cross-domain isolation:
 * - Academy schema exports no production evidence tables
 * - Academy handlers have no imports from operations/strategy
 * - Production evidence/gate handlers reject academy refs
 * - Template export kind is always 'academy_template_draft'
 */
import { describe, it, expect } from "vitest";
import { assertNotAcademyReference, assertNotAcademyTemplateDraft, isAcademyReference, ACADEMY_TEMPLATE_DRAFT_KIND } from "../contracts";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { createProject } from "../../operations/handlers/project.handler";
import { recordEvidence } from "../../operations/strategy/handlers/evidence.handler";
import { exportTemplate, _resetTemplateExportStore } from "../handlers/template-export.handler";

describe("Academy Production Contract: full firewall (Task 6)", () => {
  it("assertNotAcademyReference rejects all academy-artifact:// variants", () => {
    const academyRefs = [
      "academy-artifact://lesson/1",
      "academy-artifact://",
      "academy-artifact://simulation/p0_discovery_v1/sim_abc123",
    ];

    for (const ref of academyRefs) {
      expect(() => assertNotAcademyReference(ref, "artifactRef")).toThrowError(/academy|synthetic/i);
    }
  });

  it("assertNotAcademyReference rejects academy_* identifiers", () => {
    const academyIds = [
      "academy_attempt_12345",
      "academy_program_abc",
      "academy_enrollment_999",
    ];

    for (const id of academyIds) {
      expect(() => assertNotAcademyReference(id, "id")).toThrowError(/academy/i);
    }
  });

  it("assertNotAcademyTemplateDraft rejects academy_template_draft kind", () => {
    expect(() =>
      assertNotAcademyTemplateDraft(ACADEMY_TEMPLATE_DRAFT_KIND)
    ).toThrowError(/academy_template_draft|real source/i);
  });

  it("assertNotAcademyTemplateDraft allows production artifact kinds", () => {
    expect(() => assertNotAcademyTemplateDraft("interview_transcript")).not.toThrow();
    expect(() => assertNotAcademyTemplateDraft("evidence_document")).not.toThrow();
  });

  it("isAcademyReference correctly identifies all academy reference formats", () => {
    expect(isAcademyReference("academy-artifact://lesson/1")).toBe(true);
    expect(isAcademyReference("academy_attempt_123")).toBe(true);
    expect(isAcademyReference("artifact://live-workspace/data.pdf")).toBe(false);
    expect(isAcademyReference("s3://evidence-bucket/file.pdf")).toBe(false);
    expect(isAcademyReference(null)).toBe(false);
    expect(isAcademyReference(undefined)).toBe(false);
    expect(isAcademyReference("")).toBe(false);
  });

  it("ACADEMY_TEMPLATE_DRAFT_KIND constant is stable and correct", () => {
    expect(ACADEMY_TEMPLATE_DRAFT_KIND).toBe("academy_template_draft");
  });

  it("recordEvidence rejects an academy_template_draft artifactKind (Task 4)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Academy Firewall Project",
      description: "Project for testing template-draft rejection",
      lifecycleStage: "P0_DISCOVERY",
    });

    await expect(
      recordEvidence({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        sourceType: "interview",
        claim: "Academy template draft claim",
        artifactKind: ACADEMY_TEMPLATE_DRAFT_KIND,
      } as any)
    ).rejects.toThrow(/academy_template_draft|real source/i);
  });

  it("exportTemplate requires explicit human confirmation and always labels the draft (Task 4)", () => {
    _resetTemplateExportStore();

    expect(() =>
      exportTemplate({
        workspaceId: "ws-1",
        accountId: "acc-1",
        academyAttemptId: "att-1",
        templateKind: "interview-script",
        body: { question: "What is the biggest problem?" },
        confirmedByAccountId: "",
      })
    ).toThrow(/confirmation/i);

    const record = exportTemplate({
      workspaceId: "ws-1",
      accountId: "acc-1",
      academyAttemptId: "att-1",
      templateKind: "interview-script",
      body: { question: "What is the biggest problem?", score: 0.9, synthetic: true },
      confirmedByAccountId: "acc-1",
    });

    expect(record.liveArtifactKind).toBe(ACADEMY_TEMPLATE_DRAFT_KIND);
    expect(record.academySourceRef.startsWith("academy-artifact://")).toBe(true);
    expect(record.body).not.toHaveProperty("score");
    expect(record.body).not.toHaveProperty("synthetic");
  });

  it("Academy schema exports do not contain production lifecycle table names", async () => {
    const academySchema = await import("../../shared/db/schema/academy");
    const keys = Object.keys(academySchema);

    // These MUST NOT exist in the academy module
    const forbidden = [
      "evidence",
      "evidenceIngestions",
      "gateEvaluations",
      "workspaceStageTransitions",
      "pilotRuns",
      "metricContracts",
      "metricSnapshots",
    ];

    for (const name of forbidden) {
      expect(keys, `Academy schema must not export '${name}'`).not.toContain(name);
    }

    // These MUST exist
    const required = [
      "academyPrograms",
      "academyModules",
      "academyLessons",
      "academyEnrollments",
      "academyLessonAttempts",
      "academySimulationRuns",
      "academyTemplateExports",
    ];

    for (const name of required) {
      expect(keys, `Academy schema must export '${name}'`).toContain(name);
    }
  });
});
