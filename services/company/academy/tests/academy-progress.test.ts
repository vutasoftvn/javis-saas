/**
 * Academy progress tests — DB-backed (Task 4, kế tục Task 2 cũ).
 *
 * Verifies:
 * - Enrollment creation là cô lập với live project (không có field lifecycle)
 * - Lesson completion tăng completedLessons
 * - Lesson completion KHÔNG đổi project stage, KHÔNG tạo evidence
 * - Attempt payload chứa field production bị reject
 */
import { describe, it, expect, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  enrollLearner,
  getEnrollment,
  completeLesson,
  assertAttemptPayloadIsolated,
} from "../services/program.service";

const { academyPrograms, academyModules, academyLessons } = schema;

async function seedProgram(): Promise<string> {
  const id = generateSnowflake();
  await db.insert(academyPrograms).values({
    id,
    slug: `test-program-${id}`,
    title: "Test Program",
    version: "1.0.0",
  });
  return id.toString();
}

// LƯU Ý: `lesson_attempts.lesson_id` là FK NOT NULL tới `academy.lessons(id)`
// (xem migration 001_academy_programs.up.sql) — completeLesson() không thể
// nhận một snowflake ngẫu nhiên làm lessonId, phải seed lesson thật qua module.
async function seedLesson(programId: string): Promise<string> {
  const moduleId = generateSnowflake();
  await db.insert(academyModules).values({
    id: moduleId,
    programId: BigInt(programId),
    slug: `test-module-${moduleId}`,
    title: "Test Module",
  });

  const lessonId = generateSnowflake();
  await db.insert(academyLessons).values({
    id: lessonId,
    moduleId,
    slug: `test-lesson-${lessonId}`,
    title: "Test Lesson",
  });
  return lessonId.toString();
}

describe("Academy Progress: enrollment and lesson completion (DB-backed)", () => {
  let programId: string;

  beforeEach(async () => {
    programId = await seedProgram();
  });

  it("enrolls a learner and returns an enrollment with no lifecycle fields", async () => {
    const enrollment = await enrollLearner({
      workspaceId: generateSnowflake().toString(),
      accountId: generateSnowflake().toString(),
      programId,
    });

    expect(enrollment.id).toBeDefined();
    expect(enrollment.status).toBe("NOT_STARTED");
    expect(enrollment.completedLessons).toBe(0);

    expect(enrollment).not.toHaveProperty("lifecycleStage");
    expect(enrollment).not.toHaveProperty("projectId");
    expect(enrollment).not.toHaveProperty("evidenceId");
    expect(enrollment).not.toHaveProperty("gateEvaluationId");
  });

  it("completing a lesson increments completedLessons and preserves isolation", async () => {
    const enrollment = await enrollLearner({
      workspaceId: generateSnowflake().toString(),
      accountId: generateSnowflake().toString(),
      programId,
    });

    const result = await completeLesson({
      enrollmentId: enrollment.id,
      lessonId: await seedLesson(programId),
      reflection: "Tôi hiểu rõ hơn về giai đoạn Discovery",
    });

    expect(result.attempt.synthetic).toBe(true);
    expect(result.attempt.completedAt).toBeDefined();
    expect(result.enrollment.completedLessons).toBe(1);
    expect(result.enrollment.status).toBe("IN_PROGRESS");
    expect(result.projectStageChanged).toBe(false);
    expect(result.evidenceCreated).toBe(false);
  });

  it("getEnrollment reflects updated completedLessons after two lesson completions", async () => {
    const enrollment = await enrollLearner({
      workspaceId: generateSnowflake().toString(),
      accountId: generateSnowflake().toString(),
      programId,
    });

    await completeLesson({ enrollmentId: enrollment.id, lessonId: await seedLesson(programId) });
    await completeLesson({ enrollmentId: enrollment.id, lessonId: await seedLesson(programId) });

    const updated = await getEnrollment(enrollment.id);
    expect(updated.completedLessons).toBe(2);
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
