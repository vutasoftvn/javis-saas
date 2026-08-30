import { pgSchema, text, bigint, integer, timestamp, primaryKey } from "drizzle-orm/pg-core";

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
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  archivedAt: timestamp("archived_at", { withTimezone: true }),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

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
  platformMembershipId: text("platform_membership_id"),
  sourceUpdatedAt: timestamp("source_updated_at", { withTimezone: true }),
  syncedAt: timestamp("synced_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
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
