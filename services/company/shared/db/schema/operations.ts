import { pgSchema, text, bigint, timestamp, doublePrecision, jsonb, varchar, integer, boolean, uniqueIndex, index, primaryKey, foreignKey, date, uuid, numeric } from "drizzle-orm/pg-core";

export const operatingSchema = pgSchema("operating");
export const strategySchema = pgSchema("strategy");

export const initiatives = strategySchema.table("initiatives", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  status: text("status").default("active").notNull(),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  description: text("description"),
  intendedOutcome: text("intended_outcome"),
  startDate: timestamp("start_date", { withTimezone: true }),
  targetDate: timestamp("target_date", { withTimezone: true }),
  milestones: jsonb("milestones").default([]).notNull(),
  approvalStatus: text("approval_status").default("DRAFT").notNull(), // DRAFT | PENDING_APPROVAL | APPROVED | REJECTED | CLOSED
  approvedByMemberId: bigint("approved_by_member_id", { mode: "bigint" }),
  approvedAt: timestamp("approved_at", { withTimezone: true }),
  decisionId: bigint("decision_id", { mode: "bigint" }),
  settingsRevision: integer("settings_revision"),
  revision: integer("revision").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_initiatives_id_workspace").on(t.id, t.workspaceId),
}));


export const tasks = operatingSchema.table("tasks", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
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
  weeklyCommitmentId: bigint("weekly_commitment_id", { mode: "bigint" }).references(() => weeklyCommitments.id, { onDelete: "set null" }),
  sourceActionId: text("source_action_id"),
  sourceRevision: integer("source_revision").default(1).notNull(),
  revision: integer("revision").default(1).notNull(),
  sortKey: doublePrecision("sort_key"),
  assigneeMemberId: bigint("assignee_member_id", { mode: "bigint" }),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  executionMode: text("execution_mode"),
  function: text("function"),
  // Con trỏ tới Outcome Contract đang hiệu lực (migration 51). NULL cho task
  // lịch sử chưa remediate — không backfill contract giả.
  activeOutcomeContractId: bigint("active_outcome_contract_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_tasks_id_workspace").on(t.id, t.workspaceId),
}));

// Outcome Contract theo task (spec §6, migration 51). Revision APPEND-only;
// tối đa một CONFIRMED "đang hiệu lực" cho mỗi task.
export const taskOutcomeContracts = operatingSchema.table("task_outcome_contracts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  revision: integer("revision").default(1).notNull(),
  status: varchar("status", { length: 20 }).default("DRAFT").notNull(), // DRAFT | CONFIRMED | SUPERSEDED
  outcomeType: varchar("outcome_type", { length: 20 }).notNull(), // DIRECT_KR | ENABLING_KR | VALIDATION | BAU
  expectedOutcome: text("expected_outcome").notNull(),
  acceptanceCriteria: jsonb("acceptance_criteria").default({}).notNull(),
  expectedEvidenceRefs: jsonb("expected_evidence_refs").default([]).notNull(),
  measurementPlan: jsonb("measurement_plan"),
  impactHypothesis: text("impact_hypothesis").notNull(),
  serviceObjective: text("service_objective"),
  primaryKrId: bigint("primary_kr_id", { mode: "bigint" }).references(() => keyResults.id, { onDelete: "set null" }),
  initiativeId: bigint("initiative_id", { mode: "bigint" }).references(() => initiatives.id, { onDelete: "set null" }),
  proposedByAgentInstanceId: text("proposed_by_agent_instance_id"),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  supersedesContractId: bigint("supersedes_contract_id", { mode: "bigint" }),
  changeReason: text("change_reason"),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixTaskRevision: uniqueIndex("uix_task_outcome_contracts_task_revision").on(t.taskId, t.revision),
  ixWsTask: index("ix_task_outcome_contracts_ws_task").on(t.workspaceId, t.taskId, t.status),
}));

export const taskOutcomeKrLinks = operatingSchema.table("task_outcome_kr_links", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  contractId: bigint("contract_id", { mode: "bigint" }).notNull().references(() => taskOutcomeContracts.id, { onDelete: "cascade" }),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).notNull().references(() => keyResults.id, { onDelete: "cascade" }),
  relationType: varchar("relation_type", { length: 20 }).notNull(), // DIRECT | ENABLING | VALIDATION
  isPrimary: boolean("is_primary").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixContractKr: uniqueIndex("uix_task_outcome_kr_links_contract_kr").on(t.contractId, t.keyResultId),
}));

// Work package = đơn vị queue; attempt = đơn vị quy trách nhiệm (spec §7,
// migration 52). Company IDs Snowflake BIGINT; ref Agent Platform là opaque TEXT.
export const taskWorkPackages = operatingSchema.table("task_work_packages", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  outcomeContractId: bigint("outcome_contract_id", { mode: "bigint" }).notNull().references(() => taskOutcomeContracts.id),
  title: text("title"),
  objective: text("objective").notNull(),
  inputRefs: jsonb("input_refs").default([]).notNull(),
  outputContract: jsonb("output_contract").default({}).notNull(),
  acceptanceRubric: jsonb("acceptance_rubric").default({}).notNull(),
  requestedByManagerId: bigint("requested_by_manager_id", { mode: "bigint" }),
  assignedAgentInstanceId: text("assigned_agent_instance_id").notNull(),
  requestedPriority: varchar("requested_priority", { length: 4 }).notNull(),
  effectivePriority: varchar("effective_priority", { length: 4 }).notNull(),
  priorityReason: text("priority_reason"),
  status: varchar("status", { length: 30 }).default("QUEUED").notNull(),
  dependencyIds: jsonb("dependency_ids").default([]).notNull(),
  reviewDueAt: timestamp("review_due_at", { withTimezone: true }),
  budgetLimit: numeric("budget_limit"),
  idempotencyKey: text("idempotency_key"),
  version: integer("version").default(1).notNull(),
  queuedAt: timestamp("queued_at", { withTimezone: true }).defaultNow().notNull(),
  dueAt: timestamp("due_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixQueue: index("ix_task_work_packages_queue").on(
    t.workspaceId, t.status, t.effectivePriority, t.dueAt, t.queuedAt
  ),
  ixTask: index("ix_task_work_packages_task").on(t.workspaceId, t.taskId),
}));

export const workPackageAttempts = operatingSchema.table("work_package_attempts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  workPackageId: bigint("work_package_id", { mode: "bigint" }).notNull().references(() => taskWorkPackages.id, { onDelete: "cascade" }),
  sequenceNo: integer("sequence_no").notNull(),
  assignedAgentInstanceId: text("assigned_agent_instance_id").notNull(),
  assignmentSnapshot: jsonb("assignment_snapshot"),
  specSnapshot: jsonb("spec_snapshot"),
  runId: text("run_id"),
  status: varchar("status", { length: 30 }).default("ACTIVE").notNull(),
  startedAt: timestamp("started_at", { withTimezone: true }).defaultNow().notNull(),
  endedAt: timestamp("ended_at", { withTimezone: true }),
  endedReason: text("ended_reason"),
}, (t) => ({
  uixSeq: uniqueIndex("uix_work_package_attempts_seq").on(t.workPackageId, t.sequenceNo),
}));

export const workPackageEvents = operatingSchema.table("work_package_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  workPackageId: bigint("work_package_id", { mode: "bigint" }).notNull().references(() => taskWorkPackages.id, { onDelete: "cascade" }),
  eventType: text("event_type").notNull(),
  actorKind: text("actor_kind").notNull(),
  actorId: text("actor_id"),
  beforeJson: jsonb("before_json"),
  afterJson: jsonb("after_json"),
  reason: text("reason"),
  correlationId: text("correlation_id"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixWp: index("ix_work_package_events_wp").on(t.workPackageId, t.createdAt),
}));

// Task Result (append-only revision) + Outcome Analysis pipeline (spec §8,
// migration 53). Không cột nào ghi KR.actualValue.
export const taskResults = operatingSchema.table("task_results", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  contractId: bigint("contract_id", { mode: "bigint" }).notNull().references(() => taskOutcomeContracts.id),
  resultRevision: integer("result_revision").notNull(),
  submittedByKind: varchar("submitted_by_kind", { length: 16 }).notNull(),
  submittedById: text("submitted_by_id"),
  workAttemptIds: jsonb("work_attempt_ids").default([]).notNull(),
  summary: text("summary").notNull(),
  structuredOutputs: jsonb("structured_outputs").default({}).notNull(),
  artifactRefs: jsonb("artifact_refs").default([]).notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  claimedMeasurements: jsonb("claimed_measurements").default({}).notNull(),
  blockers: jsonb("blockers").default([]).notNull(),
  idempotencyKey: text("idempotency_key"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixTaskRevision: uniqueIndex("uix_task_results_task_revision").on(t.taskId, t.resultRevision),
}));

export const outcomeAnalysisRequests = operatingSchema.table("outcome_analysis_requests", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  taskResultId: bigint("task_result_id", { mode: "bigint" }).notNull().references(() => taskResults.id, { onDelete: "cascade" }),
  contractId: bigint("contract_id", { mode: "bigint" }).notNull().references(() => taskOutcomeContracts.id),
  contractRevision: integer("contract_revision").notNull(),
  analysisKind: varchar("analysis_kind", { length: 32 }).notNull(),
  analysisPolicy: varchar("analysis_policy", { length: 20 }).notNull(),
  status: varchar("status", { length: 32 }).default("QUEUED").notNull(),
  selectedAgentInstanceId: text("selected_agent_instance_id"),
  selectedAssignmentId: text("selected_assignment_id"),
  selectedRunId: text("selected_run_id"),
  skillId: text("skill_id"),
  skillVersion: text("skill_version"),
  definitionHash: text("definition_hash"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixIdem: uniqueIndex("uix_outcome_analysis_requests_idem").on(
    t.workspaceId, t.taskResultId, t.analysisKind, t.contractRevision
  ),
}));

export const outcomeAssessments = operatingSchema.table("outcome_assessments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  requestId: bigint("request_id", { mode: "bigint" }).notNull().references(() => outcomeAnalysisRequests.id, { onDelete: "cascade" }),
  taskResultId: bigint("task_result_id", { mode: "bigint" }).notNull().references(() => taskResults.id, { onDelete: "cascade" }),
  contractId: bigint("contract_id", { mode: "bigint" }).notNull().references(() => taskOutcomeContracts.id),
  agentInstanceId: text("agent_instance_id").notNull(),
  assignmentId: text("assignment_id").notNull(),
  runId: text("run_id").notNull(),
  skillId: text("skill_id").notNull(),
  skillVersion: text("skill_version").notNull(),
  definitionHash: text("definition_hash").notNull(),
  rubricVersion: text("rubric_version"),
  evidenceUsedRefs: jsonb("evidence_used_refs").default([]).notNull(),
  missingEvidenceRefs: jsonb("missing_evidence_refs").default([]).notNull(),
  expectedVsActual: jsonb("expected_vs_actual").default({}).notNull(),
  criterionScores: jsonb("criterion_scores").default({}).notNull(),
  confidence: doublePrecision("confidence"),
  riskFlags: jsonb("risk_flags").default([]).notNull(),
  causalLimits: jsonb("causal_limits").default([]).notNull(),
  nextActionProposals: jsonb("next_action_proposals").default([]).notNull(),
  recommendation: varchar("recommendation", { length: 24 }).notNull(),
  status: varchar("status", { length: 16 }).default("READY").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixResult: index("ix_outcome_assessments_result").on(t.taskResultId, t.status),
}));

// Review bất biến của manager/founder + priority override event (spec §7-8,
// migration 54). Không auto-accept.
export const workPackageReviews = operatingSchema.table("work_package_reviews", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  workPackageId: bigint("work_package_id", { mode: "bigint" }).notNull().references(() => taskWorkPackages.id, { onDelete: "cascade" }),
  workAttemptId: bigint("work_attempt_id", { mode: "bigint" }).references(() => workPackageAttempts.id, { onDelete: "set null" }),
  reviewerMemberId: bigint("reviewer_member_id", { mode: "bigint" }),
  reviewerKind: varchar("reviewer_kind", { length: 16 }).default("manager").notNull(),
  artifactVersionRef: text("artifact_version_ref").notNull(),
  decision: varchar("decision", { length: 16 }).notNull(), // ACCEPT | REWORK | REJECT
  rubricScores: jsonb("rubric_scores").default({}).notNull(),
  reasonCode: text("reason_code").notNull(),
  narrative: text("narrative"),
  supersedesReviewId: bigint("supersedes_review_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixWp: index("ix_work_package_reviews_wp").on(t.workPackageId, t.createdAt),
}));

export const taskOutcomeReviews = operatingSchema.table("task_outcome_reviews", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  taskResultId: bigint("task_result_id", { mode: "bigint" }).notNull().references(() => taskResults.id, { onDelete: "cascade" }),
  assessmentId: bigint("assessment_id", { mode: "bigint" }).references(() => outcomeAssessments.id, { onDelete: "set null" }),
  expectedResultRevision: integer("expected_result_revision").notNull(),
  reviewerMemberId: bigint("reviewer_member_id", { mode: "bigint" }),
  decision: varchar("decision", { length: 16 }).notNull(),
  reasonCode: text("reason_code").notNull(),
  narrative: text("narrative"),
  supersedesReviewId: bigint("supersedes_review_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixResult: index("ix_task_outcome_reviews_result").on(t.taskResultId, t.createdAt),
}));

export const workPackagePriorityEvents = operatingSchema.table("work_package_priority_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  workPackageId: bigint("work_package_id", { mode: "bigint" }).notNull().references(() => taskWorkPackages.id, { onDelete: "cascade" }),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  requestedPriority: varchar("requested_priority", { length: 4 }).notNull(),
  priorEffectivePriority: varchar("prior_effective_priority", { length: 4 }).notNull(),
  newEffectivePriority: varchar("new_effective_priority", { length: 4 }).notNull(),
  reason: text("reason").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixWp: index("ix_work_package_priority_events_wp").on(t.workPackageId, t.createdAt),
}));

export const krContributionAssessments = operatingSchema.table("kr_contribution_assessments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  assessmentId: bigint("assessment_id", { mode: "bigint" }).notNull().references(() => outcomeAssessments.id, { onDelete: "cascade" }),
  krLinkId: bigint("kr_link_id", { mode: "bigint" }).references(() => taskOutcomeKrLinks.id, { onDelete: "set null" }),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).references(() => keyResults.id, { onDelete: "set null" }),
  state: varchar("state", { length: 24 }).default("PROPOSED").notNull(),
  claimedEffect: jsonb("claimed_effect").default({}).notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  causalConfidence: doublePrecision("causal_confidence"),
  verifiedByMemberId: bigint("verified_by_member_id", { mode: "bigint" }),
  verifiedAt: timestamp("verified_at", { withTimezone: true }),
  reason: text("reason"),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixAssessment: index("ix_kr_contribution_assessments_assessment").on(t.assessmentId, t.state),
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
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  why: text("why"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  status: text("status").default("draft").notNull(),
  publishedByMemberId: bigint("published_by_member_id", { mode: "bigint" }),
  publishedAt: timestamp("published_at", { withTimezone: true }),
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
  scoringType: varchar("scoring_type", { length: 50 }).default("LINEAR_INCREASE").notNull(),
  metricContractVersion: integer("metric_contract_version"),
  evidenceRefs: jsonb("evidence_refs"),
  status: text("status").default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_key_results_id_workspace").on(t.id, t.workspaceId),
}));


export const twelveWeekCycles = operatingSchema.table("twelve_week_cycles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  theme: varchar("theme", { length: 255 }),
  visionStatement: text("vision_statement").default("").notNull(),
  stageAtStart: varchar("stage_at_start", { length: 50 }).default("S1_PROBLEM_VALIDATION").notNull(),
  currentWeek: integer("current_week").default(1).notNull(),
  durationWeeks: integer("duration_weeks").default(12).notNull(),
  overallExecutionScore: doublePrecision("overall_execution_score").default(0.0).notNull(),
  displayName: varchar("display_name", { length: 255 }),
  timezone: varchar("timezone", { length: 100 }).default("UTC").notNull(),
  startLocalDate: date("start_local_date"),
  endLocalDateExclusive: date("end_local_date_exclusive"),
  revision: integer("revision").default(1).notNull(),
  calendarState: varchar("calendar_state", { length: 50 }).default("READY").notNull(),
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
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  cycleId: bigint("cycle_id", { mode: "bigint" }).notNull().references(() => twelveWeekCycles.id, { onDelete: "cascade" }),
  weekNo: integer("week_no").notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  focus: text("focus"),
  mission: text("mission"),
  executionScore: doublePrecision("execution_score"),
  outcomeScore: doublePrecision("outcome_score"),
  reflection: text("reflection"),
  decisionId: bigint("decision_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const weeklyCommitments = operatingSchema.table("weekly_commitments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  weeklyPlanId: bigint("weekly_plan_id", { mode: "bigint" }).notNull().references(() => weeklyPlans.id, { onDelete: "cascade" }),
  initiativeId: bigint("initiative_id", { mode: "bigint" }).references(() => initiatives.id, { onDelete: "set null" }),
  title: varchar("title", { length: 255 }).notNull(),
  status: varchar("status", { length: 50 }).default("todo").notNull(),
  plannedEffort: varchar("planned_effort", { length: 50 }),
  commitmentOwnerType: varchar("commitment_owner_type", { length: 50 }).default("FOUNDER"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  purposeType: varchar("purpose_type", { length: 50 }).default("KR").notNull(),
  purposeRef: text("purpose_ref"),
  doneCriteria: jsonb("done_criteria"),
  committedAt: timestamp("committed_at", { withTimezone: true }),
  decisionId: bigint("decision_id", { mode: "bigint" }),
  executionMode: varchar("execution_mode", { length: 50 }).default("MANUAL"),
  sourceActionId: varchar("source_action_id", { length: 255 }),
  sourceRevision: integer("source_revision").default(1).notNull(),
  revision: integer("revision").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const cycleRevisions = operatingSchema.table("cycle_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  cycleId: bigint("cycle_id", { mode: "bigint" }).notNull().references(() => twelveWeekCycles.id, { onDelete: "cascade" }),
  revision: integer("revision").notNull(),
  beforeState: jsonb("before_state").notNull(),
  afterState: jsonb("after_state").notNull(),
  reason: text("reason"),
  actorId: text("actor_id"),
  actorKind: text("actor_kind").default("user").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixCycleRevision: uniqueIndex("uix_cycle_revisions_cycle_revision").on(t.cycleId, t.revision),
}));

export const cycleKeyResults = operatingSchema.table("cycle_key_results", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  cycleId: bigint("cycle_id", { mode: "bigint" }).notNull().references(() => twelveWeekCycles.id, { onDelete: "cascade" }),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).notNull().references(() => keyResults.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  pk: primaryKey({ columns: [t.workspaceId, t.cycleId, t.keyResultId] }),
}));

export const commitmentKeyResults = operatingSchema.table("commitment_key_results", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  commitmentId: bigint("commitment_id", { mode: "bigint" }).notNull().references(() => weeklyCommitments.id, { onDelete: "cascade" }),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).notNull().references(() => keyResults.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  pk: primaryKey({ columns: [t.workspaceId, t.commitmentId, t.keyResultId] }),
}));

export const initiativeKeyResults = strategySchema.table("initiative_key_results", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  initiativeId: bigint("initiative_id", { mode: "bigint" }).notNull().references(() => initiatives.id, { onDelete: "cascade" }),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).notNull().references(() => keyResults.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  pk: primaryKey({ columns: [t.workspaceId, t.initiativeId, t.keyResultId] }),
}));


export const krObservations = operatingSchema.table("kr_observations", {
  id: uuid("id").primaryKey().defaultRandom(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  krId: bigint("kr_id", { mode: "bigint" }).notNull().references(() => keyResults.id, { onDelete: "cascade" }),
  valueDecimal: numeric("value_decimal", { precision: 18, scale: 4 }).notNull(),
  measurementAt: timestamp("measurement_at", { withTimezone: true }).notNull(),
  windowStart: timestamp("window_start", { withTimezone: true }),
  windowEnd: timestamp("window_end", { withTimezone: true }),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  sourceRef: text("source_ref"),
  recordedBy: bigint("recorded_by", { mode: "bigint" }),
  metricContractVersion: integer("metric_contract_version"),
  idempotencyKey: text("idempotency_key"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixIdempotency: uniqueIndex("uix_kr_observations_ws_kr_idempotency").on(t.workspaceId, t.krId, t.idempotencyKey),
}));

export const projects = strategySchema.table("projects", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  // M4 §3 — Project lifecycle P0..P6, độc lập với Workspace W0..W5.
  lifecycleStage: varchar("lifecycle_stage", { length: 50 }).default("P0_DISCOVERY").notNull(),
  stageVersion: integer("stage_version").default(0).notNull(),
  stageEnteredAt: timestamp("stage_entered_at", { withTimezone: true }),
  currentGate: varchar("current_gate", { length: 50 }),
  status: varchar("status", { length: 50 }).default("ACTIVE").notNull(), // ACTIVE|PAUSED|COMPLETED|ARCHIVED
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  projectType: varchar("project_type", { length: 50 }),
  strategicPriority: varchar("strategic_priority", { length: 50 }),
  founderAttentionBudget: doublePrecision("founder_attention_budget"),
  // Startup Core: portfolio đã gỡ khỏi model. Cột `portfolio_id` còn trong
  // baseline 001 như cột trơ (không FK, không code path) — giữ để khớp migration.
  portfolioId: bigint("portfolio_id", { mode: "bigint" }),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixIdWorkspace: uniqueIndex("uix_projects_id_workspace").on(t.id, t.workspaceId),
}));

// M4 §3 — lịch sử chuyển lifecycle stage của Project (append-only, do người
// thực hiện). Không progression tự động bởi framework/agent/background job.
export const projectLifecycleEvents = strategySchema.table("project_lifecycle_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  fromStage: varchar("from_stage", { length: 50 }).notNull(),
  toStage: varchar("to_stage", { length: 50 }).notNull(),
  fromStageVersion: integer("from_stage_version").notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  rationale: text("rationale"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixProjCreated: index("ix_project_lifecycle_events_proj").on(t.projectId, t.createdAt),
}));

// 14. Task Execution Records (Phase 5 / Release E)
export const taskExecutionRecords = operatingSchema.table("task_execution_records", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  runId: text("run_id"),
  toolCallId: text("tool_call_id"),
  capabilityId: text("capability_id").notNull(),
  triggeredByKind: text("triggered_by_kind").notNull(), // 'agent' | 'founder' | 'workflow' | 'system'
  decisionRecordId: bigint("decision_record_id", { mode: "bigint" }),
  status: text("status").default("SUCCESS").notNull(), // 'SUCCESS' | 'FAILED'
  errorDetails: jsonb("error_details"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// 17b. Execution Plans (WGA — Weekly Goal → Agent Execution)
// Bản nháp "kế hoạch triển khai" agent đề xuất từ mục tiêu tuần; founder duyệt
// theo lô rồi mới materialize thành operating.tasks. autonomy_class ở item là
// single source of truth cho worker task-executor.
export const executionPlans = operatingSchema.table("execution_plans", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  weeklyPlanId: bigint("weekly_plan_id", { mode: "bigint" }).references(() => weeklyPlans.id, { onDelete: "set null" }),
  goalText: text("goal_text").notNull(),
  status: text("status").default("draft").notNull(), // 'draft' | 'accepted' | 'superseded' | 'rejected'
  origin: text("origin").notNull(), // 'command_center' | 'chat'
  originRef: text("origin_ref"),
  runId: text("run_id"),
  acceptedByMemberId: bigint("accepted_by_member_id", { mode: "bigint" }),
  acceptedAt: timestamp("accepted_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const executionPlanItems = operatingSchema.table("execution_plan_items", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  planId: bigint("plan_id", { mode: "bigint" }).notNull().references(() => executionPlans.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  decisionReason: text("decision_reason").notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  ownerAgentProfile: text("owner_agent_profile"), // 'operations' | 'finance' | 'marketing' | null (=founder)
  expectedCapability: text("expected_capability"),
  autonomyClass: text("autonomy_class").notNull(), // 'AUTO' | 'NEEDS_APPROVAL' | 'FOUNDER_ONLY'
  autonomyClassSource: text("autonomy_class_source").notNull(), // 'classifier_default' | 'tenant_policy' | 'founder_override'
  priority: text("priority").default("medium"),
  dependsOnItemIds: jsonb("depends_on_item_ids").default([]),
  sortKey: doublePrecision("sort_key"),
  materializedTaskId: bigint("materialized_task_id", { mode: "bigint" }).references(() => tasks.id, { onDelete: "set null" }),
  status: text("status").default("proposed").notNull(), // 'proposed' | 'accepted' | 'dropped'
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// 17c. Workspace Execution Settings (WGA #2 — kill-switch per-workspace cho sweep)
export const workspaceExecutionSettings = operatingSchema.table("workspace_execution_settings", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).primaryKey(),
  sweepEnabled: boolean("sweep_enabled").default(true).notNull(),
  updatedBy: bigint("updated_by", { mode: "bigint" }),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// 17d. Workspace Capability Policy (WGA #3 — override lớp quyền hạn per-capability)
export const workspaceCapabilityPolicy = operatingSchema.table(
  "workspace_capability_policy",
  {
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    capabilityId: text("capability_id").notNull(),
    decision: text("decision").notNull(), // 'ALLOW' | 'REQUIRE_APPROVAL' | 'DENY'
    updatedBy: bigint("updated_by", { mode: "bigint" }),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => ({
    pk: primaryKey({ columns: [t.workspaceId, t.capabilityId] }),
  })
);

// 18. Runtime Source Signals (Full MVP - Immutable upstream agent signals projection)
export const runtimeSourceSignals = operatingSchema.table("runtime_source_signals", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  sourceKind: text("source_kind").notNull(),
  sourceId: text("source_id").notNull(),
  sequence: bigint("sequence", { mode: "bigint" }).notNull(),
  state: text("state").notNull(),
  observedAt: timestamp("observed_at", { withTimezone: true }).notNull(),
  correlationId: text("correlation_id").notNull(),
  payloadHash: text("payload_hash").notNull(),
  receivedAt: timestamp("received_at", { withTimezone: true }).defaultNow().notNull(),
});

// 19. Runtime Snoozes (Full MVP - Actor-specific snooze overlay)
export const runtimeSnoozes = operatingSchema.table("runtime_snoozes", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }).notNull(),
  sourceKind: text("source_kind").notNull(),
  sourceId: text("source_id").notNull(),
  snoozedUntil: timestamp("snoozed_until", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// 20. Cycle Reviews (operating.cycle_reviews)
export const cycleReviews = operatingSchema.table(
  "cycle_reviews",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    projectId: bigint("project_id", { mode: "bigint" }).references(() => projects.id, { onDelete: "set null" }),
    cycleId: bigint("cycle_id", { mode: "bigint" }).notNull().references(() => twelveWeekCycles.id, { onDelete: "cascade" }),
    kind: varchar("kind", { length: 50 }).notNull(), // 'WEEKLY' | 'MID_CYCLE' | 'END_CYCLE'
    scheduledWeekNo: integer("scheduled_week_no").notNull(),
    scheduledAt: timestamp("scheduled_at", { withTimezone: true }),
    status: varchar("status", { length: 50 }).default("SCHEDULED").notNull(), // 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'SKIPPED' | 'SUPERSEDED'
    krSnapshots: jsonb("kr_snapshots").default([]).notNull(),
    initiativeSnapshots: jsonb("initiative_snapshots").default([]).notNull(),
    decisionId: bigint("decision_id", { mode: "bigint" }),
    conclusion: text("conclusion"),
    conductedByMemberId: bigint("conducted_by_member_id", { mode: "bigint" }),
    conductedAt: timestamp("conducted_at", { withTimezone: true }),
    settingsRevision: integer("settings_revision"),
    revision: integer("revision").default(1).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
    deletedAt: timestamp("deleted_at", { withTimezone: true }),
  },
  (t) => ({
    ixWorkspaceCycle: index("ix_cycle_reviews_workspace_cycle").on(t.workspaceId, t.cycleId, t.scheduledWeekNo, t.kind),
    uixActiveSlot: uniqueIndex("uix_cycle_reviews_active_slot").on(t.cycleId, t.kind, t.scheduledWeekNo),
  })
);


// --- COSA Automation MVP (Task 1) -------------------------------------------
// docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
// Columns match services/company/operations/migrations/003_cosa_automation_mvp.up.sql
// exactly. All FKs stay inside the Company DB.

export const automationDefinitions = operatingSchema.table("automation_definitions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  automationKey: text("automation_key").notNull(),
  currentRevisionId: bigint("current_revision_id", { mode: "bigint" }),
  lifecycleState: text("lifecycle_state").default("DRAFT").notNull(), // DRAFT | PUBLISHED | SUSPENDED | RETIRED
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
}, (t) => ({
  uixWsKey: uniqueIndex("uix_automation_definitions_ws_key").on(t.workspaceId, t.automationKey),
  ixWorkspace: index("idx_automation_definitions_workspace").on(t.workspaceId),
}));

export const automationRevisions = operatingSchema.table("automation_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  definitionId: bigint("definition_id", { mode: "bigint" }).notNull().references(() => automationDefinitions.id, { onDelete: "cascade" }),
  revisionNo: integer("revision_no").notNull(),
  revisionHash: text("revision_hash").notNull(),
  configurationJson: jsonb("configuration_json").default({}).notNull(),
  triggerContractJson: jsonb("trigger_contract_json").default({}).notNull(),
  capabilityIds: jsonb("capability_ids").default([]).notNull(),
  evidenceContractJson: jsonb("evidence_contract_json").default({}).notNull(),
  autonomyClass: text("autonomy_class").default("read_only").notNull(), // read_only | draft_only | gated_effect
  approvalContractJson: jsonb("approval_contract_json").default({}).notNull(),
  pinnedDependenciesJson: jsonb("pinned_dependencies_json").default({}).notNull(),
  effectivePolicyRevision: text("effective_policy_revision"),
  createdBy: text("created_by").notNull(),
  publishedAt: timestamp("published_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixDefinitionNo: uniqueIndex("uix_automation_revisions_definition_no").on(t.definitionId, t.revisionNo),
  ixWsDefinition: index("idx_automation_revisions_ws_definition").on(t.workspaceId, t.definitionId),
}));

export const automationInvocations = operatingSchema.table("automation_invocations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  definitionId: bigint("definition_id", { mode: "bigint" }).notNull().references(() => automationDefinitions.id, { onDelete: "cascade" }),
  revisionId: bigint("revision_id", { mode: "bigint" }).notNull().references(() => automationRevisions.id, { onDelete: "cascade" }),
  automationKey: text("automation_key").notNull(),
  revisionNo: integer("revision_no").notNull(),
  revisionHash: text("revision_hash").notNull(),
  idempotencyKey: text("idempotency_key").notNull(),
  triggerKind: text("trigger_kind").notNull(), // manual | schedule | business_event
  triggerIdentity: text("trigger_identity").notNull(),
  callerPrincipal: text("caller_principal").notNull(),
  source: text("source").notNull(),
  businessScopeJson: jsonb("business_scope_json").default({}).notNull(),
  validatedInputRef: text("validated_input_ref"),
  fingerprintHash: text("fingerprint_hash").notNull(),
  state: text("state").default("REQUESTED").notNull(),
  blockedReason: text("blocked_reason"),
  agentRunId: text("agent_run_id"),
  correlationId: text("correlation_id").notNull(),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixIdentity: uniqueIndex("uix_automation_invocations_identity").on(t.workspaceId, t.revisionId, t.idempotencyKey),
  ixWsState: index("idx_automation_invocations_ws_state").on(t.workspaceId, t.state),
  ixWsRun: index("idx_automation_invocations_ws_run").on(t.workspaceId, t.agentRunId),
}));

export const automationInvocationEvents = operatingSchema.table("automation_invocation_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  invocationId: bigint("invocation_id", { mode: "bigint" }).notNull().references(() => automationInvocations.id, { onDelete: "cascade" }),
  seq: integer("seq").notNull(),
  eventType: text("event_type").notNull(),
  payloadJson: jsonb("payload_json").default({}).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixSeq: uniqueIndex("uix_automation_invocation_events_seq").on(t.workspaceId, t.invocationId, t.seq),
}));

export const projectAgentAssignmentStateEnum = operatingSchema.enum("project_agent_assignment_state", [
  "TEMPLATE",
  "ACTIVE",
  "PAUSED",
  "RETIRED",
]);

export const projectAgentAssignments = operatingSchema.table("project_agent_assignments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  profileKey: text("profile_key").notNull(),
  state: projectAgentAssignmentStateEnum("state").default("TEMPLATE").notNull(),
  agentWorkforceMemberId: bigint("agent_workforce_member_id", { mode: "bigint" }),
  specId: text("spec_id"),
  specVersion: text("spec_version"),
  specHash: text("spec_hash"),
  activationPolicySnapshot: jsonb("activation_policy_snapshot"),
  version: integer("version").default(1).notNull(),
  disabledReason: text("disabled_reason"),
  createdBy: bigint("created_by", { mode: "bigint" }),
  activatedBy: bigint("activated_by", { mode: "bigint" }),
  pausedBy: bigint("paused_by", { mode: "bigint" }),
  activatedAt: timestamp("activated_at", { withTimezone: true }),
  pausedAt: timestamp("paused_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixWsProjKey: uniqueIndex("uix_project_agent_assignments_ws_proj_key").on(t.workspaceId, t.projectId, t.profileKey),
  fkProject: foreignKey({
    columns: [t.projectId, t.workspaceId],
    foreignColumns: [projects.id, projects.workspaceId],
    name: "fk_project_agent_assignments_proj_ws",
  }).onDelete("cascade"),
  idxWsProj: index("idx_project_agent_assignments_ws_proj").on(t.workspaceId, t.projectId),
}));

export const projectAgentAssignmentEvents = operatingSchema.table("project_agent_assignment_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  assignmentId: bigint("assignment_id", { mode: "bigint" }).notNull().references(() => projectAgentAssignments.id, { onDelete: "cascade" }),
  eventType: text("event_type").notNull(),
  fromState: projectAgentAssignmentStateEnum("from_state"),
  toState: projectAgentAssignmentStateEnum("to_state").notNull(),
  assignmentVersion: integer("assignment_version").notNull(),
  actorId: bigint("actor_id", { mode: "bigint" }).notNull(),
  occurredAt: timestamp("occurred_at", { withTimezone: true }).defaultNow().notNull(),
  eventPayload: jsonb("event_payload").default({}).notNull(),
}, (t) => ({
  idxAssignmentOccurred: index("idx_project_agent_assignment_events_assignment").on(t.assignmentId, t.occurredAt),
}));

export const projectExecutiveBoardSettings = operatingSchema.table("project_executive_board_settings", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  presetKey: varchar("preset_key", { length: 64 }).notNull(),
  version: integer("version").default(1).notNull(),
  selectedBy: bigint("selected_by", { mode: "bigint" }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  pkWsProj: primaryKey({ columns: [t.workspaceId, t.projectId] }),
  fkProject: foreignKey({
    columns: [t.projectId, t.workspaceId],
    foreignColumns: [projects.id, projects.workspaceId],
    name: "fk_project_executive_board_settings_proj_ws",
  }).onDelete("cascade"),
}));

export const projectExecutiveRoleActivations = operatingSchema.table("project_executive_role_activations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  roleKey: varchar("role_key", { length: 64 }).notNull(),
  state: varchar("state", { length: 32 }).notNull(), // 'ACTIVE' | 'DISABLED'
  activationSource: varchar("activation_source", { length: 64 }).notNull(), // 'STARTUP_CORE_PRESET' | 'FOUNDER'
  version: integer("version").default(1).notNull(),
  actorId: bigint("actor_id", { mode: "bigint" }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixWsProjRole: uniqueIndex("uix_project_executive_role_activations_ws_proj_role").on(t.workspaceId, t.projectId, t.roleKey),
  fkProject: foreignKey({
    columns: [t.projectId, t.workspaceId],
    foreignColumns: [projects.id, projects.workspaceId],
    name: "fk_project_executive_role_activations_proj_ws",
  }).onDelete("cascade"),
  idxWsProj: index("idx_project_executive_role_activations_proj").on(t.workspaceId, t.projectId),
}));

export const projectExecutiveRoleActivationEvents = operatingSchema.table("project_executive_role_activation_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  roleKey: varchar("role_key", { length: 64 }).notNull(),
  activationId: bigint("activation_id", { mode: "bigint" }).notNull().references(() => projectExecutiveRoleActivations.id, { onDelete: "cascade" }),
  fromState: varchar("from_state", { length: 32 }),
  toState: varchar("to_state", { length: 32 }).notNull(),
  actorId: bigint("actor_id", { mode: "bigint" }).notNull(),
  version: integer("version").notNull(),
  payload: jsonb("payload").default({}).notNull(),
  occurredAt: timestamp("occurred_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  idxActivationOccurred: index("idx_project_exec_role_act_events_act").on(t.activationId, t.occurredAt),
}));

export const projectExecutiveDeliberations = operatingSchema.table("project_executive_deliberations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  state: varchar("state", { length: 32 }).default("DRAFT").notNull(),
  activeFrameVersion: integer("active_frame_version").default(0).notNull(),
  version: integer("version").default(1).notNull(),
  createdBy: bigint("created_by", { mode: "bigint" }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  fkProject: foreignKey({
    columns: [t.projectId, t.workspaceId],
    foreignColumns: [projects.id, projects.workspaceId],
    name: "fk_project_executive_deliberations_proj_ws",
  }).onDelete("cascade"),
  idxWsProj: index("idx_project_exec_deliberations_proj").on(t.workspaceId, t.projectId),
}));

export const projectExecutiveDeliberationFrames = operatingSchema.table("project_executive_deliberation_frames", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  deliberationId: bigint("deliberation_id", { mode: "bigint" }).notNull().references(() => projectExecutiveDeliberations.id, { onDelete: "cascade" }),
  frameVersion: integer("frame_version").notNull(),
  question: text("question").notNull(),
  deliberationType: varchar("deliberation_type", { length: 64 }).default("STRATEGY").notNull(),
  deadline: timestamp("deadline", { withTimezone: true }),
  decisionOwnerId: bigint("decision_owner_id", { mode: "bigint" }).notNull(),
  selectedRoles: jsonb("selected_roles").default([]).notNull(),
  evidenceSources: jsonb("evidence_sources").default([]).notNull(),
  criticRequired: boolean("critic_required").default(false).notNull(),
  redactedContextRef: text("redacted_context_ref"),
  framedBy: bigint("framed_by", { mode: "bigint" }).notNull(),
  framedAt: timestamp("framed_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixDelibFrameVer: uniqueIndex("uix_proj_exec_delib_frames_ver").on(t.deliberationId, t.frameVersion),
}));

export const projectExecutiveDeliberationDecisions = operatingSchema.table("project_executive_deliberation_decisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  deliberationId: bigint("deliberation_id", { mode: "bigint" }).notNull().references(() => projectExecutiveDeliberations.id, { onDelete: "cascade" }),
  decisionType: varchar("decision_type", { length: 32 }).notNull(),
  decisionVersion: integer("decision_version").default(1).notNull(),
  actorId: bigint("actor_id", { mode: "bigint" }).notNull(),
  notes: text("notes"),
  modifications: jsonb("modifications").default({}),
  decidedAt: timestamp("decided_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixDelibDecisionVer: uniqueIndex("uix_proj_exec_delib_decisions_ver").on(t.deliberationId, t.decisionVersion),
}));

export const projectExecutiveDeliberationAnalyses = operatingSchema.table("project_executive_deliberation_analyses", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  deliberationId: bigint("deliberation_id", { mode: "bigint" }).notNull().references(() => projectExecutiveDeliberations.id, { onDelete: "cascade" }),
  frameVersion: integer("frame_version").notNull(),
  roleKey: varchar("role_key", { length: 64 }).notNull(),
  runId: text("run_id").notNull(),
  status: varchar("status", { length: 32 }).notNull(),
  descriptor: jsonb("descriptor").default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixDelibAnalysesRole: uniqueIndex("uix_proj_exec_delib_analyses_role").on(t.deliberationId, t.frameVersion, t.roleKey),
}));

// Product Decision Dossier: bản ghi nghiệp vụ Founder-reviewed, append-only,
// scoped theo workspace + project. Agent context chỉ được đọc snapshot đã
// redact (evidence_refs chỉ chứa source ref/classification/redacted excerpt),
// KHÔNG BAO GIỜ được tạo/confirm/append revision — guard tại service layer.
export const productDecisionDossiers = operatingSchema.table("product_decision_dossiers", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  status: varchar("status", { length: 24 }).default("DRAFT").notNull(), // DRAFT | CONFIRMED | SUPERSEDED
  currentVersion: integer("current_version").default(1).notNull(),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixProj: index("idx_product_decision_dossiers_proj").on(t.workspaceId, t.projectId, t.updatedAt),
  // 1 dossier duy nhất mỗi Project (xem migration 010 để biết lý do không
  // cần partial index theo status).
  uixProject: uniqueIndex("uix_product_decision_dossiers_project").on(t.workspaceId, t.projectId),
}));

export const productDecisionDossierRevisions = operatingSchema.table("product_decision_dossier_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  dossierId: bigint("dossier_id", { mode: "bigint" }).notNull().references(() => productDecisionDossiers.id, { onDelete: "cascade" }),
  version: integer("version").notNull(),
  status: varchar("status", { length: 24 }).notNull(), // DRAFT | CONFIRMED
  assumptions: jsonb("assumptions").default([]).notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  reasonCode: text("reason_code"),
  narrative: text("narrative"),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  supersedesRevisionId: bigint("supersedes_revision_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixVer: uniqueIndex("uix_product_decision_dossier_revisions_ver").on(t.dossierId, t.version),
  ixDossier: index("idx_product_decision_dossier_revisions_dossier").on(t.dossierId, t.createdAt),
}));

// People Risk Dossier: bản ghi nghiệp vụ Founder-reviewed, append-only,
// scoped theo workspace + project — mirror cấu trúc Product Decision Dossier
// ở trên nhưng data model là People Risk (capacity_bands/risk_signals đã
// classify, KHÔNG BAO GIỜ chứa CV, compensation, protected characteristics,
// performance note, health data hay contact PII). Validation allowlist thực
// hiện tại service layer (people-risk-dossier.service.ts).
export const peopleRiskDossiers = operatingSchema.table("people_risk_dossiers", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  status: varchar("status", { length: 24 }).default("DRAFT").notNull(), // DRAFT | CONFIRMED | SUPERSEDED
  currentVersion: integer("current_version").default(1).notNull(),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixProj: index("idx_people_risk_dossiers_proj").on(t.workspaceId, t.projectId, t.updatedAt),
  // 1 dossier duy nhất mỗi Project (xem migration 012).
  uixProject: uniqueIndex("uix_people_risk_dossiers_project").on(t.workspaceId, t.projectId),
}));

export const peopleRiskDossierRevisions = operatingSchema.table("people_risk_dossier_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  dossierId: bigint("dossier_id", { mode: "bigint" }).notNull().references(() => peopleRiskDossiers.id, { onDelete: "cascade" }),
  version: integer("version").notNull(),
  status: varchar("status", { length: 24 }).notNull(), // DRAFT | CONFIRMED
  capacityBands: jsonb("capacity_bands").default([]).notNull(),
  riskSignals: jsonb("risk_signals").default([]).notNull(),
  sourceRefs: jsonb("source_refs").default([]).notNull(),
  // Fixed enum (xem CHECK constraint ở migration 012), KHÔNG free text — dossier
  // này không có bất kỳ trường narrative/free-text nào trên write path.
  reasonCode: varchar("reason_code", { length: 32 }).notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  supersedesRevisionId: bigint("supersedes_revision_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixVer: uniqueIndex("uix_people_risk_dossier_revisions_ver").on(t.dossierId, t.version),
  ixDossier: index("idx_people_risk_dossier_revisions_dossier").on(t.dossierId, t.createdAt),
}));

// Security Posture Dossier: bản ghi nghiệp vụ Founder-reviewed, append-only,
// scoped theo workspace + project — mirror cấu trúc People Risk Dossier ở
// trên nhưng data model là Security Posture (controls đã classify theo
// category/state, findings theo severity/category/sourceRef). KHÔNG BAO GIỜ
// chứa password, token, private key, raw HTTP header, raw vulnerability
// payload hay infrastructure topology — validation allowlist + deep secret
// scan thực hiện tại service layer (security-posture.service.ts).
export const securityPostureDossiers = operatingSchema.table("security_posture_dossiers", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  status: varchar("status", { length: 24 }).default("DRAFT").notNull(), // DRAFT | CONFIRMED | SUPERSEDED
  currentVersion: integer("current_version").default(1).notNull(),
  createdByMemberId: bigint("created_by_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixProj: index("idx_security_posture_dossiers_proj").on(t.workspaceId, t.projectId, t.updatedAt),
  // 1 dossier duy nhất mỗi Project (xem migration 014).
  uixProject: uniqueIndex("uix_security_posture_dossiers_project").on(t.workspaceId, t.projectId),
}));

export const securityPostureDossierRevisions = operatingSchema.table("security_posture_dossier_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  dossierId: bigint("dossier_id", { mode: "bigint" }).notNull().references(() => securityPostureDossiers.id, { onDelete: "cascade" }),
  version: integer("version").notNull(),
  status: varchar("status", { length: 24 }).notNull(), // DRAFT | CONFIRMED
  controls: jsonb("controls").default([]).notNull(),
  findings: jsonb("findings").default([]).notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  severity: varchar("severity", { length: 16 }).notNull(), // LOW | MEDIUM | HIGH | CRITICAL (aggregate)
  // Fixed enum (xem CHECK constraint ở migration 014), KHÔNG free text —
  // dossier này không có bất kỳ trường narrative/free-text nào trên write path.
  reasonCode: varchar("reason_code", { length: 32 }).notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  supersedesRevisionId: bigint("supersedes_revision_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixVer: uniqueIndex("uix_security_posture_dossier_revisions_ver").on(t.dossierId, t.version),
  ixDossier: index("idx_security_posture_dossier_revisions_dossier").on(t.dossierId, t.createdAt),
}));


