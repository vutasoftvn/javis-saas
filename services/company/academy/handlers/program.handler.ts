/**
 * Academy program, enrollment, and progress handlers.
 *
 * ISOLATION RULE: This file MUST NOT import any module from:
 * - `operations/strategy` handlers or services
 * - `operations/handlers` (project, task, etc.)
 * - `commercial` or `finance-legal` handlers
 *
 * Academy is a separate bounded context.
 */
import { api } from "encore.dev/api";
import {
  getAcademyPrograms,
  getAcademyProgram,
  enrollLearner,
  getEnrollment,
  completeLesson,
} from "../services/program.service";
import type {
  AcademyProgram,
  AcademyEnrollment,
  CompleteLessonResult,
  EnrollLearnerParams,
  CompleteLessonParams,
} from "../services/program.service";

export type { AcademyProgram, AcademyEnrollment, CompleteLessonResult, EnrollLearnerParams, CompleteLessonParams };

export const listAcademyPrograms = api(
  { method: "GET", path: "/academy/programs", expose: true },
  async (): Promise<{ programs: AcademyProgram[] }> => ({ programs: await getAcademyPrograms() })
);

export const getAcademyProgramEndpoint = api(
  { method: "GET", path: "/academy/programs/:id", expose: true },
  async ({ id }: { id: string }): Promise<AcademyProgram> => getAcademyProgram(id)
);

export const enrollLearnerEndpoint = api(
  { method: "POST", path: "/academy/enrollments", expose: true },
  async (params: EnrollLearnerParams): Promise<AcademyEnrollment> => enrollLearner(params)
);

export const getEnrollmentEndpoint = api(
  { method: "GET", path: "/academy/enrollments/:id", expose: true },
  async ({ id }: { id: string }): Promise<AcademyEnrollment> => getEnrollment(id)
);

export const completeLessonEndpoint = api(
  { method: "POST", path: "/academy/enrollments/:enrollmentId/complete-lesson", expose: true },
  async (params: { enrollmentId: string } & Omit<CompleteLessonParams, "enrollmentId">): Promise<CompleteLessonResult> =>
    completeLesson({ ...params, enrollmentId: params.enrollmentId })
);
