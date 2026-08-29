import { pgSchema, text, bigint, timestamp, date, integer, jsonb } from "drizzle-orm/pg-core";

export const legalSchema = pgSchema("legal");

export const regulationSources = legalSchema.table("regulation_sources", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  sourceName: text("source_name").notNull(),
  issuer: text("issuer").notNull(),
  number: text("number").notNull().unique(),
  url: text("url").notNull(),
  contentHash: text("content_hash"),
  layer: text("layer").notNull(), // 'CURRENT_LAW' | 'POLICY_WATCH' | 'PROFESSIONAL_REVIEW'
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const regulationVersions = legalSchema.table("regulation_versions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  regulationSourceId: bigint("regulation_source_id", { mode: "bigint" })
    .notNull()
    .references(() => regulationSources.id, { onDelete: "cascade" }),
  version: text("version").notNull(),
  effectiveFrom: date("effective_from").notNull(),
  effectiveTo: date("effective_to"),
  supersededById: bigint("superseded_by_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const legalEntityProfiles = legalSchema.table("legal_entity_profiles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  entityType: text("entity_type").notNull(),
  // M4 §5 — DRAFT|REGISTRATION_PREPARATION|REGISTERED_UNVERIFIED|VERIFIED|SUSPENDED|DISSOLVED
  status: text("status").default("DRAFT").notNull(),
  registrationNumber: text("registration_number"),
  taxId: text("tax_id"),
  verifiedByMemberId: bigint("verified_by_member_id", { mode: "bigint" }),
  verifiedAt: timestamp("verified_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

// M1 §6 — durable approval record cho legal verification. Thay cho check prefix chuỗi
// `appr_legal_` (không lưu DB, không expiry, không tách requester/approver).
export const legalVerificationApprovals = legalSchema.table("legal_verification_approvals", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  // bind: approval này chỉ confirm được đúng transition status này
  expectedStatus: text("expected_status").notNull(),
  requestedBy: bigint("requested_by", { mode: "bigint" }).notNull(),
  approvedBy: bigint("approved_by", { mode: "bigint" }),
  status: text("status").default("PENDING").notNull(), // PENDING | APPROVED | REJECTED | EXPIRED
  requestedAt: timestamp("requested_at", { withTimezone: true }).defaultNow().notNull(),
  decidedAt: timestamp("decided_at", { withTimezone: true }),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  rationale: text("rationale"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const legalObligationTemplates = legalSchema.table("legal_obligation_templates", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  regulationVersionId: bigint("regulation_version_id", { mode: "bigint" })
    .notNull()
    .references(() => regulationVersions.id, { onDelete: "cascade" }),
  title: text("title").notNull(),
  description: text("description"),
  typicalDueOffsetDays: integer("typical_due_offset_days"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const applicabilityRules = legalSchema.table("applicability_rules", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  regulationVersionId: bigint("regulation_version_id", { mode: "bigint" })
    .notNull()
    .references(() => regulationVersions.id, { onDelete: "cascade" }),
  predicate: jsonb("predicate").notNull(),
  obligationTemplateId: bigint("obligation_template_id", { mode: "bigint" })
    .notNull()
    .references(() => legalObligationTemplates.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const legalObligationInstances = legalSchema.table("legal_obligation_instances", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityProfileId: bigint("legal_entity_profile_id", { mode: "bigint" })
    .references(() => legalEntityProfiles.id, { onDelete: "set null" }),
  templateId: bigint("template_id", { mode: "bigint" })
    .references(() => legalObligationTemplates.id, { onDelete: "set null" }),
  regulationVersionId: bigint("regulation_version_id", { mode: "bigint" })
    .references(() => regulationVersions.id, { onDelete: "set null" }),
  source: text("source").notNull(), // 'REGULATION_TEMPLATE' | 'USER_CREATED' | 'AI_PROPOSAL'
  title: text("title").notNull(),
  dueDate: date("due_date"),
  status: text("status").default("OPEN").notNull(),
  evidenceArtifactId: bigint("evidence_artifact_id", { mode: "bigint" }),
  applicabilityAssessedAt: timestamp("applicability_assessed_at", { withTimezone: true }),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  reviewStatus: text("review_status").default("PENDING").notNull(),
  legacyRef: text("legacy_ref").unique(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
