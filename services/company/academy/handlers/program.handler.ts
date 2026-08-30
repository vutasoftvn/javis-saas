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

import { assertNotAcademyReference, ACADEMY_TEMPLATE_DRAFT_KIND } from "../contracts";

// ─── In-memory program store (until DB is wired) ────────────────────────────
export interface AcademyProgram {
  id: string;
  slug: string;
  title: string;
  description: string;
  version: string;
  moduleCount: number;
  lessonCount: number;
  published: boolean;
  createdAt: string;
}

export interface AcademyModule {
  id: string;
  programId: string;
  slug: string;
  title: string;
  order: number;
  learningObjective: string;
  lifecycleTopic: string;
}

export interface AcademyLesson {
  id: string;
  moduleId: string;
  slug: string;
  title: string;
  order: number;
  practiceType: string;
}

export interface AcademyEnrollment {
  id: string;
  workspaceId: string;
  accountId: string;
  programId: string;
  completedLessons: number;
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";
  enrolledAt: string;
  completedAt: string | null;
  // INVARIANT: no lifecycleStage, no projectId, no gateEvaluationId, no evidenceId
}

export interface AcademyLessonAttempt {
  id: string;
  enrollmentId: string;
  lessonId: string;
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";
  reflection: string | null;
  score: number | null;
  /** Always true — this is a learning rubric score, not a PMF/maturity metric */
  synthetic: true;
  attemptedAt: string;
  completedAt: string | null;
}

// ─── In-memory stores for testability ───────────────────────────────────────
const _programs: Map<string, AcademyProgram> = new Map();
const _enrollments: Map<string, AcademyEnrollment> = new Map();
const _attempts: Map<string, AcademyLessonAttempt[]> = new Map();

export function getAcademyPrograms(): AcademyProgram[] {
  return Array.from(_programs.values());
}

export function getAcademyProgram(id: string): AcademyProgram | undefined {
  return _programs.get(id);
}

export interface EnrollLearnerParams {
  workspaceId: string;
  accountId: string;
  programId: string;
}

export function enrollLearner(params: EnrollLearnerParams): AcademyEnrollment {
  const id = `enr_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const enrollment: AcademyEnrollment = {
    id,
    workspaceId: params.workspaceId,
    accountId: params.accountId,
    programId: params.programId,
    completedLessons: 0,
    status: "NOT_STARTED",
    enrolledAt: new Date().toISOString(),
    completedAt: null,
  };
  _enrollments.set(id, enrollment);
  return enrollment;
}

export function getEnrollment(enrollmentId: string): AcademyEnrollment | undefined {
  return _enrollments.get(enrollmentId);
}

export interface CompleteLessonParams {
  enrollmentId: string;
  lessonId: string;
  reflection?: string;
  score?: number;
}

export interface CompleteLessonResult {
  attempt: AcademyLessonAttempt;
  enrollment: AcademyEnrollment;
  /** INVARIANT: always false — lesson completion never changes a live project stage */
  projectStageChanged: false;
  /** INVARIANT: always false — lesson completion never creates live evidence */
  evidenceCreated: false;
}

export function completeLesson(params: CompleteLessonParams): CompleteLessonResult {
  const enrollment = _enrollments.get(params.enrollmentId);
  if (!enrollment) throw new Error(`Enrollment not found: ${params.enrollmentId}`);

  const attemptId = `att_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const attempt: AcademyLessonAttempt = {
    id: attemptId,
    enrollmentId: params.enrollmentId,
    lessonId: params.lessonId,
    status: "COMPLETED",
    reflection: params.reflection ?? null,
    score: params.score ?? null,
    synthetic: true,
    attemptedAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
  };

  const existing = _attempts.get(params.enrollmentId) ?? [];
  _attempts.set(params.enrollmentId, [...existing, attempt]);

  // Update enrollment progress
  const updated: AcademyEnrollment = {
    ...enrollment,
    completedLessons: enrollment.completedLessons + 1,
    status: "IN_PROGRESS",
  };
  _enrollments.set(params.enrollmentId, updated);

  return {
    attempt,
    enrollment: updated,
    projectStageChanged: false,  // INVARIANT: never mutates live lifecycle
    evidenceCreated: false,       // INVARIANT: never creates live evidence
  };
}

/**
 * Validates that an attempt payload does NOT contain forbidden production fields.
 * Call before persisting any attempt payload.
 */
export function assertAttemptPayloadIsolated(payload: Record<string, unknown>): void {
  const forbidden = ["gateEvaluationId", "lifecycleStage", "evidenceId", "projectId", "pilotId", "metricContractId"];
  for (const field of forbidden) {
    if (field in payload) {
      throw new Error(
        `Academy lesson attempt payload contains forbidden production field: '${field}'. ` +
        `Academy is isolated from live project, evidence, and gate state.`
      );
    }
  }
}

// ─── Reset for testing ───────────────────────────────────────────────────────
export function _resetAcademyStores(): void {
  _programs.clear();
  _enrollments.clear();
  _attempts.clear();
}
