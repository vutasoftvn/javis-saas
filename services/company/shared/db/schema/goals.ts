import { text, bigint, timestamp, integer, numeric, index, date, AnyPgColumn } from "drizzle-orm/pg-core";
import { strategySchema } from "./operations";
import { identityWorkspaces } from "./identity";
import { onboardSnapshots } from "./onboard";

// =========================================================
// GOALS (nested, time-boxed)
// =========================================================
export const goals = strategySchema.table("goals", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  parentId: bigint("parent_id", { mode: "bigint" })
    .references((): AnyPgColumn => goals.id, { onDelete: "cascade" }),

  title: text("title").notNull(),
  description: text("description"),
  goalType: text("goal_type").notNull(), // 'vision' | 'strategic' | 'tactical' | 'sprint'

  // Time-box (vision có thể NULL)
  startDate: date("start_date"),
  endDate: date("end_date"),
  durationWeeks: numeric("duration_weeks", { precision: 4, scale: 1 }),

  status: text("status").default("active").notNull(), // 'draft' | 'active' | 'completed' | 'abandoned'
  onboardSnapshotId: bigint("onboard_snapshot_id", { mode: "bigint" })
    .references(() => onboardSnapshots.id),

  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
}, (t) => ({
  idxGoalsWsActive: index("idx_goals_workspace_active").on(t.workspaceId, t.status),
  idxGoalsParent: index("idx_goals_parent").on(t.parentId),
  idxGoalsDates: index("idx_goals_dates").on(t.workspaceId, t.startDate, t.endDate),
  idxGoalsType: index("idx_goals_type").on(t.workspaceId, t.goalType, t.status),
}));

// =========================================================
// OBJECTIVES (nhiều objective trong 1 goal)
// =========================================================
export const objectives = strategySchema.table("objectives", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  goalId: bigint("goal_id", { mode: "bigint" })
    .notNull()
    .references(() => goals.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),

  title: text("title").notNull(),
  description: text("description"),
  ownerUserId: bigint("owner_user_id", { mode: "bigint" }),
  weight: numeric("weight", { precision: 4, scale: 2 }).default("1.0"),
  displayOrder: integer("display_order").default(0),
  status: text("status").default("active").notNull(), // 'active' | 'completed' | 'abandoned'
  progressPct: numeric("progress_pct", { precision: 5, scale: 2 }).default("0"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  idxObjectivesGoal: index("idx_objectives_goal").on(t.goalId, t.displayOrder),
  idxObjectivesWorkspace: index("idx_objectives_workspace").on(t.workspaceId, t.status),
  idxObjectivesOwner: index("idx_objectives_owner").on(t.ownerUserId),
}));

// =========================================================
// KEY RESULTS
// =========================================================
export const cosaKeyResults = strategySchema.table("cosa_key_results", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  objectiveId: bigint("objective_id", { mode: "bigint" })
    .notNull()
    .references(() => objectives.id, { onDelete: "cascade" }),
  metricName: text("metric_name").notNull(),
  baseline: numeric("baseline"),
  target: numeric("target").notNull(),
  currentValue: numeric("current_value").default("0"),
  unit: text("unit"),
  status: text("status").default("active"), // 'active' | 'achieved' | 'missed' | 'archived'
  displayOrder: integer("display_order").default(0),
}, (t) => ({
  idxKrObjective: index("idx_kr_objective").on(t.objectiveId, t.displayOrder),
}));
