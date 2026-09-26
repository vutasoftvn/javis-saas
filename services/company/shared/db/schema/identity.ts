import { pgSchema, text, bigint, integer, timestamp, primaryKey, boolean, uuid, jsonb, index, unique } from "drizzle-orm/pg-core";

export const coreSchema = pgSchema("core");

export const identityWorkspaces = coreSchema.table("workspaces", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  name: text("name").notNull(),
  // M2 §6 — DNS identity toàn cầu khi link platform; nullable khi local-only chưa link.
  slug: text("slug"),
  // M2 §1 — enum khớp shared/contracts/enums.json.
  status: text("status").default("ACTIVE").notNull(), // ACTIVE | ARCHIVED | SUSPENDED
  runtimeMode: text("runtime_mode").default("LOCAL_ONLY").notNull(),
  syncPolicy: text("sync_policy").default("CONTROL_METADATA_ONLY").notNull(),
  syncStatus: text("sync_status").default("LOCAL_ONLY").notNull(),
  stageVersion: integer("stage_version").default(0).notNull(), // M4 §2 — CAS cho transition
  primaryLegalEntityId: bigint("primary_legal_entity_id", { mode: "bigint" }),
  // M4 §1 — lifecycle stage của Workspace (enum W0_IDEA..W5_SCALE), độc lập với Project stage.
  lifecycleStage: text("lifecycle_stage").default("W0_IDEA").notNull(),
  platformCompanyId: text("platform_company_id").unique(),
  platformWorkspaceId: text("platform_workspace_id").unique(),
  stageEnteredAt: timestamp("stage_entered_at", { withTimezone: true }),
  // Định hướng workspace (Vision/Mission/Core Values) — 1 bộ tuỳ chọn per workspace.
  vision: text("vision"),
  mission: text("mission"),
  coreValues: text("core_values"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  archivedAt: timestamp("archived_at", { withTimezone: true }),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// M4 §1 — lịch sử chuyển lifecycle stage của Workspace (append-only, do người
// thực hiện). KHÔNG phải progression tự động; chỉ ghi nhận transition thủ công.
export const identityWorkspaceLifecycleEvents = coreSchema.table("workspace_lifecycle_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  fromStage: text("from_stage").notNull(),
  toStage: text("to_stage").notNull(),
  fromStageVersion: integer("from_stage_version").notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  rationale: text("rationale"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixWsCreated: index("ix_workspace_lifecycle_events_ws").on(t.workspaceId, t.createdAt),
}));

// M2 §6 / ADR-SLUG-001 — lịch sử giữ chỗ + rename slug. workspace_id bất biến.
export const identityWorkspaceSlugs = coreSchema.table("workspace_slugs", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" })
    .notNull()
    .references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  slug: text("slug").notNull(),
  status: text("status").default("ACTIVE").notNull(), // ACTIVE | REDIRECT | RELEASED
  redirectToSlug: text("redirect_to_slug"),
  reservedAt: timestamp("reserved_at", { withTimezone: true }).defaultNow().notNull(),
  releasedAt: timestamp("released_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const identityUserProjections = coreSchema.table("user_projections", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  email: text("email").unique(),
  phone: text("phone").unique(),
  displayName: text("display_name"),
  status: text("status").default("active").notNull(),
  platformUserId: text("platform_user_id").unique(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const identityWorkspaceMemberships = coreSchema.table("workspace_memberships", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  userId: bigint("user_id", { mode: "bigint" }).notNull().references(() => identityUserProjections.id, { onDelete: "cascade" }),
  role: text("role").default("member").notNull(),
  membershipState: text("membership_state").default("active").notNull(),
  sourceMembershipVersion: bigint("source_membership_version", { mode: "number" }).default(1).notNull(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  // Local session có auth_time trước mốc này không dùng được cho membership (migration 006).
  sessionNotBefore: timestamp("session_not_before", { withTimezone: true }),
  platformMembershipId: text("platform_membership_id"),
  sourceUpdatedAt: timestamp("source_updated_at", { withTimezone: true }),
  syncedAt: timestamp("synced_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const identityMembershipEventInbox = coreSchema.table("membership_event_inbox", {
  eventId: text("event_id").primaryKey(),
  organizationId: text("organization_id").notNull(),
  userId: text("user_id").notNull(),
  membershipVersion: bigint("membership_version", { mode: "number" }).notNull(),
  status: text("status").notNull(),
  processedAt: timestamp("processed_at", { withTimezone: true }).defaultNow().notNull(),
});

// Task 3 (AI compliance hardening) — chống replay cho scoped COSA->Company
// delegation JWT (mint_company_delegation ở apps/cosa/auth/jwt.py). Mỗi jti
// chỉ được "consume" đúng 1 lần cho 1 cặp (run_id, capability_id) trước khi
// thực hiện side effect (EXTERNAL call hoặc mutation) — không dùng cho
// READ-only snapshot resolution (idempotent tự nhiên, chỉ cần exp hợp lệ).
// Composite PK thật (jti, capabilityId) — `jti` chứa ĐÚNG JWT ID từ claim
// (không phải chuỗi tổng hợp "${jti}:${capabilityId}"). 1 delegation có thể
// khai báo nhiều capability_ids; mỗi capability được "consume" đúng 1 lần,
// độc lập với các capability khác của cùng delegation — composite PK diễn
// đạt đúng ràng buộc đó ở tầng DB thay vì chỉ ở cách app-layer build key.
export const identityCosaDelegationReplays = coreSchema.table(
  "cosa_delegation_replays",
  {
    jti: text("jti").notNull(),
    capabilityId: text("capability_id").notNull(),
    workspaceId: text("workspace_id").notNull(),
    runId: text("run_id").notNull(),
    consumedAt: timestamp("consumed_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    pk: primaryKey({ columns: [table.jti, table.capabilityId] }),
  })
);

export const identityWorkforceMembers = coreSchema.table("workforce_members", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  memberType: text("member_type").notNull(),
  humanUserId: bigint("human_user_id", { mode: "bigint" }).references(() => identityUserProjections.id, { onDelete: "cascade" }),
  agentSpecId: text("agent_spec_id"),
  agentSpecVersion: text("agent_spec_version"),
  managerMemberId: bigint("manager_member_id", { mode: "bigint" }),
  roleTitle: text("role_title").notNull(),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const corePermissionDefinitions = coreSchema.table("permission_definitions", {
  permissionKey: text("permission_key").primaryKey(),
  domain: text("domain").notNull(),
  description: text("description"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export type RoleMemberType = "HUMAN" | "AI_AGENT";
export type AuthorizationEnforcementMode = "SHADOW" | "ENFORCED";

export const coreWorkspaceRoles = coreSchema.table("workspace_roles", {
  id: uuid("id").primaryKey().defaultRandom(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  roleKey: text("role_key").notNull(),
  name: text("name").notNull(),
  isSystem: boolean("is_system").default(false).notNull(),
  allowedMemberTypes: text("allowed_member_types").array(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uqWorkspaceRoleKey: unique("uq_workspace_roles_key").on(t.workspaceId, t.roleKey),
}));

export const coreRolePermissions = coreSchema.table("role_permissions", {
  roleId: uuid("role_id").notNull().references(() => coreWorkspaceRoles.id, { onDelete: "cascade" }),
  permissionKey: text("permission_key").notNull().references(() => corePermissionDefinitions.permissionKey, { onDelete: "cascade" }),
  effect: text("effect").notNull(), // 'ALLOW' | 'DENY' | 'REQUIRE_APPROVAL'
  conditions: jsonb("conditions").default({}).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  pk: primaryKey({ columns: [t.roleId, t.permissionKey] }),
}));

export const coreMemberRoleAssignments = coreSchema.table("member_role_assignments", {
  id: uuid("id").primaryKey().defaultRandom(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  workforceMemberId: bigint("workforce_member_id", { mode: "bigint" }).notNull().references(() => identityWorkforceMembers.id, { onDelete: "cascade" }),
  roleId: uuid("role_id").notNull().references(() => coreWorkspaceRoles.id, { onDelete: "cascade" }),
  projectId: bigint("project_id", { mode: "bigint" }),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  validFrom: timestamp("valid_from", { withTimezone: true }).defaultNow().notNull(),
  validUntil: timestamp("valid_until", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  lookupIdx: index("idx_member_role_assignments_lookup").on(t.workspaceId, t.workforceMemberId),
}));

export const coreWorkspacePolicyVersions = coreSchema.table("workspace_policy_versions", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  version: integer("version").notNull(),
  policyHash: text("policy_hash").notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  reason: text("reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  pk: primaryKey({ columns: [t.workspaceId, t.version] }),
}));

export const coreWorkspaceAuthorizationStates = coreSchema.table("workspace_authorization_states", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).primaryKey().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  enforcementMode: text("enforcement_mode").default("SHADOW").notNull(),
  authorizationEpoch: integer("authorization_epoch").default(1).notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const coreCapabilityPermissionBindings = coreSchema.table("capability_permission_bindings", {
  capabilityId: text("capability_id").primaryKey(),
  permissionKey: text("permission_key").notNull().references(() => corePermissionDefinitions.permissionKey, { onDelete: "cascade" }),
  riskClass: text("risk_class").notNull(), // READ | INTERNAL_WRITE | EXTERNAL_WRITE | FINANCIAL | LEGAL | AUTHORITY
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const coreAgentCapabilityGrants = coreSchema.table("agent_capability_grants", {
  id: uuid("id").primaryKey().defaultRandom(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  agentWorkforceMemberId: bigint("agent_workforce_member_id", { mode: "bigint" }).notNull().references(() => identityWorkforceMembers.id, { onDelete: "cascade" }),
  capabilityId: text("capability_id").notNull().references(() => coreCapabilityPermissionBindings.capabilityId, { onDelete: "cascade" }),
  projectId: bigint("project_id", { mode: "bigint" }),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  constraints: jsonb("constraints").default({}).notNull(),
  validFrom: timestamp("valid_from", { withTimezone: true }).defaultNow().notNull(),
  validUntil: timestamp("valid_until", { withTimezone: true }),
  status: text("status").default("ACTIVE").notNull(),
  grantedByFounderMemberId: bigint("granted_by_founder_member_id", { mode: "bigint" }).notNull().references(() => identityWorkforceMembers.id, { onDelete: "cascade" }),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  revokeReason: text("revoke_reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  lookupIdx: index("idx_agent_capability_grants_lookup").on(t.workspaceId, t.agentWorkforceMemberId, t.capabilityId),
}));

export const coreAuthorizationEvents = coreSchema.table("authorization_events", {
  id: uuid("id").primaryKey().defaultRandom(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  eventType: text("event_type").notNull(),
  actorMemberId: bigint("actor_member_id", { mode: "bigint" }),
  targetMemberId: bigint("target_member_id", { mode: "bigint" }),
  capabilityId: text("capability_id"),
  roleId: uuid("role_id"),
  grantId: uuid("grant_id"),
  policyVersion: integer("policy_version"),
  authorizationEpoch: integer("authorization_epoch"),
  beforeHash: text("before_hash"),
  afterHash: text("after_hash"),
  reason: text("reason"),
  correlationId: text("correlation_id"),
  details: jsonb("details").default({}).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixWsCreated: index("ix_authorization_events_ws_created").on(t.workspaceId, t.createdAt),
}));

export const coreAgentAuthorizationTickets = coreSchema.table("agent_authorization_tickets", {
  id: uuid("id").primaryKey().defaultRandom(),
  ticketId: text("ticket_id").notNull().unique(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  runId: text("run_id").notNull(),
  toolCallId: text("tool_call_id").notNull(),
  checkpointRef: text("checkpoint_ref").notNull(),
  capabilityId: text("capability_id").notNull(),
  agentWorkforceMemberId: bigint("agent_workforce_member_id", { mode: "bigint" }).notNull().references(() => identityWorkforceMembers.id, { onDelete: "cascade" }),
  authorizationEpoch: integer("authorization_epoch").notNull(),
  status: text("status").default("ISSUED").notNull(), // ISSUED | CONSUMED | EXPIRED
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  consumedAt: timestamp("consumed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  ixTicketLookup: index("ix_agent_auth_tickets_lookup").on(t.workspaceId, t.runId, t.capabilityId),
}));

