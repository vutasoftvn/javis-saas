import { pgSchema, text, bigint, bigserial, timestamp, doublePrecision, jsonb, varchar, integer, boolean, date, numeric } from "drizzle-orm/pg-core";

export const financeSchema = pgSchema("finance");
export const legalSchema = pgSchema("legal");
export const validationSchema = pgSchema("validation");

export const accountingProfiles = financeSchema.table("accounting_profiles", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().unique(),
  mode: text("mode").default("TT58_MODE_1").notNull(),
  status: text("status").default("DRAFT").notNull(),
  confirmedBy: bigint("confirmed_by", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingPeriods = financeSchema.table("accounting_periods", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  startDate: date("start_date").notNull(),
  endDate: date("end_date").notNull(),
  status: text("status").default("OPEN").notNull(),
  closedBy: bigint("closed_by", { mode: "bigint" }),
  closedAt: timestamp("closed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const financialTransactions = financeSchema.table("financial_transactions", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  documentId: bigint("document_id", { mode: "bigint" }),
  projectId: bigint("project_id", { mode: "bigint" }),
  cycleId: bigint("cycle_id", { mode: "bigint" }),
  workItemId: bigint("work_item_id", { mode: "bigint" }),
  idempotencyKey: text("idempotency_key"),
  transactionDate: date("transaction_date").notNull(),
  description: text("description").notNull(),
  amount: numeric("amount", { precision: 20, scale: 2 }).notNull(),
  direction: text("direction").notNull(),
  category: text("category"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const financeExceptions = financeSchema.table("finance_exceptions", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  transactionId: bigint("transaction_id", { mode: "bigint" }).references(() => financialTransactions.id, { onDelete: "cascade" }),
  exceptionType: text("exception_type").notNull(),
  severity: text("severity").default("WARNING").notNull(),
  details: jsonb("details"),
  status: text("status").default("OPEN").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const financeManagementSnapshots = financeSchema.table("finance_management_snapshots", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  cycleId: bigint("cycle_id", { mode: "bigint" }),
  asOf: date("as_of").notNull(),
  cash: numeric("cash", { precision: 20, scale: 2 }).notNull(),
  burn: numeric("burn", { precision: 20, scale: 2 }).notNull(),
  runwayMonths: numeric("runway_months", { precision: 12, scale: 2 }),
  revenue: numeric("revenue", { precision: 20, scale: 2 }).default("0").notNull(),
  expenses: numeric("expenses", { precision: 20, scale: 2 }).default("0").notNull(),
  budgetVariance: numeric("budget_variance", { precision: 20, scale: 2 }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingFiscalProfiles = financeSchema.table("accounting_fiscal_profiles", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  fiscalYear: integer("fiscal_year").notNull(),
  regulationCode: varchar("regulation_code", { length: 50 }).default("TT58_2026").notNull(),
  mode: varchar("mode", { length: 50 }).default("TT58_MODE_1").notNull(),
  status: varchar("status", { length: 30 }).default("ACTIVE").notNull(),
  lockedAt: timestamp("locked_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingCoaMappings = financeSchema.table("accounting_coa_mappings", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  sourceRegulation: varchar("source_regulation", { length: 50 }).notNull(),
  targetRegulation: varchar("target_regulation", { length: 50 }).notNull(),
  sourceAccountCode: varchar("source_account_code", { length: 50 }).notNull(),
  targetAccountCode: varchar("target_account_code", { length: 50 }).notNull(),
  mappingType: varchar("mapping_type", { length: 30 }).default("DIRECT_1_1").notNull(),
  description: varchar("description", { length: 255 }),
});

export const accountingRegimeTransitionLogs = financeSchema.table("accounting_regime_transition_logs", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  fromFiscalYear: integer("from_fiscal_year").notNull(),
  toFiscalYear: integer("to_fiscal_year").notNull(),
  fromRegulation: varchar("from_regulation", { length: 50 }).notNull(),
  toRegulation: varchar("to_regulation", { length: 50 }).notNull(),
  cutoffDate: date("cutoff_date").notNull(),
  isBalanced: boolean("is_balanced").default(true).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const legalChecklistItems = legalSchema.table("legal_checklist_items", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  status: text("status").default("OPEN").notNull(),
  evidenceArtifactId: bigint("evidence_artifact_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const legalObligations = legalSchema.table("legal_obligations", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  description: text("description"),
  dueAt: timestamp("due_at", { withTimezone: true }),
  status: text("status").default("OPEN").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const validationHypotheses = validationSchema.table("validation_hypotheses", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  title: varchar("title", { length: 255 }).notNull(),
  statement: text("statement").notNull(),
  confidenceScore: doublePrecision("confidence_score").default(0.5).notNull(),
  status: varchar("status", { length: 50 }).default("TESTING").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const validationExperiments = validationSchema.table("validation_experiments", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  hypothesisId: bigint("hypothesis_id", { mode: "bigint" }).notNull().references(() => validationHypotheses.id, { onDelete: "cascade" }),
  experimentType: varchar("experiment_type", { length: 50 }).default("INTERVIEW").notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  status: varchar("status", { length: 50 }).default("RUNNING").notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const evidenceItems = validationSchema.table("evidence_items", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  experimentId: bigint("experiment_id", { mode: "bigint" }).notNull().references(() => validationExperiments.id, { onDelete: "cascade" }),
  evidenceType: varchar("evidence_type", { length: 50 }).default("QUOTE").notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  content: text("content").notNull(),
  strengthScore: doublePrecision("strength_score").default(1.0).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const customerInterviews = validationSchema.table("customer_interviews", {
  id: bigserial("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  customerName: varchar("customer_name", { length: 255 }).notNull(),
  interviewDate: timestamp("interview_date", { withTimezone: true }).defaultNow().notNull(),
  keyInsights: text("key_insights"),
  painPoints: text("pain_points"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
