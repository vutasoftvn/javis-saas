import { text, bigint, timestamp, doublePrecision, jsonb, varchar, integer, boolean, primaryKey, numeric, date } from "drizzle-orm/pg-core";
import { projects, strategySchema, okrObjectives } from "./operations";


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

// 2. Stage Transition Policies (config edge/policy — KHÔNG phải history journal; xem workspaceStageTransitions)
export const stageTransitionPolicies = strategySchema.table("stage_transition_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  fromStage: varchar("from_stage", { length: 50 }).notNull(),
  toStage: varchar("to_stage", { length: 50 }).notNull(),
  policyId: bigint("policy_id", { mode: "bigint" }).references(() => stagePolicies.id, { onDelete: "set null" }),
  allowed: boolean("allowed").default(true).notNull(),
  // M4 §2 — versioned policy: journal ghi lại policy_version áp dụng cho từng transition.
  policyVersion: text("policy_version").default("v1").notNull(),
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
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  status: varchar("status", { length: 50 }).default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 5a. Evidence Ingestions (Idempotent source intake receipt)
export const evidenceIngestions = strategySchema.table("evidence_ingestions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  sourceSystem: varchar("source_system", { length: 50 }).notNull(),
  sourceRecordId: text("source_record_id").notNull(),
  sourcePayloadHash: text("source_payload_hash").notNull(),
  artifactRef: text("artifact_ref"),
  sourceUrl: text("source_url"),
  observedAt: timestamp("observed_at", { withTimezone: true }).notNull(),
  ingestedByMemberId: bigint("ingested_by_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 5. Evidence
export const evidence = strategySchema.table("evidence", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  experimentId: bigint("experiment_id", { mode: "bigint" }).references(() => experiments.id, { onDelete: "set null" }),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  evidenceIngestionId: bigint("evidence_ingestion_id", { mode: "bigint" }).references(() => evidenceIngestions.id, { onDelete: "set null" }),
  sourceType: varchar("source_type", { length: 50 }).notNull(),
  claim: text("claim").notNull(),
  strength: doublePrecision("strength").default(0.0).notNull(),
  confidence: doublePrecision("confidence").default(0.0).notNull(),
  supportsOrRefutes: varchar("supports_or_refutes", { length: 20 }).default("supports").notNull(),
  status: varchar("status", { length: 30 }).default("candidate").notNull(),
  reviewComment: text("review_comment"),
  reviewedByMemberId: bigint("reviewed_by_member_id", { mode: "bigint" }),
  reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
  artifactRef: text("artifact_ref"),
  sourceUrl: text("source_url"),
  sourceSystem: varchar("source_system", { length: 50 }),
  factOrInference: varchar("fact_or_inference", { length: 30 }).default("inference").notNull(),
  observedAt: timestamp("observed_at", { withTimezone: true }),
  freshUntil: timestamp("fresh_until", { withTimezone: true }),
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
  projectId: bigint("project_id", { mode: "bigint" }).references(() => projects.id, { onDelete: "cascade" }),
  gateEvaluationId: bigint("gate_evaluation_id", { mode: "bigint" }).references(() => gateEvaluations.id, { onDelete: "set null" }),
  decision: varchar("decision", { length: 50 }).notNull(),
  decisionType: text("decision_type"),
  createdByKind: text("created_by_kind"), // 'FOUNDER' | 'AI' | 'SYSTEM'
  createdByRef: text("created_by_ref"),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  regulationRefs: jsonb("regulation_refs").default([]).notNull(),
  confidence: numeric("confidence"),
  assumptions: jsonb("assumptions").default([]).notNull(),
  alternatives: jsonb("alternatives").default([]).notNull(),
  policyVersion: text("policy_version"),
  aiPromptVersion: text("ai_prompt_version"),
  founderDecision: text("founder_decision"), // 'accepted' | 'rejected' | 'deferred'
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  evidenceSnapshot: jsonb("evidence_snapshot").default({}).notNull(),
  decidedAt: timestamp("decided_at", { withTimezone: true }),
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

// 12. Venture Profiles
export const ventureProfiles = strategySchema.table("venture_profiles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().unique(),
  problemStatement: text("problem_statement"),
  targetCustomer: text("target_customer"),
  industry: text("industry"),
  geography: text("geography"),
  currency: text("currency").default("VND"),
  timezone: text("timezone").default("Asia/Ho_Chi_Minh"),
  founderGoal: varchar("founder_goal", { length: 50 }),
  initialRunwayMonths: integer("initial_runway_months"),
  stageEnteredAt: timestamp("stage_entered_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// 13. Workspace Stage Transitions Journal (history — M4 §1 đổi tên từ venture_stage_transitions)
export const workspaceStageTransitions = strategySchema.table("workspace_stage_transitions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  fromStage: varchar("from_stage", { length: 50 }).notNull(),
  toStage: varchar("to_stage", { length: 50 }).notNull(),
  reason: text("reason").notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  overrideFlag: boolean("override_flag").default(false).notNull(),
  // M4 §2 — CAS + provenance: version workspace lúc transition, nguồn, role actor,
  // policy_version áp dụng, ref approval override, và snapshot evidence/eval kèm quyết định.
  stageVersionFrom: integer("stage_version_from"),
  source: text("source").default("manual").notNull(), // manual | autonomous | api | system
  actorRole: text("actor_role"),
  policyVersion: text("policy_version"),
  overrideApprovalRef: text("override_approval_ref"),
  evidenceSnapshot: jsonb("evidence_snapshot").default({}).notNull(),
  evaluationResult: jsonb("evaluation_result"),
  decidedAt: timestamp("decided_at", { withTimezone: true }).defaultNow().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 13b. Project Stage Transition Policies (M4 §3 — riêng cho Project P0..P6, KHÔNG dùng chung Workspace)
export const projectStageTransitionPolicies = strategySchema.table("project_stage_transition_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  fromStage: varchar("from_stage", { length: 50 }).notNull(),
  toStage: varchar("to_stage", { length: 50 }).notNull(),
  allowed: boolean("allowed").default(true).notNull(),
  policyVersion: text("policy_version").default("v1").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 13c. Project Stage Transitions Journal (M4 §3)
export const projectStageTransitions = strategySchema.table("project_stage_transitions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  fromStage: varchar("from_stage", { length: 50 }).notNull(),
  toStage: varchar("to_stage", { length: 50 }).notNull(),
  reason: text("reason").notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  actorRole: text("actor_role"),
  overrideFlag: boolean("override_flag").default(false).notNull(),
  overrideApprovalRef: text("override_approval_ref"),
  source: text("source").default("manual").notNull(),
  stageVersionFrom: integer("stage_version_from"),
  policyVersion: text("policy_version"),
  evidenceSnapshot: jsonb("evidence_snapshot").default({}).notNull(),
  evaluationResult: jsonb("evaluation_result"),
  decidedAt: timestamp("decided_at", { withTimezone: true }).defaultNow().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 14. Next Best Actions (Phase 5 / Release E)
export const nextBestActions = strategySchema.table("next_best_actions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  source: text("source").notNull(), // 'evidence' | 'finance' | 'legal' | 'stage'
  recommendation: text("recommendation").notNull(),
  priority: integer("priority").default(1).notNull(),
  dueBy: date("due_by"),
  status: text("status").default("PROPOSED").notNull(), // 'PROPOSED' | 'ACCEPTED' | 'REJECTED' | 'DONE'
  capabilityRequired: text("capability_required"),
  decisionReason: text("decision_reason").notNull(),
  contextSnapshot: jsonb("context_snapshot").default({}).notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  regulationRefs: jsonb("regulation_refs").default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// 15. Weekly Reviews (Phase 5 / Release E)
export const weeklyReviews = strategySchema.table("weekly_reviews", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  weekStartDate: date("week_start_date").notNull(),
  summary: text("summary").notNull(),
  stageAssessment: text("stage_assessment"),
  cashSummary: text("cash_summary"),
  obligationsSummary: text("obligations_summary"),
  actionProposals: jsonb("action_proposals").default([]).notNull(),
  status: text("status").default("DRAFT").notNull(), // 'DRAFT' | 'COMPLETED'
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// 16. Pilot Runs (P3 Pilot Readiness / Tranche B1)
export const pilotRuns = strategySchema.table("pilot_runs", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  experimentId: bigint("experiment_id", { mode: "bigint" }).references(() => experiments.id, { onDelete: "set null" }),
  status: varchar("status", { length: 50 }).default("DRAFT").notNull(),
  designPartnerEvidenceRefs: jsonb("design_partner_evidence_refs").default([]).notNull(),
  metricContractArtifactRef: text("metric_contract_artifact_ref"),
  instrumentationArtifactRef: text("instrumentation_artifact_ref"),
  onboardingArtifactRef: text("onboarding_artifact_ref"),
  supportEscalationArtifactRef: text("support_escalation_artifact_ref"),
  rollbackArtifactRef: text("rollback_artifact_ref"),
  releaseOwnerMemberId: bigint("release_owner_member_id", { mode: "bigint" }).notNull(),
  approvedByMemberId: bigint("approved_by_member_id", { mode: "bigint" }),
  approvalRef: text("approval_ref"),
  approvedAt: timestamp("approved_at", { withTimezone: true }),
  activatedByMemberId: bigint("activated_by_member_id", { mode: "bigint" }),
  activatedAt: timestamp("activated_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  cancelledAt: timestamp("cancelled_at", { withTimezone: true }),
  cancellationReason: text("cancellation_reason"),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 17. Metric Contracts (Tranche B2 / Task 1)
export const metricContracts = strategySchema.table("metric_contracts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  metricKey: varchar("metric_key", { length: 100 }).notNull(),
  displayName: text("display_name").notNull(),
  unit: varchar("unit", { length: 50 }).notNull(),
  numeratorDefinition: text("numerator_definition").notNull(),
  denominatorDefinition: text("denominator_definition").notNull(),
  cohortDefinition: text("cohort_definition").notNull(),
  sourceMapping: jsonb("source_mapping").default({}).notNull(),
  cadence: varchar("cadence", { length: 50 }).notNull(),
  freshUntil: timestamp("fresh_until", { withTimezone: true }),
  guardrail: text("guardrail"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  decisionUse: text("decision_use").notNull(),
  status: varchar("status", { length: 50 }).default("DRAFT").notNull(),
  version: integer("version").default(1).notNull(),
  approvalRef: text("approval_ref"),
  changeRationale: text("change_rationale"),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  publishedByMemberId: bigint("published_by_member_id", { mode: "bigint" }),
  publishedAt: timestamp("published_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 18. Metric Snapshots (Tranche B2 / Task 2)
export const metricSnapshots = strategySchema.table("metric_snapshots", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  contractVersionId: bigint("contract_version_id", { mode: "bigint" }).notNull().references(() => metricContracts.id, { onDelete: "cascade" }),
  sourceSystem: varchar("source_system", { length: 50 }).notNull(),
  sourceWindow: varchar("source_window", { length: 50 }).notNull(),
  sourceRecordId: text("source_record_id").notNull(),
  payloadHash: text("payload_hash").notNull(),
  observedAt: timestamp("observed_at", { withTimezone: true }).notNull(),
  capturedAt: timestamp("captured_at", { withTimezone: true }).defaultNow().notNull(),
  value: doublePrecision("value").notNull(),
  numerator: doublePrecision("numerator"),
  denominator: doublePrecision("denominator"),
  qualityStatus: varchar("quality_status", { length: 30 }).default("VALID").notNull(),
  qualityChecks: jsonb("quality_checks").default({}).notNull(),
  evidenceIngestionId: bigint("evidence_ingestion_id", { mode: "bigint" }).references(() => evidenceIngestions.id, { onDelete: "set null" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 19. PMF Scoreboard Runs (Tranche B2 / Task 3)
export const pmfScoreboardRuns = strategySchema.table("pmf_scoreboard_runs", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  contractVersionIds: jsonb("contract_version_ids").default([]).notNull(),
  inputSnapshotIds: jsonb("input_snapshot_ids").default([]).notNull(),
  reviewedEvidenceIds: jsonb("reviewed_evidence_ids").default([]).notNull(),
  policyVersion: text("policy_version").default("v1").notNull(),
  scoreComponents: jsonb("score_components").default([]).notNull(),
  missingDataFlags: jsonb("missing_data_flags").default([]).notNull(),
  reliabilityFlags: jsonb("reliability_flags").default([]).notNull(),
  calculationHash: text("calculation_hash").notNull(),
  result: varchar("result", { length: 50 }).notNull(),
  humanReviewState: jsonb("human_review_state").default({}).notNull(),
  calculatedAt: timestamp("calculated_at", { withTimezone: true }).defaultNow().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 20. Maturity Assessments (Tranche B2 / Task 3)
export const maturityAssessments = strategySchema.table("maturity_assessments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  scoreboardRunId: bigint("scoreboard_run_id", { mode: "bigint" }).references(() => pmfScoreboardRuns.id, { onDelete: "set null" }),
  dimensions: jsonb("dimensions").default({}).notNull(),
  assessedAt: timestamp("assessed_at", { withTimezone: true }).defaultNow().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 21. Strategy Canvases (Full MVP)
export const canvases = strategySchema.table("canvases", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: text("name").notNull(),
  description: text("description"),
  currentRevisionId: bigint("current_revision_id", { mode: "bigint" }),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// 22. Strategy Canvas Revisions (Full MVP)
export const canvasRevisions = strategySchema.table("canvas_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  canvasId: bigint("canvas_id", { mode: "bigint" }).notNull().references(() => canvases.id, { onDelete: "cascade" }),
  parentRevisionId: bigint("parent_revision_id", { mode: "bigint" }),
  content: jsonb("content").notNull(),
  status: text("status").notNull(), // 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED'
  origin: text("origin").notNull(), // 'USER' | 'MODEL_DRAFT'
  sourceRefs: jsonb("source_refs").default([]).notNull(),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  reviewedByMemberId: bigint("reviewed_by_member_id", { mode: "bigint" }),
  reviewNote: text("review_note"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
});
