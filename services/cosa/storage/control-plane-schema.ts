import { pgSchema, text, integer, boolean, timestamp, jsonb, bigint } from "drizzle-orm/pg-core";

// Wave 7 — Control Plane (ADR-CONTROLPLANE-001, ACCEPTED — implementation đã
// bắt đầu 2026-08-25, xem control-plane.handler.ts cho trạng thái consumer
// theo từng nhóm bảng: leases/scheduled_tasks đã có consumer production
// thật (apps/cosa/worker/main.py), missions/tasks/workers/watches/delivery
// vẫn chưa). Tách schema Postgres riêng `control_plane` (khác `cosa` dùng
// cho identity/license) để rõ ranh giới: đây là execution-plane/mission-task
// state, không phải business identity truth.
export const controlPlaneSchema = pgSchema("control_plane");

export const missions = controlPlaneSchema.table("missions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  tenantId: bigint("tenant_id", { mode: "bigint" }).notNull(),
  creatorId: bigint("creator_id", { mode: "bigint" }).notNull(),
  goal: text("goal").notNull(),
  status: text("status").default("active").notNull(),
  priority: integer("priority").default(0).notNull(),
  budgetCents: bigint("budget_cents", { mode: "bigint" }),
  deadline: timestamp("deadline", { withTimezone: true }),
  rootRunId: text("root_run_id"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
});

export const tasks = controlPlaneSchema.table("tasks", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  missionId: bigint("mission_id", { mode: "bigint" }).notNull().references(() => missions.id, { onDelete: "cascade" }),
  parentTaskId: bigint("parent_task_id", { mode: "bigint" }),
  description: text("description").notNull(),
  status: text("status").default("pending").notNull(),
  priority: integer("priority").default(0).notNull(),
  requirements: jsonb("requirements").default({}).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const assignments = controlPlaneSchema.table("assignments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  taskId: bigint("task_id", { mode: "bigint" }).notNull().references(() => tasks.id, { onDelete: "cascade" }),
  workerId: text("worker_id").notNull(),
  status: text("status").default("leased").notNull(),
  leaseUntil: timestamp("lease_until", { withTimezone: true }).notNull(),
  attemptNo: integer("attempt_no").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workers = controlPlaneSchema.table("workers", {
  id: text("id").primaryKey(),
  runtimeKind: text("runtime_kind").notNull(),
  endpoint: text("endpoint"),
  capabilities: jsonb("capabilities").default([]).notNull(),
  concurrencyLimit: integer("concurrency_limit").default(1).notNull(),
  trustTier: text("trust_tier").default("T0").notNull(),
  lastHeartbeatAt: timestamp("last_heartbeat_at", { withTimezone: true }),
  status: text("status").default("online").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// Thay packages/agent_core/runs/leases.py::RunLeaseManager (in-memory) —
// durable, chống split-brain thật giữa nhiều process.
export const runtimeLeases = controlPlaneSchema.table("runtime_leases", {
  runId: text("run_id").primaryKey(),
  workerId: text("worker_id").notNull().references(() => workers.id, { onDelete: "cascade" }),
  leaseToken: text("lease_token").notNull(),
  acquiredAt: timestamp("acquired_at", { withTimezone: true }).defaultNow().notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  heartbeatIntervalSec: integer("heartbeat_interval_sec").default(30).notNull(),
});

// Thay packages/agent_core/coordination/scheduler.py::RunScheduler (in-memory).
// attempt_count..dead_letter_reason: Phase 3 Durable Queue Recovery (xem
// migration 10_scheduled_tasks_durable_claims.up.sql) — claim atomic bằng
// fencing token (claim_token) + retry backoff + dead-letter khi vượt
// max_attempts, thay vì kẹt vĩnh viễn ở 'processing' khi worker chết.
export const scheduledTasks = controlPlaneSchema.table("scheduled_tasks", {
  id: text("id").primaryKey(),
  coalescingKey: text("coalescing_key"),
  targetSpecId: text("target_spec_id").notNull(),
  targetSpecKind: text("target_spec_kind").default("agent").notNull(),
  inputPayload: jsonb("input_payload").default({}).notNull(),
  runAt: timestamp("run_at", { withTimezone: true }).defaultNow().notNull(),
  status: text("status").default("scheduled").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  attemptCount: integer("attempt_count").default(0).notNull(),
  maxAttempts: integer("max_attempts").default(5).notNull(),
  claimedBy: text("claimed_by"),
  claimToken: text("claim_token"),
  claimedAt: timestamp("claimed_at", { withTimezone: true }),
  heartbeatAt: timestamp("heartbeat_at", { withTimezone: true }),
  visibilityTimeoutAt: timestamp("visibility_timeout_at", { withTimezone: true }),
  lastError: text("last_error"),
  nextRetryAt: timestamp("next_retry_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  deadLetterReason: text("dead_letter_reason"),
});

export const watches = controlPlaneSchema.table("watches", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  tenantId: bigint("tenant_id", { mode: "bigint" }).notNull(),
  kind: text("kind").notNull(),
  config: jsonb("config").default({}).notNull(),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const triggerPolicies = controlPlaneSchema.table("trigger_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  watchId: bigint("watch_id", { mode: "bigint" }).notNull().references(() => watches.id, { onDelete: "cascade" }),
  condition: jsonb("condition").default({}).notNull(),
  targetAgentSpecId: text("target_agent_spec_id").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const signalObservations = controlPlaneSchema.table("signal_observations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  watchId: bigint("watch_id", { mode: "bigint" }).notNull().references(() => watches.id, { onDelete: "cascade" }),
  dedupeKey: text("dedupe_key").notNull(),
  payload: jsonb("payload").default({}).notNull(),
  triggeredRunId: text("triggered_run_id"),
  observedAt: timestamp("observed_at", { withTimezone: true }).defaultNow().notNull(),
});

export const deliveryPolicies = controlPlaneSchema.table("delivery_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  tenantId: bigint("tenant_id", { mode: "bigint" }).notNull(),
  channel: text("channel").notNull(),
  config: jsonb("config").default({}).notNull(),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const deliveryAttempts = controlPlaneSchema.table("delivery_attempts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  deliveryPolicyId: bigint("delivery_policy_id", { mode: "bigint" })
    .notNull()
    .references(() => deliveryPolicies.id, { onDelete: "cascade" }),
  artifactRef: text("artifact_ref").notNull(),
  status: text("status").default("pending").notNull(),
  errorMessage: text("error_message"),
  attemptedAt: timestamp("attempted_at", { withTimezone: true }).defaultNow().notNull(),
});

export const costLedger = controlPlaneSchema.table("cost_ledger", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  tenantId: bigint("tenant_id", { mode: "bigint" }).notNull(),
  missionId: bigint("mission_id", { mode: "bigint" }),
  runId: text("run_id"),
  provider: text("provider").notNull(),
  model: text("model").notNull(),
  inputTokens: bigint("input_tokens", { mode: "bigint" }).default(BigInt(0)).notNull(),
  outputTokens: bigint("output_tokens", { mode: "bigint" }).default(BigInt(0)).notNull(),
  costCents: bigint("cost_cents", { mode: "bigint" }).default(BigInt(0)).notNull(),
  recordedAt: timestamp("recorded_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceConnectorInstallations = controlPlaneSchema.table("workspace_connector_installations", {
  id: text("id").primaryKey(),
  companyId: text("company_id").notNull(),
  workspaceId: text("workspace_id").notNull(),
  connectorKey: text("connector_key").notNull(),
  installedBy: text("installed_by").notNull(),
  status: text("status").default("enabled").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const connectorAuthorizations = controlPlaneSchema.table("connector_authorizations", {
  id: text("id").primaryKey(),
  installationId: text("installation_id")
    .notNull()
    .references(() => workspaceConnectorInstallations.id, { onDelete: "cascade" }),
  principalId: text("principal_id").notNull(),
  secretRef: text("secret_ref").notNull(),
  grantedScopes: jsonb("granted_scopes").default([]).notNull(),
  state: text("state").default("active").notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const sessionConnectorGrants = controlPlaneSchema.table("session_connector_grants", {
  id: text("id").primaryKey(),
  companyId: text("company_id").notNull(),
  workspaceId: text("workspace_id").notNull(),
  conversationId: text("conversation_id").notNull(),
  authorizationId: text("authorization_id")
    .notNull()
    .references(() => connectorAuthorizations.id, { onDelete: "cascade" }),
  grantedBy: text("granted_by").notNull(),
  allowedActions: jsonb("allowed_actions").default([]).notNull(),
  state: text("state").default("enabled").notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceScheduleDefinitions = controlPlaneSchema.table("workspace_schedule_definitions", {
  id: text("id").primaryKey(),
  companyId: text("company_id").notNull(),
  workspaceId: text("workspace_id").notNull(),
  createdBy: text("created_by").notNull(),
  scheduleKind: text("schedule_kind").notNull(),
  timezone: text("timezone").default("Asia/Ho_Chi_Minh").notNull(),
  runAt: timestamp("run_at", { withTimezone: true }),
  hour: integer("hour"),
  minute: integer("minute"),
  weekdays: jsonb("weekdays").default([]).notNull(),
  promptTemplate: text("prompt_template").notNull(),
  agentProfile: text("agent_profile").default("operations").notNull(),
  connectorGrantIds: jsonb("connector_grant_ids").default([]).notNull(),
  state: text("state").default("enabled").notNull(),
  nextRunAt: timestamp("next_run_at", { withTimezone: true }),
  lastRunAt: timestamp("last_run_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceScheduleExecutions = controlPlaneSchema.table("workspace_schedule_executions", {
  id: text("id").primaryKey(),
  definitionId: text("definition_id")
    .notNull()
    .references(() => workspaceScheduleDefinitions.id, { onDelete: "cascade" }),
  companyId: text("company_id").notNull(),
  workspaceId: text("workspace_id").notNull(),
  scheduledFor: timestamp("scheduled_for", { withTimezone: true }).notNull(),
  promptTemplateSnapshot: text("prompt_template_snapshot").notNull(),
  agentProfileSnapshot: text("agent_profile_snapshot").notNull(),
  connectorGrantIdsSnapshot: jsonb("connector_grant_ids_snapshot").default([]).notNull(),
  state: text("state").default("queued").notNull(),
  taskId: text("task_id"),
  conversationId: text("conversation_id"),
  runId: text("run_id"),
  error: text("error"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

