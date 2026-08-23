import { text, bigint, timestamp, doublePrecision, jsonb, varchar, integer, boolean } from "drizzle-orm/pg-core";
import { projects, strategySchema } from "./operations";

// 1. Stage Policies
export const stagePolicies = strategySchema.table("stage_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  stageKey: varchar("stage_key", { length: 50 }).notNull(),
  requirements: jsonb("requirements").default([]).notNull(),
  minimumEvidenceScore: doublePrecision("minimum_evidence_score").default(0.0).notNull(),
  blockingRiskRules: jsonb("blocking_risk_rules").default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 2. Stage Transitions
export const stageTransitions = strategySchema.table("stage_transitions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  fromStage: varchar("from_stage", { length: 50 }).notNull(),
  toStage: varchar("to_stage", { length: 50 }).notNull(),
  policyId: bigint("policy_id", { mode: "bigint" }).references(() => stagePolicies.id, { onDelete: "set null" }),
  allowed: boolean("allowed").default(true).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 3. Assumptions
export const assumptions = strategySchema.table("assumptions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  statement: text("statement").notNull(),
  importance: integer("importance").default(1).notNull(),
  uncertainty: integer("uncertainty").default(1).notNull(),
  riskScore: doublePrecision("risk_score").default(1.0).notNull(),
  status: varchar("status", { length: 50 }).default("untested").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 4. Experiments
export const experiments = strategySchema.table("experiments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  assumptionId: bigint("assumption_id", { mode: "bigint" }).references(() => assumptions.id, { onDelete: "set null" }),
  hypothesis: text("hypothesis").notNull(),
  method: text("method").notNull(),
  successCriteria: text("success_criteria").notNull(),
  budget: doublePrecision("budget").default(0.0).notNull(),
  ownerWorkforceMemberId: bigint("owner_workforce_member_id", { mode: "bigint" }),
  status: varchar("status", { length: 50 }).default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 5. Evidence
export const evidence = strategySchema.table("evidence", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  experimentId: bigint("experiment_id", { mode: "bigint" }).references(() => experiments.id, { onDelete: "set null" }),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  sourceType: varchar("source_type", { length: 50 }).notNull(),
  claim: text("claim").notNull(),
  strength: doublePrecision("strength").default(0.0).notNull(),
  confidence: doublePrecision("confidence").default(0.0).notNull(),
  supportsOrRefutes: varchar("supports_or_refutes", { length: 20 }).default("supports").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 6. Interviews
export const interviews = strategySchema.table("interviews", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  contactRef: bigint("contact_ref", { mode: "bigint" }), // Reference to commercial.contacts (loose coupling)
  notes: text("notes").notNull(),
  conductedAt: timestamp("conducted_at", { withTimezone: true }).defaultNow().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 7. Discovery Signals
export const discoverySignals = strategySchema.table("discovery_signals", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  signalType: varchar("signal_type", { length: 50 }).notNull(),
  payload: jsonb("payload").default({}).notNull(),
  source: text("source").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 8. Gate Evaluations
export const gateEvaluations = strategySchema.table("gate_evaluations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  stagePolicyId: bigint("stage_policy_id", { mode: "bigint" }).references(() => stagePolicies.id, { onDelete: "set null" }),
  requirementsMet: boolean("requirements_met").default(false).notNull(),
  evidenceScore: doublePrecision("evidence_score").default(0.0).notNull(),
  blockingRisks: jsonb("blocking_risks").default([]).notNull(),
  result: varchar("result", { length: 50 }).default("pending").notNull(),
  rationale: text("rationale").default("").notNull(),
  humanOverride: boolean("human_override").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 9. Decision Records
export const decisionRecords = strategySchema.table("decision_records", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  gateEvaluationId: bigint("gate_evaluation_id", { mode: "bigint" }).references(() => gateEvaluations.id, { onDelete: "set null" }),
  decision: varchar("decision", { length: 50 }).notNull(),
  actorWorkforceMemberId: bigint("actor_workforce_member_id", { mode: "bigint" }),
  evidenceSnapshot: jsonb("evidence_snapshot").default({}).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 10. Next Action Candidates
export const nextActionCandidates = strategySchema.table("next_action_candidates", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  source: varchar("source", { length: 50 }).notNull(),
  score: doublePrecision("score").default(0.0).notNull(),
  rationale: text("rationale").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 11. Next Action Rankings
export const nextActionRankings = strategySchema.table("next_action_rankings", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  candidateId: bigint("candidate_id", { mode: "bigint" }).notNull().references(() => nextActionCandidates.id, { onDelete: "cascade" }),
  rank: integer("rank").notNull(),
  llmRerankNote: text("llm_rerank_note"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
