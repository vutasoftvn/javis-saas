/**
 * Academy progress tests — Task 2 Step 1
 *
 * Verifies:
 * - Enrollment creation is isolated from live projects
 * - Lesson completion increments completedLessons
 * - Lesson completion does NOT mutate live project stage
 * - Lesson completion does NOT create live evidence
 * - Attempt payloads with forbidden production fields are rejected
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  enrollLearner,
  getEnrollment,
  completeLesson,
  assertAttemptPayloadIsolated,
  _resetAcademyStores,
} from "../handlers/program.handler";

describe("Academy Progress: enrollment and lesson completion (Task 2)", () => {
  beforeEach(() => {
    _resetAcademyStores();
  });

  it("enrolls a learner and returns an enrollment with no lifecycle fields", () => {
    const enrollment = enrollLearner({
      workspaceId: "ws-learn-1",
      accountId: "acc-founder-1",
      programId: "prog-lifecycle-101",
    });

    expect(enrollment.id).toBeDefined();
    expect(enrollment.status).toBe("NOT_STARTED");
    expect(enrollment.completedLessons).toBe(0);

    // INVARIANT: no lifecycle/project/evidence fields
    expect(enrollment).not.toHaveProperty("lifecycleStage");
    expect(enrollment).not.toHaveProperty("projectId");
    expect(enrollment).not.toHaveProperty("evidenceId");
    expect(enrollment).not.toHaveProperty("gateEvaluationId");
  });

  it("completing a lesson increments completedLessons and preserves isolation", () => {
    const enrollment = enrollLearner({
      workspaceId: "ws-learn-1",
      accountId: "acc-founder-1",
      programId: "prog-lifecycle-101",
    });

    const result = completeLesson({
      enrollmentId: enrollment.id,
      lessonId: "lesson-p0-01",
      reflection: "Tôi hiểu rõ hơn về giai đoạn Discovery",
    });

    expect(result.attempt.synthetic).toBe(true);
    expect(result.attempt.completedAt).toBeDefined();
    expect(result.enrollment.completedLessons).toBe(1);
    expect(result.enrollment.status).toBe("IN_PROGRESS");

    // INVARIANT: live project stage is never mutated
    expect(result.projectStageChanged).toBe(false);
    // INVARIANT: no live evidence was created
    expect(result.evidenceCreated).toBe(false);
  });

  it("getEnrollment reflects updated completedLessons after two lesson completions", () => {
    const enrollment = enrollLearner({
      workspaceId: "ws-learn-2",
      accountId: "acc-leader-2",
      programId: "prog-lifecycle-101",
    });

    completeLesson({ enrollmentId: enrollment.id, lessonId: "lesson-p0-01" });
    completeLesson({ enrollmentId: enrollment.id, lessonId: "lesson-p0-02" });

    const updated = getEnrollment(enrollment.id);
    expect(updated?.completedLessons).toBe(2);
  });

  it("rejects attempt payload containing gateEvaluationId (forbidden production field)", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Good learning", gateEvaluationId: "gate-123" })
    ).toThrowError(/gateEvaluationId/);
  });

  it("rejects attempt payload containing lifecycleStage", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Learning complete", lifecycleStage: "P3_PILOT" })
    ).toThrowError(/lifecycleStage/);
  });

  it("rejects attempt payload containing evidenceId", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Done", evidenceId: "ev-456" })
    ).toThrowError(/evidenceId/);
  });

  it("accepts attempt payload with only allowed fields", () => {
    expect(() =>
      assertAttemptPayloadIsolated({ reflection: "Great session", score: 85 })
    ).not.toThrow();
  });
});
