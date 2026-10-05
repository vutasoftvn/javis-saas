import { text, bigint, timestamp, numeric, index, date, AnyPgColumn } from "drizzle-orm/pg-core";
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
