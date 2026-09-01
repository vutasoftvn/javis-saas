import { pgSchema, text, integer, boolean, timestamp, jsonb, bigint, varchar } from "drizzle-orm/pg-core";
import { controlPlaneSchema } from "./control-plane-schema";

export * from "./control-plane-schema";

export const cosaSchema = pgSchema("cosa");

export const roles = cosaSchema.table("roles", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  category: text("category").notNull(),
  sortOrder: integer("sort_order").default(0).notNull(),
  description: text("description"),
});

export const users = cosaSchema.table("users", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  email: varchar("email", { length: 255 }),
  phone: varchar("phone", { length: 50 }),
  hashedPassword: text("hashed_password").notNull(),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  lastLoginAt: timestamp("last_login_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const profiles = cosaSchema.table("profiles", {
  id: bigint("user_id", { mode: "bigint" }).primaryKey().references(() => users.id, { onDelete: "cascade" }),
  roleId: varchar("role_id", { length: 50 }).default("member").notNull().references(() => roles.id),
  fullName: text("full_name"),
  avatarUrl: text("avatar_url"),
  headline: text("headline"),
  bio: text("bio"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const plans = cosaSchema.table("plans", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  defaultLimits: jsonb("default_limits").default({ max_projects: 1, max_seats: 2, max_scheduled_agents: 1 }).notNull(),
  defaultFeatures: jsonb("default_features").default({ marketing: true, crm: true, finance: false, custom_domain: false }).notNull(),
  isPublic: boolean("is_public").default(true).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaces = cosaSchema.table("platform_workspaces", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceName: text("workspace_name").notNull(),
  ownerId: bigint("owner_user_id", { mode: "bigint" }).notNull().references(() => users.id, { onDelete: "cascade" }),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceMemberships = cosaSchema.table("platform_workspace_memberships", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("platform_workspace_id", { mode: "bigint" }).notNull().references(() => workspaces.id, { onDelete: "cascade" }),
  userId: bigint("user_id", { mode: "bigint" }).notNull().references(() => users.id, { onDelete: "cascade" }),
  roleId: text("role").default("member").notNull().references(() => roles.id),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceAgentPolicy = cosaSchema.table("workspace_agent_policy", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("platform_workspace_id", { mode: "bigint" }).notNull().references(() => workspaces.id, { onDelete: "cascade" }),
  toolPattern: text("tool_pattern").notNull(),
  decision: text("decision").notNull(),
  reason: text("reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceLicenses = cosaSchema.table("workspace_licenses", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("platform_workspace_id", { mode: "bigint" }).notNull().references(() => workspaces.id, { onDelete: "cascade" }),
  planId: text("plan_id").notNull().references(() => plans.id),
  licenseKey: text("license_key").notNull().unique(),
  status: text("status").default("active").notNull(),
  startsAt: timestamp("starts_at", { withTimezone: true }).defaultNow().notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  gracePeriodDays: integer("grace_period_days").default(7).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const workspaceEntitlements = cosaSchema.table("workspace_entitlements", {
  workspaceId: bigint("platform_workspace_id", { mode: "bigint" }).primaryKey().references(() => workspaces.id, { onDelete: "cascade" }),
  planId: text("plan_id").notNull().references(() => plans.id),
  effectiveLimits: jsonb("effective_limits").default({}).notNull(),
  effectiveFeatures: jsonb("effective_features").default({}).notNull(),
  customOverrides: jsonb("custom_overrides").default({}).notNull(),
  snapshotSignature: text("snapshot_signature"),
  lastIssuedAt: timestamp("last_issued_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceSyncLogs = cosaSchema.table("platform_workspace_sync_log", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("platform_workspace_id", { mode: "bigint" }).notNull().references(() => workspaces.id, { onDelete: "cascade" }),
  clientCreationId: text("client_creation_id").notNull().unique(),
  syncStatus: text("sync_status").default("pending").notNull(),
  errorMsg: text("error_msg"),
  syncedAt: timestamp("synced_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// Backward compatibility aliases
export const platformWorkspaces = workspaces;
export const platformWorkspaceMemberships = workspaceMemberships;
export const platformWorkspaceSyncLog = workspaceSyncLogs;

export const workspaceSettingsAuditEvents = controlPlaneSchema.table("workspace_settings_audit_events", {
  eventId: bigint("event_id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  actorId: text("actor_id").notNull(),
  eventType: text("event_type").notNull(),
  targetKind: text("target_kind").notNull(),
  targetId: text("target_id").notNull(),
  details: jsonb("details").default({}).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});
