import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { academyPrograms, academyEnrollments, academyLessonAttempts } = schema;

export interface AcademyProgram {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  version: string;
  moduleCount: number;
  lessonCount: number;
  published: boolean;
  createdAt: string;
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
  // INVARIANT: không có lifecycleStage, projectId, gateEvaluationId, evidenceId
}

export interface AcademyLessonAttempt {
  id: string;
  enrollmentId: string;
  lessonId: string;
  status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";
  reflection: string | null;
  score: number | null;
  /** Luôn true — đây là điểm rubric học tập, không phải metric PMF/maturity. */
  synthetic: true;
  attemptedAt: string;
  completedAt: string | null;
}

export interface CompleteLessonResult {
  attempt: AcademyLessonAttempt;
  enrollment: AcademyEnrollment;
  /** INVARIANT: luôn false — hoàn thành bài học không bao giờ đổi project stage thật. */
  projectStageChanged: false;
  /** INVARIANT: luôn false — hoàn thành bài học không bao giờ tạo evidence thật. */
  evidenceCreated: false;
}

const PROGRAM_VIEW_COLUMNS = {
  id: academyPrograms.id,
  slug: academyPrograms.slug,
  title: academyPrograms.title,
  description: academyPrograms.description,
  version: academyPrograms.version,
  moduleCount: academyPrograms.moduleCount,
  lessonCount: academyPrograms.lessonCount,
  published: academyPrograms.published,
  createdAt: academyPrograms.createdAt,
} as const;

type ProgramRow = Pick<typeof academyPrograms.$inferSelect, keyof typeof PROGRAM_VIEW_COLUMNS>;

function mapProgramRow(row: ProgramRow): AcademyProgram {
  return {
    id: row.id.toString(),
    slug: row.slug,
    title: row.title,
    description: row.description ?? null,
    version: row.version,
    moduleCount: row.moduleCount,
    lessonCount: row.lessonCount,
    published: row.published,
    createdAt: row.createdAt.toISOString(),
  };
}

const ENROLLMENT_VIEW_COLUMNS = {
  id: academyEnrollments.id,
  workspaceId: academyEnrollments.workspaceId,
  accountId: academyEnrollments.accountId,
  programId: academyEnrollments.programId,
  completedLessons: academyEnrollments.completedLessons,
  status: academyEnrollments.status,
  enrolledAt: academyEnrollments.enrolledAt,
  completedAt: academyEnrollments.completedAt,
} as const;

type EnrollmentRow = Pick<typeof academyEnrollments.$inferSelect, keyof typeof ENROLLMENT_VIEW_COLUMNS>;

function mapEnrollmentRow(row: EnrollmentRow): AcademyEnrollment {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    accountId: row.accountId.toString(),
    programId: row.programId.toString(),
    completedLessons: row.completedLessons,
    status: row.status as AcademyEnrollment["status"],
    enrolledAt: row.enrolledAt.toISOString(),
    completedAt: row.completedAt ? row.completedAt.toISOString() : null,
  };
}

function mapAttemptRow(row: typeof academyLessonAttempts.$inferSelect): AcademyLessonAttempt {
  return {
    id: row.id.toString(),
    enrollmentId: row.enrollmentId.toString(),
    lessonId: row.lessonId.toString(),
    status: row.status as AcademyLessonAttempt["status"],
    reflection: row.reflection ?? null,
    score: row.score ?? null,
    synthetic: true,
    attemptedAt: row.attemptedAt.toISOString(),
    completedAt: row.completedAt ? row.completedAt.toISOString() : null,
  };
}

export async function getAcademyPrograms(): Promise<AcademyProgram[]> {
  const rows = await db.select(PROGRAM_VIEW_COLUMNS).from(academyPrograms);
  return rows.map(mapProgramRow);
}

export async function getAcademyProgram(id: string): Promise<AcademyProgram> {
  const [row] = await db
    .select(PROGRAM_VIEW_COLUMNS)
    .from(academyPrograms)
    .where(eq(academyPrograms.id, BigInt(id)))
    .limit(1);
  if (!row) throw APIError.notFound(`academy program ${id} not found`);
  return mapProgramRow(row);
}

export interface EnrollLearnerParams {
  workspaceId: string;
  accountId: string;
  programId: string;
}

export async function enrollLearner(params: EnrollLearnerParams): Promise<AcademyEnrollment> {
  const [row] = await db
    .insert(academyEnrollments)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      accountId: BigInt(params.accountId),
      programId: BigInt(params.programId),
    })
    .returning(ENROLLMENT_VIEW_COLUMNS);
  if (!row) throw APIError.internal("failed to create academy enrollment");
  return mapEnrollmentRow(row);
}

export async function getEnrollment(enrollmentId: string): Promise<AcademyEnrollment> {
  const [row] = await db
    .select(ENROLLMENT_VIEW_COLUMNS)
    .from(academyEnrollments)
    .where(eq(academyEnrollments.id, BigInt(enrollmentId)))
    .limit(1);
  if (!row) throw APIError.notFound(`academy enrollment ${enrollmentId} not found`);
  return mapEnrollmentRow(row);
}

export interface CompleteLessonParams {
  enrollmentId: string;
  lessonId: string;
  reflection?: string;
  score?: number;
}

export async function completeLesson(params: CompleteLessonParams): Promise<CompleteLessonResult> {
  const enrollment = await getEnrollment(params.enrollmentId);

  const [attemptRow] = await db
    .insert(academyLessonAttempts)
    .values({
      id: generateSnowflake(),
      enrollmentId: BigInt(params.enrollmentId),
      lessonId: BigInt(params.lessonId),
      status: "COMPLETED",
      reflection: params.reflection ?? null,
      score: params.score ?? null,
      synthetic: true,
      completedAt: new Date(),
    })
    .returning();
  if (!attemptRow) throw APIError.internal("failed to record lesson attempt");

  const [updatedRow] = await db
    .update(academyEnrollments)
    .set({
      completedLessons: enrollment.completedLessons + 1,
      status: "IN_PROGRESS",
    })
    .where(eq(academyEnrollments.id, BigInt(params.enrollmentId)))
    .returning(ENROLLMENT_VIEW_COLUMNS);
  if (!updatedRow) throw APIError.internal("failed to update academy enrollment");

  return {
    attempt: mapAttemptRow(attemptRow),
    enrollment: mapEnrollmentRow(updatedRow),
    projectStageChanged: false,
    evidenceCreated: false,
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
