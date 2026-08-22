import { pgSchema, text, bigint, bigserial, timestamp } from "drizzle-orm/pg-core";

export const coreSchema = pgSchema("core");

export const identityWorkspaces = coreSchema.table("workspaces", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  name: text("name").notNull(),
  companyStage: text("company_stage").default("S0_GENESIS").notNull(),
  platformCompanyId: text("platform_company_id").unique(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const identityUsers = coreSchema.table("users", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  email: text("email").unique(),
  phone: text("phone").unique(),
  passwordHash: text("password_hash"),
  displayName: text("display_name"),
  status: text("status").default("active").notNull(),
  platformUserId: text("platform_user_id").unique(),
  role: text("role"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const identityWorkspaceMembers = coreSchema.table("workspace_members", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id),
  userId: bigint("user_id", { mode: "bigint" }).notNull().references(() => identityUsers.id),
  role: text("role").default("member").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const identityOrganizations = coreSchema.table("organizations", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().unique().references(() => identityWorkspaces.id),
  name: text("name").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const identityWorkforceMembers = coreSchema.table("workforce_members", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  organizationId: bigint("organization_id", { mode: "bigint" }).notNull().references(() => identityOrganizations.id),
  memberType: text("member_type").notNull(),
  humanUserId: bigint("human_user_id", { mode: "bigint" }).references(() => identityUsers.id),
  agentDefinitionId: bigint("agent_definition_id", { mode: "bigint" }),
  roleTitle: text("role_title").notNull(),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});
