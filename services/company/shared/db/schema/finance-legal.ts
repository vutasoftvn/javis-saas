import { pgSchema, text, bigint, timestamp, doublePrecision, jsonb, varchar, integer, boolean, date, numeric } from "drizzle-orm/pg-core";

export const financeSchema = pgSchema("finance");
export const legalSchema = pgSchema("legal");

export const accountingProfiles = financeSchema.table("accounting_profiles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().unique(),
  mode: text("mode").default("TT58_MODE_1").notNull(),
  status: text("status").default("DRAFT").notNull(),
  regulationVersionId: bigint("regulation_version_id", { mode: "bigint" }),
  applicabilityConfirmedAt: timestamp("applicability_confirmed_at", { withTimezone: true }),
  applicabilityConfirmedBy: bigint("applicability_confirmed_by", { mode: "bigint" }),
  confirmedBy: bigint("confirmed_by", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingPeriods = financeSchema.table("accounting_periods", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
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
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  documentId: bigint("document_id", { mode: "bigint" }),
  accountingDocumentId: bigint("accounting_document_id", { mode: "bigint" }),
  projectId: bigint("project_id", { mode: "bigint" }),
  cycleId: bigint("cycle_id", { mode: "bigint" }),
  workItemId: bigint("work_item_id", { mode: "bigint" }),
  idempotencyKey: text("idempotency_key"),
  transactionDate: date("transaction_date").notNull(),
  description: text("description").notNull(),
  amount: numeric("amount", { precision: 20, scale: 2 }).notNull(),
  direction: text("direction").notNull(),
  category: text("category"),
  provenance: jsonb("provenance").default({}).notNull(),
  approvalStatus: text("approval_status").default("AUTO_APPROVED").notNull(),
  approvedByUserId: bigint("approved_by_user_id", { mode: "bigint" }),
  approvedAt: timestamp("approved_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const financeExceptions = financeSchema.table("finance_exceptions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
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
  id: bigint("id", { mode: "bigint" }).primaryKey(),
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
  id: bigint("id", { mode: "bigint" }).primaryKey(),
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
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  sourceRegulation: varchar("source_regulation", { length: 50 }).notNull(),
  targetRegulation: varchar("target_regulation", { length: 50 }).notNull(),
  sourceAccountCode: varchar("source_account_code", { length: 50 }).notNull(),
  targetAccountCode: varchar("target_account_code", { length: 50 }).notNull(),
  mappingType: varchar("mapping_type", { length: 30 }).default("DIRECT_1_1").notNull(),
  description: varchar("description", { length: 255 }),
});

export const accountingRegimeTransitionLogs = financeSchema.table("accounting_regime_transition_logs", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
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
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  status: text("status").default("OPEN").notNull(),
  evidenceArtifactId: bigint("evidence_artifact_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const legalObligations = legalSchema.table("legal_obligations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  description: text("description"),
  dueAt: timestamp("due_at", { withTimezone: true }),
  status: text("status").default("OPEN").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingRegimePolicies = financeSchema.table("accounting_regime_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  regulationVersionId: bigint("regulation_version_id", { mode: "bigint" }).notNull(),
  mode: text("mode").notNull(),
  effectiveFrom: date("effective_from").notNull(),
  effectiveTo: date("effective_to"),
  requiresCoa: boolean("requires_coa").default(false).notNull(),
  requiresDoubleEntry: boolean("requires_double_entry").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const bankConnections = financeSchema.table("bank_connections", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  provider: text("provider").notNull(), // 'cas' | 'manual'
  consentState: text("consent_state").default("PENDING").notNull(), // 'PENDING' | 'GRANTED' | 'REVOKED' | 'EXPIRED'
  secretRef: text("secret_ref"),
  scopes: jsonb("scopes").default([]).notNull(),
  accountLinks: jsonb("account_links").default([]).notNull(),
  grantExpiresAt: timestamp("grant_expires_at", { withTimezone: true }),
  lastSyncedAt: timestamp("last_synced_at", { withTimezone: true }),
  syncStatus: text("sync_status").default("IDLE").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const ingestionEvents = financeSchema.table("ingestion_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  bankConnectionId: bigint("bank_connection_id", { mode: "bigint" }).notNull().references(() => bankConnections.id, { onDelete: "cascade" }),
  providerEventId: text("provider_event_id").notNull(),
  receivedAt: timestamp("received_at", { withTimezone: true }).defaultNow().notNull(),
  rawPayloadRef: text("raw_payload_ref"),
  checksum: text("checksum"),
  status: text("status").default("RECEIVED").notNull(), // 'RECEIVED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'DLQ'
  errorMsg: text("error_msg"),
  processedAt: timestamp("processed_at", { withTimezone: true }),
});

export const bankTransactions = financeSchema.table("bank_transactions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  bankConnectionId: bigint("bank_connection_id", { mode: "bigint" }).notNull().references(() => bankConnections.id, { onDelete: "cascade" }),
  ingestionEventId: bigint("ingestion_event_id", { mode: "bigint" }).references(() => ingestionEvents.id, { onDelete: "set null" }),
  externalTransactionId: text("external_transaction_id").notNull(),
  postedAt: timestamp("posted_at", { withTimezone: true }).notNull(),
  amount: numeric("amount", { precision: 20, scale: 2 }).notNull(),
  currency: text("currency").default("VND").notNull(),
  direction: text("direction").notNull(), // 'IN' | 'OUT'
  description: text("description").notNull(),
  counterpartyName: text("counterparty_name"),
  counterpartyAccount: text("counterparty_account"),
  status: text("status").default("UNRECONCILED").notNull(), // 'UNRECONCILED' | 'MATCHED' | 'CONFIRMED'
  matchedAccountingDocumentId: bigint("matched_accounting_document_id", { mode: "bigint" }),
  rawPayload: jsonb("raw_payload"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const accountingDocuments = financeSchema.table("accounting_documents", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  documentType: text("document_type").notNull(), // 'RECEIPT' | 'PAYMENT' | 'INVOICE' | 'JOURNAL'
  number: text("number").notNull(),
  documentDate: date("document_date").notNull(),
  amount: numeric("amount", { precision: 20, scale: 2 }).notNull(),
  currency: text("currency").default("VND").notNull(),
  description: text("description").notNull(),
  status: text("status").default("DRAFT").notNull(), // 'DRAFT' | 'CONFIRMED' | 'VOID'
  regimePolicyId: bigint("regime_policy_id", { mode: "bigint" }).references(() => accountingRegimePolicies.id, { onDelete: "set null" }),
  lineItems: jsonb("line_items").default([]).notNull(),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  confirmedBy: bigint("confirmed_by", { mode: "bigint" }),
  voidReason: text("void_reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const documentReconciliationProposals = financeSchema.table("document_reconciliation_proposals", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  bankTransactionId: bigint("bank_transaction_id", { mode: "bigint" }).notNull().references(() => bankTransactions.id, { onDelete: "cascade" }),
  accountingDocumentId: bigint("accounting_document_id", { mode: "bigint" }).notNull().references(() => accountingDocuments.id, { onDelete: "cascade" }),
  confidence: numeric("confidence", { precision: 5, scale: 4 }).notNull(),
  candidateMatch: jsonb("candidate_match").default({}).notNull(),
  status: text("status").default("PENDING").notNull(), // 'PENDING' | 'ACCEPTED' | 'REJECTED'
  acceptedBy: bigint("accepted_by", { mode: "bigint" }),
  acceptedAt: timestamp("accepted_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const financialSnapshots = financeSchema.table("financial_snapshots", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  snapshotDate: date("snapshot_date").notNull(),
  cashIn: numeric("cash_in", { precision: 20, scale: 2 }).default("0").notNull(),
  cashOut: numeric("cash_out", { precision: 20, scale: 2 }).default("0").notNull(),
  netBurn: numeric("net_burn", { precision: 20, scale: 2 }).default("0").notNull(),
  runwayMonths: numeric("runway_months", { precision: 6, scale: 2 }),
  // M7 §8 — số dư thật + burn theo cửa sổ trailing.
  openingBalance: numeric("opening_balance", { precision: 20, scale: 2 }).default("0").notNull(),
  currentCash: numeric("current_cash", { precision: 20, scale: 2 }),
  monthlyNetBurn: numeric("monthly_net_burn", { precision: 20, scale: 2 }),
  burnWindowMonths: integer("burn_window_months").default(3).notNull(),
  cashFlowPositive: boolean("cash_flow_positive").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const casWebhookInbox = financeSchema.table("cas_webhook_inbox", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  providerEventId: text("provider_event_id").notNull().unique(),
  rawPayload: text("raw_payload").notNull(),
  signatureHeader: text("signature_header"),
  status: text("status").default("RECEIVED").notNull(), // 'RECEIVED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'DLQ'
  errorMsg: text("error_msg"),
  receivedAt: timestamp("received_at", { withTimezone: true }).defaultNow().notNull(),
  processedAt: timestamp("processed_at", { withTimezone: true }),
});



