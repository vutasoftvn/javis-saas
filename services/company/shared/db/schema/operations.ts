import { pgSchema, text, bigint, timestamp, doublePrecision, jsonb, varchar, integer, boolean, uniqueIndex } from "drizzle-orm/pg-core";

export const operatingSchema = pgSchema("operating");
export const strategySchema = pgSchema("strategy");

export const initiatives = strategySchema.table("initiatives", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  title: text("title").notNull(),
  status: text("status").default("active").notNull(),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const tasks = operatingSchema.table("tasks", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  idempotencyKey: text("idempotency_key"),
  status: text("status").default("todo").notNull(),
  priority: text("priority").default("medium").notNull(),
  plannedStartAt: timestamp("planned_start_at", { withTimezone: true }),
  dueAt: timestamp("due_at", { withTimezone: true }),
  timezone: text("timezone").default("UTC").notNull(),
  source: text("source"),
  completionPolicy: text("completion_policy"),
  initiativeId: bigint("initiative_id", { mode: "bigint" }).references(() => initiatives.id, { onDelete: "set null" }),
  weeklyCommitmentId: bigint("weekly_commitment_id", { mode: "bigint" }),
  sortKey: doublePrecision("sort_key"),
  assigneeMemberId: bigint("assignee_member_id", { mode: "bigint" }),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  executionMode: text("execution_mode"),
  function: text("function"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_tasks_id_workspace").on(t.id, t.workspaceId),
}));

export const taskDependencies = operatingSchema.table("task_dependencies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  dependsOnTaskId: bigint("depends_on_task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  dependencyType: varchar("dependency_type", { length: 50 }).default("BLOCKS"),
  status: varchar("status", { length: 50 }).default("PENDING").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const taskSchedules = operatingSchema.table("task_schedules", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  scheduleType: varchar("schedule_type", { length: 50 }).default("once").notNull(),
  cronExpr: varchar("cron_expr", { length: 100 }),
  nextRunAt: timestamp("next_run_at", { withTimezone: true }),
  active: boolean("active").default(true).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const okrCycles = strategySchema.table("okr_cycles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: text("name").notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  status: text("status").default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const okrObjectives = strategySchema.table("okr_objectives", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  cycleId: bigint("cycle_id", { mode: "bigint" }).notNull().references(() => okrCycles.id, { onDelete: "cascade" }),
  strategicObjectiveId: bigint("strategic_objective_id", { mode: "bigint" }),
  title: text("title").notNull(),
  why: text("why"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  status: text("status").default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_okr_objectives_id_workspace").on(t.id, t.workspaceId),
}));

export const keyResults = strategySchema.table("key_results", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  objectiveId: bigint("objective_id", { mode: "bigint" }).notNull().references(() => okrObjectives.id, { onDelete: "cascade" }),
  title: text("title"),
  metricId: bigint("metric_id", { mode: "bigint" }),
  baselineValue: doublePrecision("baseline_value"),
  currentValue: doublePrecision("current_value"),
  targetValue: doublePrecision("target_value"),
  unit: text("unit"),
  cadence: text("cadence"),
  metricType: text("metric_type"),
  evidenceRefs: jsonb("evidence_refs"),
  status: text("status").default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const twelveWeekCycles = operatingSchema.table("twelve_week_cycles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  theme: varchar("theme", { length: 255 }),
  visionStatement: text("vision_statement").default("").notNull(),
  stageAtStart: varchar("stage_at_start", { length: 50 }).default("S1_PROBLEM_VALIDATION").notNull(),
  currentWeek: integer("current_week").default(1).notNull(),
  durationWeeks: integer("duration_weeks").default(12).notNull(),
  overallExecutionScore: doublePrecision("overall_execution_score").default(0.0).notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  commitmentLevel: varchar("commitment_level", { length: 50 }),
  status: varchar("status", { length: 50 }).default("ACTIVE").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const weeklyPlans = operatingSchema.table("weekly_plans", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  cycleId: bigint("cycle_id", { mode: "bigint" }).notNull().references(() => twelveWeekCycles.id, { onDelete: "cascade" }),
  weekNo: integer("week_no").notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  focus: text("focus"),
  mission: text("mission"),
  executionScore: doublePrecision("execution_score"),
  outcomeScore: doublePrecision("outcome_score"),
  reflection: text("reflection"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const weeklyCommitments = operatingSchema.table("weekly_commitments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  weeklyPlanId: bigint("weekly_plan_id", { mode: "bigint" }).notNull().references(() => weeklyPlans.id, { onDelete: "cascade" }),
  initiativeId: bigint("initiative_id", { mode: "bigint" }).references(() => initiatives.id, { onDelete: "set null" }),
  title: varchar("title", { length: 255 }).notNull(),
  status: varchar("status", { length: 50 }).default("todo").notNull(),
  plannedEffort: varchar("planned_effort", { length: 50 }),
  commitmentOwnerType: varchar("commitment_owner_type", { length: 50 }).default("FOUNDER"),
  executionMode: varchar("execution_mode", { length: 50 }).default("MANUAL"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const portfolios = strategySchema.table("portfolios", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  description: text("description"),
  strategicFocus: varchar("strategic_focus", { length: 255 }),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_portfolios_id_workspace").on(t.id, t.workspaceId),
}));

export const projects = strategySchema.table("projects", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  phase: varchar("phase", { length: 50 }),
  currentGate: varchar("current_gate", { length: 50 }),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  projectType: varchar("project_type", { length: 50 }),
  strategicPriority: varchar("strategic_priority", { length: 50 }),
  founderAttentionBudget: doublePrecision("founder_attention_budget"),
  portfolioId: bigint("portfolio_id", { mode: "bigint" }).references(() => portfolios.id, { onDelete: "set null" }),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_projects_id_workspace").on(t.id, t.workspaceId),
}));

export const portfolioProjects = strategySchema.table("portfolio_projects", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  portfolioId: bigint("portfolio_id", { mode: "bigint" }).notNull().references(() => portfolios.id, { onDelete: "cascade" }),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  strategicPriority: varchar("strategic_priority", { length: 50 }).default("core").notNull(),
  capacityAllocation: doublePrecision("capacity_allocation").default(0.0).notNull(),
  founderAttentionHours: doublePrecision("founder_attention_hours").default(0.0).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
