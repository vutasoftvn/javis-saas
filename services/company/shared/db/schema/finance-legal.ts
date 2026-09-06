import { pgSchema, text, bigint, timestamp, doublePrecision, jsonb, varchar, integer, boolean, date, numeric, smallint } from "drizzle-orm/pg-core";
import { legalSchema } from "./legal";
import { LedgerBucket } from "../../../finance-legal/services/accounting-mapping";

export const financeSchema = pgSchema("finance");


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
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  startDate: date("start_date").notNull(),
  endDate: date("end_date").notNull(),
  fiscalProfileId: bigint("fiscal_profile_id", { mode: "bigint" }),
  version: integer("version").default(1).notNull(),
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
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  documentId: bigint("document_id", { mode: "bigint" }),
  accountingDocumentId: bigint("accounting_document_id", { mode: "bigint" }),
  projectId: bigint("project_id", { mode: "bigint" }),
  cycleId: bigint("cycle_id", { mode: "bigint" }),
  workItemId: bigint("work_item_id", { mode: "bigint" }),
  idempotencyKey: text("idempotency_key"),
  transactionDate: date("transaction_date").notNull(),
  description: text("description").notNull(),
  amount: numeric("amount", { precision: 20, scale: 2 }).notNull(),
  currency: text("currency").default("VND").notNull(),
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
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  yearEnd: date("year_end"),
  mappingVersion: varchar("mapping_version", { length: 50 }),
  applicabilityDecisionId: bigint("applicability_decision_id", { mode: "bigint" }),
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

export const accountingReportMappings = financeSchema.table("accounting_report_mappings", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  regimeCode: varchar("regime_code", { length: 50 }).notNull(),
  mappingVersion: varchar("mapping_version", { length: 50 }).notNull(),
  reportCode: varchar("report_code", { length: 10 }).notNull(),
  lineCode: varchar("line_code", { length: 20 }).notNull(),
  officialCode: varchar("official_code", { length: 50 }).notNull(),
  name: text("name").notNull(),
  sourceRef: text("source_ref").notNull(),
  ruleType: varchar("rule_type", { length: 20 }).notNull(),
  bucket: varchar("bucket", { length: 20 }).$type<LedgerBucket>().notNull(),
  sign: smallint("sign").notNull(),
  rounding: varchar("rounding", { length: 20 }).notNull(),
  definitionHash: text("definition_hash").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const accountingMappingConfirmations = financeSchema.table("accounting_mapping_confirmations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  // Xác nhận mapping phải thuộc về từng workspace (migration 43) — trước đó
  // là toàn cục nên founder của workspace bất kỳ vô tình VERIFIED report của
  // mọi tenant khác.
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  regimeCode: varchar("regime_code", { length: 50 }).notNull(),
  mappingVersion: varchar("mapping_version", { length: 50 }).notNull(),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }).notNull(),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }).defaultNow().notNull(),
});

export const accountingBookEntries = financeSchema.table("accounting_book_entries", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  periodId: bigint("period_id", { mode: "bigint" }).notNull(),
  documentId: bigint("document_id", { mode: "bigint" }),
  item: text("item").notNull(),
  category: varchar("category", { length: 30 }).notNull(),
  amountMinor: numeric("amount_minor", { precision: 38, scale: 0 }).notNull(),
  currency: varchar("currency", { length: 10 }).default("VND").notNull(),
  effectiveDate: date("effective_date").notNull(),
  source: text("source").notNull(),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingReportSnapshots = financeSchema.table("accounting_report_snapshots", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  periodId: bigint("period_id", { mode: "bigint" }).notNull(),
  reportCode: varchar("report_code", { length: 10 }).notNull(),
  mappingVersion: varchar("mapping_version", { length: 50 }).notNull(),
  inputWatermark: text("input_watermark").notNull(),
  lines: jsonb("lines")
    .$type<Array<{ lineCode: string; officialCode: string; name: string; sourceRef: string; amountMinor: string }>>()
    .default([])
    .notNull(),
  status: varchar("status", { length: 20 }).$type<"INCOMPLETE" | "PROVIDER_NOT_READY" | "VERIFIED">().notNull(),
  issues: jsonb("issues").$type<string[]>().default([]).notNull(),
  generatedAt: timestamp("generated_at", { withTimezone: true }).defaultNow().notNull(),
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
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  provider: text("provider").notNull(), // 'cas' | 'manual'
  providerEnvironment: text("provider_environment").default("sandbox").notNull(),
  consentState: text("consent_state").default("PENDING").notNull(), // 'PENDING' | 'GRANTED' | 'REVOKED' | 'EXPIRED'
  secretRef: text("secret_ref"),
  scopes: jsonb("scopes").default([]).notNull(),
  accountLinks: jsonb("account_links").default([]).notNull(),
  providerGrantId: text("provider_grant_id"),
  externalAccountId: text("external_account_id"),
  institutionId: text("institution_id"),
  accountFingerprint: text("account_fingerprint"),
  grantedScopes: jsonb("granted_scopes").default([]).notNull(),
  grantExpiresAt: timestamp("grant_expires_at", { withTimezone: true }),
  providerContractVersion: text("provider_contract_version"),
  reauthRequired: boolean("reauth_required").default(false).notNull(),
  // F3 — sync cursor/lease cho GET-poll. `lastSyncedAt` mang nghĩa "lần
  // ĐỒNG BỘ THÀNH CÔNG cuối", không phải lần thử cuối (attempt lỗi không đổi
  // field này). `updatedAt` (đã có sẵn, được cas-link.service bump khi
  // revoke/reauthorize) dùng làm optimistic-lock "grant version" cho
  // syncCasConnection — không thêm cột grant_version riêng để tránh phình
  // schema khi updatedAt đã đủ dùng.
  syncCursor: text("sync_cursor"),
  syncError: text("sync_error"),
  syncErrorCount: integer("sync_error_count").default(0).notNull(),
  syncLockedUntil: timestamp("sync_locked_until", { withTimezone: true }),
  syncCoverageStart: timestamp("sync_coverage_start", { withTimezone: true }),
  lastSyncedAt: timestamp("last_synced_at", { withTimezone: true }),
  syncStatus: text("sync_status").default("IDLE").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const casLinkSessions = financeSchema.table("cas_link_sessions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  createdBy: bigint("created_by", { mode: "bigint" }).notNull(),
  stateHash: text("state_hash").notNull().unique(),
  scopes: jsonb("scopes").default([]).notNull(),
  allowedRedirect: text("allowed_redirect").notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  consumedAt: timestamp("consumed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// `ingestion_events` predate kế hoạch F3 và không còn được pipeline mới dùng
// (không có caller nào query bảng này ngoài chính service cũ của nó, đã bị
// thay bằng `cas_sync_inbox` bên dưới — bảng hợp nhất GET-poll + webhook).
// Giữ nguyên bảng cũ (migration Expand-only, không xoá dữ liệu đã tồn tại),
// chỉ không mở rộng thêm cột cho nó nữa.
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

// F3 — hộp thư hợp nhất cho CẢ webhook (Cas.so đẩy) VÀ GET-poll (Cas.so kéo).
// Dedup theo (provider, environment, event_identity) — identity dựng từ field
// contract-defined (bank_connection_id/grant + account + transaction id +
// loại event + version contract), KHÔNG dùng hash nguyên payload đơn độc làm
// identity (2 lần giao hàng cùng 1 giao dịch có thể lệch byte nhưng vẫn phải
// trỏ về đúng 1 canonical row). Nhờ vậy GET-poll và webhook của cùng giao
// dịch tự nhiên collapse về 1 dòng inbox duy nhất.
export const casSyncInbox = financeSchema.table("cas_sync_inbox", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  // NULL khi webhook chưa resolve được tenant (unknown grant/account) — dòng
  // ở trạng thái QUARANTINED, không tự gán nhầm sang workspace nào.
  bankConnectionId: bigint("bank_connection_id", { mode: "bigint" }).references(() => bankConnections.id, { onDelete: "cascade" }),
  provider: text("provider").default("cas").notNull(),
  environment: text("environment").default("sandbox").notNull(),
  source: text("source").notNull(), // 'webhook' | 'poll'
  eventIdentity: text("event_identity").notNull(),
  rawPayload: jsonb("raw_payload").notNull(),
  // 'RECEIVED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'DLQ' | 'QUARANTINED' | 'IGNORED'
  status: text("status").default("RECEIVED").notNull(),
  attempts: integer("attempts").default(0).notNull(),
  nextAttemptAt: timestamp("next_attempt_at", { withTimezone: true }).defaultNow().notNull(),
  leaseUntil: timestamp("lease_until", { withTimezone: true }),
  leaseToken: text("lease_token"),
  errorCode: text("error_code"),
  errorMsg: text("error_msg"),
  bankTransactionId: bigint("bank_transaction_id", { mode: "bigint" }).references(() => bankTransactions.id, { onDelete: "set null" }),
  receivedAt: timestamp("received_at", { withTimezone: true }).defaultNow().notNull(),
  processedAt: timestamp("processed_at", { withTimezone: true }),
});

// Audit trail chuyển đổi raw -> bank_transaction, tách khỏi cas_sync_inbox để
// giữ lịch sử dù dòng inbox có bị prune sau này. unique(bank_connection_id,
// provider_tx_id) là lớp dedup THỨ HAI ở mức nghiệp vụ (độc lập với dedup ở
// mức inbox) — hai lớp cùng tồn tại vì inbox dedup theo identity dựng từ
// contract, còn log này dedup theo provider_tx_id thô providers trả về.
export const casNormalizerLog = financeSchema.table("cas_normalizer_log", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  bankConnectionId: bigint("bank_connection_id", { mode: "bigint" }).notNull().references(() => bankConnections.id, { onDelete: "cascade" }),
  inboxEventId: bigint("inbox_event_id", { mode: "bigint" }).references(() => casSyncInbox.id, { onDelete: "set null" }),
  providerTxId: text("provider_tx_id").notNull(),
  providerTxHash: text("provider_tx_hash").notNull(),
  bankTransactionId: bigint("bank_transaction_id", { mode: "bigint" }).references(() => bankTransactions.id, { onDelete: "set null" }),
  // 'INSERT' | 'SKIP_DUP' (trùng, hash khớp) | 'CONFLICT' (trùng provider_tx_id
  // nhưng hash lệch — nghi correction/reversal, KHÔNG tự overwrite, cần review)
  // | 'FAIL' (raw payload không hợp lệ)
  action: text("action").default("INSERT").notNull(),
  failReason: text("fail_reason"),
  normalizedAt: timestamp("normalized_at", { withTimezone: true }).defaultNow().notNull(),
});

// DLQ cho inbox event thất bại quá số lần retry cho phép — cần con người xem
// lại thay vì worker tự lặp vô hạn.
export const ingestionDlq = financeSchema.table("ingestion_dlq", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  inboxEventId: bigint("inbox_event_id", { mode: "bigint" }).notNull().references(() => casSyncInbox.id),
  bankConnectionId: bigint("bank_connection_id", { mode: "bigint" }).references(() => bankConnections.id),
  movedAt: timestamp("moved_at", { withTimezone: true }).defaultNow().notNull(),
  failCount: integer("fail_count").default(0).notNull(),
  lastError: text("last_error"),
  reviewed: boolean("reviewed").default(false).notNull(),
  reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
  reviewedBy: bigint("reviewed_by", { mode: "bigint" }),
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
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  snapshotDate: date("snapshot_date").notNull(),
  currency: text("currency").default("VND").notNull(),
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

// F4 — chỉ phần state machine đề nghị chi (payment_requests). Xem migration
// 40 để biết phạm vi CHƯA làm (payment_allocations, QR provider integration).
export const paymentRequests = financeSchema.table("payment_requests", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  amountMinor: numeric("amount_minor", { precision: 38, scale: 0 }).notNull(),
  currency: text("currency").default("VND").notNull(),
  beneficiaryBankBin: text("beneficiary_bank_bin").notNull(),
  beneficiaryAccountNumber: text("beneficiary_account_number").notNull(),
  beneficiaryName: text("beneficiary_name").notNull(),
  purpose: text("purpose").notNull(),
  documentRefs: jsonb("document_refs").default([]).notNull(),
  dueAt: timestamp("due_at", { withTimezone: true }),
  transferReference: text("transfer_reference"),
  approvalState: text("approval_state").default("DRAFT").notNull(), // DRAFT | SUBMITTED | APPROVED | REJECTED | CANCELLED
  settlementState: text("settlement_state").default("UNPAID").notNull(), // UNPAID | REPORTED | PARTIAL | PAID | EXCEPTION
  accountingState: text("accounting_state").default("UNCLASSIFIED").notNull(), // UNCLASSIFIED | DRAFT | POSTED | REVIEW_REQUIRED
  version: integer("version").default(1).notNull(),
  approvalHash: text("approval_hash"),
  approvedVersion: integer("approved_version"),
  approvedByMemberId: bigint("approved_by_member_id", { mode: "bigint" }),
  approvedAt: timestamp("approved_at", { withTimezone: true }),
  reportedByMemberId: bigint("reported_by_member_id", { mode: "bigint" }),
  reportedAt: timestamp("reported_at", { withTimezone: true }),
  idempotencyKey: text("idempotency_key").notNull(),
  createdBy: bigint("created_by", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

// F4 phần 2 — khớp payment_requests với bank_transactions thật. Xem
// migration 41 để biết phạm vi CHƯA làm (migrate dữ liệu đối soát cũ).
export const paymentAllocations = financeSchema.table("payment_allocations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  bankTransactionId: bigint("bank_transaction_id", { mode: "bigint" })
    .notNull()
    .references(() => bankTransactions.id),
  requestId: bigint("request_id", { mode: "bigint" })
    .notNull()
    .references(() => paymentRequests.id),
  amountMinor: numeric("amount_minor", { precision: 38, scale: 0 }).notNull(),
  currency: text("currency").notNull(),
  status: text("status").default("ACTIVE").notNull(), // ACTIVE | REVERSED
  reversedReason: text("reversed_reason"),
  reversedByMemberId: bigint("reversed_by_member_id", { mode: "bigint" }),
  reversedAt: timestamp("reversed_at", { withTimezone: true }),
  idempotencyKey: text("idempotency_key").notNull(),
  createdBy: bigint("created_by", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});



