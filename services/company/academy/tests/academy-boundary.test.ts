/**
 * Academy Boundary Tests — Task 1 Step 1
 *
 * Verifies structural isolation:
 * - Academy artifacts cannot enter production evidence (recordEvidence rejects academy-artifact:// refs)
 * - Academy IDs cannot be used as live project references
 * - Academy schema tables do not contain production lifecycle columns
 * - assertNotAcademyReference throws for academy refs and is a no-op for valid refs
 */
import { describe, it, expect } from "vitest";
import { assertNotAcademyReference, assertNotAcademyTemplateDraft, isAcademyReference } from "../contracts";

describe("Academy Boundary: contract isolation (Task 1)", () => {
  describe("assertNotAcademyReference", () => {
    it("throws for academy-artifact:// reference in evidence artifactRef", () => {
      expect(() =>
        assertNotAcademyReference("academy-artifact://lesson/1/output", "artifactRef")
      ).toThrowError(/academy|synthetic/i);
    });

    it("throws for academy_* id in sourceRecordId", () => {
      expect(() =>
        assertNotAcademyReference("academy_attempt_12345", "sourceRecordId")
      ).toThrowError(/academy/i);
    });

    it("does not throw for valid artifact refs", () => {
      expect(() => assertNotAcademyReference("artifact://ws-1/interviews/int-001.pdf")).not.toThrow();
      expect(() => assertNotAcademyReference("s3://company-evidence/ev-2026-001.pdf")).not.toThrow();
      expect(() => assertNotAcademyReference(null)).not.toThrow();
      expect(() => assertNotAcademyReference(undefined)).not.toThrow();
      expect(() => assertNotAcademyReference("")).not.toThrow();
    });

    it("throws for partial academy prefix at start", () => {
      expect(() =>
        assertNotAcademyReference("academy-artifact://", "field")
      ).toThrowError(/academy/i);
    });

    it("does NOT throw for academy ref appearing only in the middle of a string", () => {
      // Safety: only prefix-based rejection, not substring matching
      expect(() =>
        assertNotAcademyReference("see also: academy-artifact://lesson/1")
      ).not.toThrow();
    });
  });

  describe("assertNotAcademyTemplateDraft", () => {
    it("throws for academy_template_draft artifact kind", () => {
      expect(() =>
        assertNotAcademyTemplateDraft("academy_template_draft")
      ).toThrowError(/academy_template_draft|real source/i);
    });

    it("does not throw for approved source kinds", () => {
      expect(() => assertNotAcademyTemplateDraft("interview_transcript")).not.toThrow();
      expect(() => assertNotAcademyTemplateDraft("market_research_report")).not.toThrow();
      expect(() => assertNotAcademyTemplateDraft(null)).not.toThrow();
    });
  });

  describe("isAcademyReference", () => {
    it("returns true for academy-artifact:// refs", () => {
      expect(isAcademyReference("academy-artifact://lesson/1")).toBe(true);
    });

    it("returns true for academy_* ids", () => {
      expect(isAcademyReference("academy_attempt_123")).toBe(true);
    });

    it("returns false for production refs", () => {
      expect(isAcademyReference("artifact://ws-1/data.pdf")).toBe(false);
      expect(isAcademyReference("")).toBe(false);
      expect(isAcademyReference(null)).toBe(false);
      expect(isAcademyReference(undefined)).toBe(false);
    });
  });

  describe("Schema isolation: academy schema tables", () => {
    it("academy schema does not export evidence, gate_evaluations, or stage_transition tables", async () => {
      const academyModule = await import("../../shared/db/schema/academy");
      const exportedNames = Object.keys(academyModule);

      // These production table names must NOT exist in academy schema
      expect(exportedNames).not.toContain("evidence");
      expect(exportedNames).not.toContain("gateEvaluations");
      expect(exportedNames).not.toContain("workspaceStageTransitions");
      expect(exportedNames).not.toContain("pilotRuns");
      expect(exportedNames).not.toContain("metricContracts");
      expect(exportedNames).not.toContain("evidenceIngestions");

      // Academy tables that SHOULD exist
      expect(exportedNames).toContain("academyPrograms");
      expect(exportedNames).toContain("academyLessons");
      expect(exportedNames).toContain("academyEnrollments");
      expect(exportedNames).toContain("academyLessonAttempts");
      expect(exportedNames).toContain("academySimulationRuns");
    });
  });
});
