import { pgSchema, text, integer, boolean, timestamp, jsonb, bigint, varchar } from "drizzle-orm/pg-core";

export const cosaSchema = pgSchema("cosa");

export const roles = cosaSchema.table("roles", {
  id: text("id").primaryKey(),
  scope: text("scope").notNull(),
  level: integer("level").notNull(),
  description: text("description"),
});

export const users = cosaSchema.table("users", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  email: varchar("email", { length: 255 }),
  phone: varchar("phone", { length: 50 }),
  hashedPassword: text("hashed_password").notNull(),
  isPlatformAdmin: boolean("is_platform_admin").default(false).notNull(),
  platformRoleId: varchar("platform_role_id", { length: 50 }).references(() => roles.id),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  lastLoginAt: timestamp("last_login_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const profiles = cosaSchema.table("profiles", {
  userId: bigint("user_id", { mode: "bigint" }).primaryKey().references(() => users.id, { onDelete: "cascade" }),
  fullName: text("full_name"),
  avatarUrl: text("avatar_url"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const companies = cosaSchema.table("companies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  slug: varchar("slug", { length: 100 }).notNull().unique(),
  name: varchar("name", { length: 255 }).notNull(),
  logoUrl: text("logo_url"),
  industry: varchar("industry", { length: 100 }),
  countryCode: varchar("country_code", { length: 10 }).default("VN"),
  createdBy: bigint("created_by", { mode: "bigint" }).references(() => users.id, { onDelete: "cascade" }),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const companyAgentPolicy = cosaSchema.table("company_agent_policy", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  companyId: bigint("company_id", { mode: "bigint" }).notNull().references(() => companies.id, { onDelete: "cascade" }),
  toolPattern: text("tool_pattern").notNull(),
  decision: text("decision").notNull(),
  reason: text("reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const companyMemberships = cosaSchema.table("company_memberships", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  companyId: bigint("company_id", { mode: "bigint" }).notNull().references(() => companies.id, { onDelete: "cascade" }),
  userId: bigint("user_id", { mode: "bigint" }).notNull().references(() => users.id, { onDelete: "cascade" }),
  roleId: varchar("role_id", { length: 50 }).notNull().references(() => roles.id).default("user"),
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

export const licenses = cosaSchema.table("licenses", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  companyId: bigint("company_id", { mode: "bigint" }).notNull().references(() => companies.id, { onDelete: "cascade" }),
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

export const companyEntitlements = cosaSchema.table("company_entitlements", {
  companyId: bigint("company_id", { mode: "bigint" }).primaryKey().references(() => companies.id, { onDelete: "cascade" }),
  planId: text("plan_id").notNull().references(() => plans.id),
  effectiveLimits: jsonb("effective_limits").default({}).notNull(),
  effectiveFeatures: jsonb("effective_features").default({}).notNull(),
  customOverrides: jsonb("custom_overrides").default({}).notNull(),
  lastIssuedAt: timestamp("last_issued_at", { withTimezone: true }).defaultNow().notNull(),
  snapshotSignature: text("snapshot_signature"),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
