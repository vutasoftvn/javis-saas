import { text, bigint, timestamp, jsonb, integer, boolean, numeric, uniqueIndex, index } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";
import { strategySchema } from "./operations";
import { identityWorkspaces } from "./identity";

// =========================================================
// ONBOARD SESSIONS
// =========================================================
export const onboardSessions = strategySchema.table("onboard_sessions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionType: text("session_type").notNull(), // 'initial' | 'partial_update' | 'event_driven'
  status: text("status").default("in_progress").notNull(), // 'in_progress' | 'completed' | 'abandoned'
  startedAt: timestamp("started_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  durationMinutes: integer("duration_minutes"),
  dimensionsTouched: text("dimensions_touched").array().default([]),
  summary: text("summary"),
  transcript: jsonb("transcript"),
  metadata: jsonb("metadata").default({}),
}, (t) => ({
  idxSessionsWs: index("idx_sessions_workspace").on(t.workspaceId, t.startedAt),
}));

// =========================================================
// CONVERSATION TURNS (Audit)
// =========================================================
export const conversationTurns = strategySchema.table("conversation_turns", {
  id: bigint("id", { mode: "bigint" }).primaryKey(), // Generated via snowflake or sequence in DB
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id, { onDelete: "cascade" }),
  turnNumber: integer("turn_number").notNull(),
  role: text("role").notNull(), // 'user' | 'assistant' | 'system'
  content: text("content").notNull(),
  dimension: text("dimension"), // 'identity' | 'stage_scale' | 'founder' | 'team_culture' | 'market' | 'challenges' | 'goals_ambition'
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  idxTurnsSession: index("idx_turns_session").on(t.sessionId, t.turnNumber),
  idxTurnsDimension: index("idx_turns_dimension").on(t.sessionId, t.dimension),
}));

// =========================================================
// ONBOARD SNAPSHOTS
// =========================================================
export const onboardSnapshots = strategySchema.table("onboard_snapshots", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  fullContext: jsonb("full_context").notNull(),
  changedDimensions: text("changed_dimensions").array().default([]),
  changeReason: text("change_reason"),
  isCurrent: boolean("is_current").default(false).notNull(),
  capturedAt: timestamp("captured_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  idxSnapshotsWs: index("idx_snapshots_workspace").on(t.workspaceId, t.capturedAt),
  uniqSnapshotCurrent: uniqueIndex("uniq_snapshot_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

// =========================================================
// CHIỀU 1: IDENTITY & VALUES
// =========================================================
export const onboardIdentity = strategySchema.table("onboard_identity", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  whatTheyDo: text("what_they_do"),
  whoTheyServe: text("who_they_serve"),
  foundingWhy: text("founding_why"),
  oneSentencePitch: text("one_sentence_pitch"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uniqIdentityCurrent: uniqueIndex("uniq_identity_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

export const onboardValues = strategySchema.table("onboard_values", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  identityId: bigint("identity_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardIdentity.id, { onDelete: "cascade" }),
  valueText: text("value_text").notNull(),
  isFireWorthy: boolean("is_fire_worthy").default(false),
  realityStatus: text("reality_status"), // 'real' | 'poster' | 'unclear'
  displayOrder: integer("display_order").default(0),
});

// =========================================================
// CHIỀU 2: STAGE & SCALE
// =========================================================
export const onboardStageScale = strategySchema.table("onboard_stage_scale", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  headcountFt: integer("headcount_ft"),
  headcountContractor: integer("headcount_contractor"),
  revenueArr: numeric("revenue_arr", { precision: 14, scale: 2 }),
  revenueCurrency: text("revenue_currency").default("USD"),
  runwayMonths: numeric("runway_months", { precision: 5, scale: 1 }),
  stage: text("stage"), // 'pre_pmf' | 'scaling' | 'optimizing'
  whatBrokeLast90d: text("what_broke_last_90d"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uniqStageCurrent: uniqueIndex("uniq_stage_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

// =========================================================
// CHIỀU 3: FOUNDERS
// =========================================================
export const onboardFounders = strategySchema.table("onboard_founders", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  founderName: text("founder_name").notNull(),
  role: text("role"),
  superpower: text("superpower"),
  blindSpots: text("blind_spots"),
  archetype: text("archetype"), // 'product' | 'sales' | 'technical' | 'operator' | 'hybrid'
  whatKeepsUp: text("what_keeps_up"),
  cofounderCritique: text("cofounder_critique"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  idxFoundersCurrent: index("idx_founders_current").on(t.workspaceId, t.founderName).where(sql`${t.isCurrent} = true`),
}));

// =========================================================
// CHIỀU 4: TEAM & CULTURE
// =========================================================
export const onboardTeamCulture = strategySchema.table("onboard_team_culture", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  threeWords: text("three_words").array().default([]),
  lastRealConflict: text("last_real_conflict"),
  conflictResolution: text("conflict_resolution"),
  strongestLeader: text("strongest_leader"),
  weakestLeader: text("weakest_leader"),
  hasRealConflict: boolean("has_real_conflict"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uniqTeamCurrent: uniqueIndex("uniq_team_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

// =========================================================
// CHIỀU 5: MARKET & COMPETITION
// =========================================================
export const onboardMarket = strategySchema.table("onboard_market", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  marketDescription: text("market_description"),
  unfairAdvantage: text("unfair_advantage"),
  competitiveThreat: text("competitive_threat"),
  hasRealCompetition: boolean("has_real_competition"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uniqMarketCurrent: uniqueIndex("uniq_market_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

export const onboardCompetitors = strategySchema.table("onboard_competitors", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  marketId: bigint("market_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardMarket.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  whyWinning: text("why_winning"),
  threatLevel: text("threat_level"), // 'low' | 'medium' | 'high' | 'critical'
  displayOrder: integer("display_order").default(0),
});

// =========================================================
// CHIỀU 6: CHALLENGES
// =========================================================
export const onboardChallenges = strategySchema.table("onboard_challenges", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  priorityProduct: integer("priority_product"), // 1..5
  priorityGrowth: integer("priority_growth"),   // 1..5
  priorityPeople: integer("priority_people"),   // 1..5
  priorityMoney: integer("priority_money"),     // 1..5
  priorityOperations: integer("priority_operations"), // 1..5
  avoidedDecision: text("avoided_decision"),
  extraDayAnswer: text("extra_day_answer"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uniqChallengesCurrent: uniqueIndex("uniq_challenges_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

// =========================================================
// CHIỀU 7: GOALS & AMBITION
// =========================================================
export const onboardGoalsAmbition = strategySchema.table("onboard_goals_ambition", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  sessionId: bigint("session_id", { mode: "bigint" })
    .notNull()
    .references(() => onboardSessions.id),
  goal12MonthsText: text("goal_12_months_text"),
  goal36MonthsText: text("goal_36_months_text"),
  exitOrientation: text("exit_orientation"), // 'exit' | 'build_forever' | 'undecided'
  personalSuccessDefinition: text("personal_success_definition"),
  notCaptured: text("not_captured").array().default([]),
  isCurrent: boolean("is_current").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uniqAmbitionCurrent: uniqueIndex("uniq_ambition_current").on(t.workspaceId).where(sql`${t.isCurrent} = true`),
}));

// =========================================================
// REVIEW CADENCE (BSC-style)
// =========================================================
export const onboardReviewCadence = strategySchema.table("onboard_review_cadence", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  dimension: text("dimension").notNull(), // 'identity' | 'stage_scale' | 'founder' | 'team_culture' | 'market' | 'challenges' | 'goals_ambition'
  cadence: text("cadence").notNull(), // 'slow' | 'medium' | 'fast' | 'event'
  intervalDays: integer("interval_days"),
  lastReviewedAt: timestamp("last_reviewed_at", { withTimezone: true }),
  nextDueAt: timestamp("next_due_at", { withTimezone: true }),
});
