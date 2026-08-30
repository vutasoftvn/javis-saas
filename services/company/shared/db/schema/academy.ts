/**
 * Academy schema — completely isolated from production lifecycle data.
 *
 * RULES:
 * - No foreign keys into strategy.projects, evidence, gate_evaluations,
 *   metric_contracts, pilots, tasks, or capability_enablements.
 * - Learner profiles link to identity only via workspace_id / account reference.
 * - Academy identifiers are branded to prevent accidental cross-domain usage.
 *
 * Academy artifacts use the `academy-artifact://` scheme.
 * Production evidence rejects that scheme via assertNotAcademyReference().
 */
import {
  text,
  bigint,
  timestamp,
  varchar,
  integer,
  boolean,
  jsonb,
  pgSchema,
} from "drizzle-orm/pg-core";

export const academySchema = pgSchema("academy");

// ─── Branded ID types ───────────────────────────────────────────────────────
// These opaque types prevent accidental use of Academy IDs in production APIs.
declare const _academyProgramBrand: unique symbol;
declare const _academyAttemptBrand: unique symbol;
declare const _academyArtifactBrand: unique symbol;
declare const _syntheticScenarioBrand: unique symbol;

export type AcademyProgramId = string & { readonly [_academyProgramBrand]: never };
export type AcademyAttemptId = string & { readonly [_academyAttemptBrand]: never };
export type AcademyArtifactRef = string & { readonly [_academyArtifactBrand]: never };
export type SyntheticScenarioRef = string & { readonly [_syntheticScenarioBrand]: never };

/** Cast a raw string to AcademyProgramId (caller is responsible for format). */
export function asAcademyProgramId(id: string): AcademyProgramId {
  return id as AcademyProgramId;
}
export function asAcademyAttemptId(id: string): AcademyAttemptId {
  return id as AcademyAttemptId;
}
export function asAcademyArtifactRef(ref: string): AcademyArtifactRef {
  if (!ref.startsWith("academy-artifact://")) {
    throw new Error(`AcademyArtifactRef must start with 'academy-artifact://', got: ${ref}`);
  }
  return ref as AcademyArtifactRef;
}
export function asSyntheticScenarioRef(ref: string): SyntheticScenarioRef {
  return ref as SyntheticScenarioRef;
}

// ─── Academy Programs ────────────────────────────────────────────────────────
export const academyPrograms = academySchema.table("programs", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  slug: varchar("slug", { length: 100 }).notNull().unique(),
  title: text("title").notNull(),
  description: text("description"),
  version: varchar("version", { length: 20 }).default("1.0.0").notNull(),
  moduleCount: integer("module_count").default(0).notNull(),
  lessonCount: integer("lesson_count").default(0).notNull(),
  published: boolean("published").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// ─── Academy Modules ─────────────────────────────────────────────────────────
export const academyModules = academySchema.table("modules", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  programId: bigint("program_id", { mode: "bigint" })
    .notNull()
    .references(() => academyPrograms.id, { onDelete: "cascade" }),
  slug: varchar("slug", { length: 100 }).notNull(),
  title: text("title").notNull(),
  order: integer("order").default(0).notNull(),
  learningObjective: text("learning_objective"),
  lifecycleTopic: varchar("lifecycle_topic", { length: 100 }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// ─── Academy Lessons ─────────────────────────────────────────────────────────
export const academyLessons = academySchema.table("lessons", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  moduleId: bigint("module_id", { mode: "bigint" })
    .notNull()
    .references(() => academyModules.id, { onDelete: "cascade" }),
  slug: varchar("slug", { length: 100 }).notNull(),
  title: text("title").notNull(),
  order: integer("order").default(0).notNull(),
  practiceType: varchar("practice_type", { length: 50 }).default("reading").notNull(),
  // content is curriculum material only — never a capability spec, pinned hash, or workspace prompt
  content: text("content"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// ─── Academy Enrollments ─────────────────────────────────────────────────────
export const academyEnrollments = academySchema.table("enrollments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  // Links to workspace/account only — NOT to a project, pilot, evidence, or gate.
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  accountId: bigint("account_id", { mode: "bigint" }).notNull(),
  programId: bigint("program_id", { mode: "bigint" })
    .notNull()
    .references(() => academyPrograms.id, { onDelete: "cascade" }),
  completedLessons: integer("completed_lessons").default(0).notNull(),
  status: varchar("status", { length: 30 }).default("NOT_STARTED").notNull(), // NOT_STARTED|IN_PROGRESS|COMPLETED
  enrolledAt: timestamp("enrolled_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
});

// ─── Academy Lesson Attempts ─────────────────────────────────────────────────
export const academyLessonAttempts = academySchema.table("lesson_attempts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  enrollmentId: bigint("enrollment_id", { mode: "bigint" })
    .notNull()
    .references(() => academyEnrollments.id, { onDelete: "cascade" }),
  lessonId: bigint("lesson_id", { mode: "bigint" })
    .notNull()
    .references(() => academyLessons.id, { onDelete: "cascade" }),
  status: varchar("status", { length: 30 }).default("NOT_STARTED").notNull(),
  reflection: text("reflection"),
  // synthetic always true; score is a learning rubric score, NEVER a PMF/maturity score
  score: integer("score"),
  synthetic: boolean("synthetic").default(true).notNull(),
  attemptedAt: timestamp("attempted_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
});

// ─── Synthetic Simulation Runs ───────────────────────────────────────────────
export const academySimulationRuns = academySchema.table("simulation_runs", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  enrollmentId: bigint("enrollment_id", { mode: "bigint" })
    .notNull()
    .references(() => academyEnrollments.id, { onDelete: "cascade" }),
  scenarioRef: text("scenario_ref").notNull(), // e.g. "p0_discovery_v1"
  scenarioVersion: varchar("scenario_version", { length: 20 }).notNull(),
  // artifactRef MUST start with 'academy-artifact://' — validated by application layer
  artifactRef: text("artifact_ref").notNull(),
  synthetic: boolean("synthetic").default(true).notNull(),
  feedback: jsonb("feedback"),
  disclaimer: text("disclaimer").notNull(),
  startedAt: timestamp("started_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
});

// ─── Academy Template Exports ────────────────────────────────────────────────
// One-way, human-confirmed exports only. Never creates Evidence candidates.
export const academyTemplateExports = academySchema.table("template_exports", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  simulationRunId: bigint("simulation_run_id", { mode: "bigint" })
    .references(() => academySimulationRuns.id, { onDelete: "set null" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  accountId: bigint("account_id", { mode: "bigint" }).notNull(),
  templateKind: varchar("template_kind", { length: 80 }).notNull(),
  // body is stripped of simulation scores, model feedback, and synthetic claims
  body: jsonb("body").notNull(),
  // academySourceRef starts with 'academy-artifact://'
  academySourceRef: text("academy_source_ref").notNull(),
  disclaimer: text("disclaimer").notNull(),
  // live_artifact_kind = 'academy_template_draft' — ineligible for Evidence until human replaces sources
  liveArtifactKind: varchar("live_artifact_kind", { length: 60 }).default("academy_template_draft").notNull(),
  exportedAt: timestamp("exported_at", { withTimezone: true }).defaultNow().notNull(),
  confirmedByAccountId: bigint("confirmed_by_account_id", { mode: "bigint" }).notNull(),
});
