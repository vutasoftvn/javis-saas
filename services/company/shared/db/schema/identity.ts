import { pgSchema, text, bigint, timestamp } from "drizzle-orm/pg-core";

export const coreSchema = pgSchema("core");

export const identityWorkspaces = coreSchema.table("workspaces", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  name: text("name").notNull(),
  companyStage: text("company_stage").default("S0_GENESIS").notNull(),
  platformCompanyId: text("platform_company_id").unique(),
  platformWorkspaceId: text("platform_workspace_id").unique(),
  ventureStageEnteredAt: timestamp("venture_stage_entered_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
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
