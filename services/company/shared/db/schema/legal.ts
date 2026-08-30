import { pgSchema, text, bigint, timestamp, date, integer, jsonb, boolean, unique, foreignKey } from "drizzle-orm/pg-core";

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

// AI Compliance & Governance Schema
export const aiSystemCatalog = legalSchema.table("ai_system_catalog", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  systemKey: text("system_key").notNull().unique(),
  name: text("name").notNull(),
  allowedPurposes: jsonb("allowed_purposes").default([]).notNull(),
  prohibitedPurposes: jsonb("prohibited_purposes").default([]).notNull(),
  technicalOwnerMemberId: bigint("technical_owner_member_id", { mode: "bigint" }),
  lifecycleStatus: text("lifecycle_status").default("DRAFT").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const aiSystemVersions = legalSchema.table("ai_system_versions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  systemCatalogId: bigint("system_catalog_id", { mode: "bigint" })
    .notNull()
    .references(() => aiSystemCatalog.id, { onDelete: "cascade" }),
  version: text("version").notNull(),
  configHash: text("config_hash").notNull(),
  modelProfileRef: text("model_profile_ref"),
  status: text("status").default("DRAFT").notNull(),
  releasedAt: timestamp("released_at", { withTimezone: true }),
  deprecatedAt: timestamp("deprecated_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const workspaceAiDeployments = legalSchema.table(
  "workspace_ai_deployments",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    systemVersionId: bigint("system_version_id", { mode: "bigint" })
      .notNull()
      .references(() => aiSystemVersions.id),
    mode: text("mode").notNull(),
    status: text("status").notNull(),
    founderMemberId: bigint("founder_member_id", { mode: "bigint" }).notNull(),
    technicalOwnerMemberId: bigint("technical_owner_member_id", { mode: "bigint" }),
    // nullable — deployment mới tạo chưa có assessment nào được chốt làm current
    currentAssessmentId: bigint("current_assessment_id", { mode: "bigint" }),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: composite unique key để các bảng con FK theo
    // (workspace_id, id) — PostgreSQL tự chặn con trỏ sang deployment của
    // workspace khác, không chỉ dựa vào scoping ở tầng code TS (Task 1).
    unique("workspace_ai_deployments_workspace_id_id_key").on(t.workspaceId, t.id),
    // Lưu ý: composite FK workspace_ai_deployments_workspace_assessment_fk
    // (current_assessment_id → ai_risk_assessments(workspace_id, id)) CÓ tồn
    // tại thật ở tầng DB (migration 29 up.sql) nhưng KHÔNG được khai báo ở
    // đây — vì workspace_ai_deployments ⇄ ai_risk_assessments tham chiếu
    // vòng lẫn nhau (ai_risk_assessments.deployment_id cũng FK ngược lại),
    // và TypeScript không suy luận được kiểu cho 2 `pgTable` tự tham chiếu
    // vòng qua composite foreignKey() (lỗi TS7022/TS7024 "implicitly has
    // type any"). Trước migration 29, current_assessment_id vốn cũng không
    // được model .references() trong Drizzle vì cùng lý do — đây không phải
    // constraint ORM-only bị thiếu ở DB, mà là constraint DB có thật nhưng
    // ORM không thể biểu diễn được do giới hạn suy luận kiểu tuần hoàn.
  ]
);

export const aiSystemCapabilityBindings = legalSchema.table("ai_system_capability_bindings", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  systemVersionId: bigint("system_version_id", { mode: "bigint" })
    .notNull()
    .references(() => aiSystemVersions.id, { onDelete: "cascade" }),
  capabilityId: text("capability_id").notNull(),
  effectClass: text("effect_class").notNull(),
  decisionDomain: text("decision_domain").notNull(),
  requiresHumanConfirmation: boolean("requires_human_confirmation").default(true).notNull(),
  maySendToModel: boolean("may_send_to_model").default(false).notNull(),
  maxDataCategory: text("max_data_category").notNull(),
  actionRecipientScope: text("action_recipient_scope"),
  prohibitedPurpose: boolean("prohibited_purpose").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const aiRiskAssessments = legalSchema.table(
  "ai_risk_assessments",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    deploymentId: bigint("deployment_id", { mode: "bigint" })
      .notNull()
      .references(() => workspaceAiDeployments.id, { onDelete: "cascade" }),
    classification: text("classification").notNull(),
    intendedPurpose: text("intended_purpose").notNull(),
    affectedStakeholders: jsonb("affected_stakeholders").default([]).notNull(),
    controls: jsonb("controls").default([]).notNull(),
    reviewerMemberId: bigint("reviewer_member_id", { mode: "bigint" }),
    approvedByMemberId: bigint("approved_by_member_id", { mode: "bigint" }),
    approvedAt: timestamp("approved_at", { withTimezone: true }),
    rationale: text("rationale"),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    status: text("status").default("PENDING").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: composite unique key — cho phép ai_compliance_evidence,
    // ai_compliance_snapshots và workspace_ai_deployments.current_assessment_id
    // FK theo (workspace_id, id).
    unique("ai_risk_assessments_workspace_id_id_key").on(t.workspaceId, t.id),
    // deployment_id phải cùng workspace với deployment cha — composite FK,
    // NOT VALID trên 1 row rác lịch sử (xem migration 29 up.sql).
    foreignKey({
      name: "ai_risk_assessments_workspace_deployment_fk",
      columns: [t.workspaceId, t.deploymentId],
      foreignColumns: [workspaceAiDeployments.workspaceId, workspaceAiDeployments.id],
    }),
  ]
);

export const aiComplianceEvidence = legalSchema.table(
  "ai_compliance_evidence",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    assessmentId: bigint("assessment_id", { mode: "bigint" })
      .notNull()
      .references(() => aiRiskAssessments.id, { onDelete: "cascade" }),
    evidenceType: text("evidence_type").notNull(),
    uriReference: text("uri_reference").notNull(),
    contentHash: text("content_hash").notNull(),
    checkedAt: timestamp("checked_at", { withTimezone: true }).defaultNow().notNull(),
    reviewerMemberId: bigint("reviewer_member_id", { mode: "bigint" }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: assessment_id phải cùng workspace với assessment cha —
    // composite FK, NOT VALID trên 1 row rác lịch sử (xem migration 29 up.sql).
    foreignKey({
      name: "ai_compliance_evidence_workspace_assessment_fk",
      columns: [t.workspaceId, t.assessmentId],
      foreignColumns: [aiRiskAssessments.workspaceId, aiRiskAssessments.id],
    }),
  ]
);

export const aiProviderProfiles = legalSchema.table(
  "ai_provider_profiles",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    providerKey: text("provider_key").notNull(),
    modelKey: text("model_key").notNull(),
    version: text("version").notNull(),
    status: text("status").notNull(),
    declaredProcessingRegion: text("declared_processing_region").notNull(),
    dpaReference: text("dpa_reference"),
    allowedDataCategories: jsonb("allowed_data_categories").default([]).notNull(),
    reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
    reviewedByMemberId: bigint("reviewed_by_member_id", { mode: "bigint" }),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: composite unique key — cho phép ai_data_processing_profiles
    // FK theo (workspace_id, id) qua recipient_provider_profile_id.
    unique("ai_provider_profiles_workspace_id_id_key").on(t.workspaceId, t.id),
  ]
);

export const aiDataProcessingProfiles = legalSchema.table(
  "ai_data_processing_profiles",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    deploymentId: bigint("deployment_id", { mode: "bigint" })
      .notNull()
      .references(() => workspaceAiDeployments.id, { onDelete: "cascade" }),
    bindingId: bigint("binding_id", { mode: "bigint" })
      .references(() => aiSystemCapabilityBindings.id, { onDelete: "set null" }),
    purposeId: text("purpose_id").notNull(),
    dataCategories: jsonb("data_categories").default([]).notNull(),
    // nullable — composite FK bên dưới cho phép NULL (MATCH SIMPLE mặc định)
    recipientProviderProfileId: bigint("recipient_provider_profile_id", { mode: "bigint" })
      .references(() => aiProviderProfiles.id, { onDelete: "restrict" }),
    retentionPolicyId: text("retention_policy_id").notNull(),
    transferConditions: jsonb("transfer_conditions").default([]).notNull(),
    minimizationRequired: boolean("minimization_required").default(true).notNull(),
    version: text("version").notNull(),
    status: text("status").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29 mục 3: composite unique key — cho phép
    // ai_compliance_snapshots.data_profile_id FK theo (workspace_id, id).
    unique("ai_data_processing_profiles_workspace_id_id_key").on(t.workspaceId, t.id),
    // Migration 29: deployment_id / recipient_provider_profile_id phải cùng
    // workspace với deployment/provider profile cha tương ứng — composite
    // FK, NOT VALID trên 1 row rác lịch sử mỗi quan hệ (xem migration 29
    // up.sql), vẫn enforce đầy đủ cho ghi mới.
    foreignKey({
      name: "ai_data_profiles_workspace_deployment_fk",
      columns: [t.workspaceId, t.deploymentId],
      foreignColumns: [workspaceAiDeployments.workspaceId, workspaceAiDeployments.id],
    }),
    foreignKey({
      name: "ai_data_profiles_workspace_provider_fk",
      columns: [t.workspaceId, t.recipientProviderProfileId],
      foreignColumns: [aiProviderProfiles.workspaceId, aiProviderProfiles.id],
    }),
  ]
);

export const dataProcessingAuthorizations = legalSchema.table("data_processing_authorizations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  subjectReferenceHash: text("subject_reference_hash").notNull(),
  purposeId: text("purpose_id").notNull(),
  purposeVersion: text("purpose_version").notNull(),
  authorityType: text("authority_type").notNull(),
  proofReference: text("proof_reference").notNull(),
  proofHash: text("proof_hash").notNull(),
  status: text("status").notNull(),
  grantedAt: timestamp("granted_at", { withTimezone: true }).defaultNow().notNull(),
  withdrawnAt: timestamp("withdrawn_at", { withTimezone: true }),
  restrictedAt: timestamp("restricted_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const dataSubjectRequests = legalSchema.table("data_subject_requests", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  subjectReferenceHash: text("subject_reference_hash").notNull(),
  requestType: text("request_type").notNull(),
  deadline: timestamp("deadline", { withTimezone: true }).notNull(),
  status: text("status").notNull(),
  resultSummary: text("result_summary"),
  legalHold: boolean("legal_hold").default(false).notNull(),
  legalHoldReason: text("legal_hold_reason"),
  handledByMemberId: bigint("handled_by_member_id", { mode: "bigint" }),
  resolvedAt: timestamp("resolved_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const aiIncidents = legalSchema.table(
  "ai_incidents",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    deploymentId: bigint("deployment_id", { mode: "bigint" })
      .notNull()
      .references(() => workspaceAiDeployments.id, { onDelete: "cascade" }),
    severity: text("severity").notNull(),
    status: text("status").notNull(),
    detectedAt: timestamp("detected_at", { withTimezone: true }).notNull(),
    containedAt: timestamp("contained_at", { withTimezone: true }),
    closedAt: timestamp("closed_at", { withTimezone: true }),
    dataCategories: jsonb("data_categories").default([]).notNull(),
    notificationDeadline: timestamp("notification_deadline", { withTimezone: true }),
    notificationDecision: text("notification_decision"),
    notificationDecisionAt: timestamp("notification_decision_at", { withTimezone: true }),
    notificationDecisionByMemberId: bigint("notification_decision_by_member_id", { mode: "bigint" }),
    notificationRationale: text("notification_rationale"),
    summary: text("summary").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: composite unique key — cho phép ai_incident_actions FK
    // theo (workspace_id, id).
    unique("ai_incidents_workspace_id_id_key").on(t.workspaceId, t.id),
    // deployment_id phải cùng workspace với deployment cha — composite FK,
    // NOT VALID trên 1 row rác lịch sử (xem migration 29 up.sql).
    foreignKey({
      name: "ai_incidents_workspace_deployment_fk",
      columns: [t.workspaceId, t.deploymentId],
      foreignColumns: [workspaceAiDeployments.workspaceId, workspaceAiDeployments.id],
    }),
  ]
);

export const aiIncidentActions = legalSchema.table(
  "ai_incident_actions",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    incidentId: bigint("incident_id", { mode: "bigint" })
      .notNull()
      .references(() => aiIncidents.id, { onDelete: "cascade" }),
    actionType: text("action_type").notNull(),
    description: text("description").notNull(),
    takenByMemberId: bigint("taken_by_member_id", { mode: "bigint" }).notNull(),
    evidenceReference: text("evidence_reference"),
    evidenceHash: text("evidence_hash"),
    takenAt: timestamp("taken_at", { withTimezone: true }).defaultNow().notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: incident_id phải cùng workspace với incident cha —
    // composite FK, NOT VALID trên 1 row rác lịch sử (xem migration 29 up.sql).
    foreignKey({
      name: "ai_incident_actions_workspace_incident_fk",
      columns: [t.workspaceId, t.incidentId],
      foreignColumns: [aiIncidents.workspaceId, aiIncidents.id],
    }),
  ]
);

export const aiComplianceSnapshots = legalSchema.table(
  "ai_compliance_snapshots",
  {
    id: bigint("id", { mode: "bigint" }).primaryKey(),
    workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
    deploymentId: bigint("deployment_id", { mode: "bigint" })
      .notNull()
      .references(() => workspaceAiDeployments.id, { onDelete: "cascade" }),
    assessmentId: bigint("assessment_id", { mode: "bigint" })
      .notNull()
      .references(() => aiRiskAssessments.id, { onDelete: "cascade" }),
    mode: text("mode").notNull(),
    status: text("status").notNull(),
    allowedCapabilities: jsonb("allowed_capabilities").default([]).notNull(),
    providerProfileVersion: text("provider_profile_version").notNull(),
    dataProfileVersion: text("data_profile_version").notNull(),
    legalVersionIds: jsonb("legal_version_ids").default([]).notNull(),
    // Migration 29 mục 3 (reviewer fix — task-2-brief.md "Produces"):
    // provenance thật của snapshot, không chỉ version dạng text.
    capabilityBindingIds: jsonb("capability_binding_ids").default([]).notNull(),
    evidenceIds: jsonb("evidence_ids").default([]).notNull(),
    evidenceHashes: jsonb("evidence_hashes").default([]).notNull(),
    // nullable — composite FK bên dưới cho phép NULL (MATCH SIMPLE mặc
    // định); NULL nghĩa là chưa verify được provider/data profile thật.
    providerProfileId: bigint("provider_profile_id", { mode: "bigint" }),
    dataProfileId: bigint("data_profile_id", { mode: "bigint" }),
    // true chỉ khi providerProfileId VÀ dataProfileId đều verify được — Task
    // 4 resolver phải coi false là "unusable", không tự suy diễn/lấp đầy.
    provenanceComplete: boolean("provenance_complete").default(false).notNull(),
    policySnapshotHash: text("policy_snapshot_hash").notNull(),
    snapshotHash: text("snapshot_hash").notNull().unique(),
    issuedAt: timestamp("issued_at", { withTimezone: true }).defaultNow().notNull(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [
    // Migration 29: deployment_id / assessment_id phải cùng workspace với
    // deployment/assessment cha tương ứng — composite FK, NOT VALID trên 1
    // row rác lịch sử mỗi quan hệ (xem migration 29 up.sql), vẫn enforce
    // đầy đủ cho ghi mới.
    foreignKey({
      name: "ai_compliance_snapshots_workspace_deployment_fk",
      columns: [t.workspaceId, t.deploymentId],
      foreignColumns: [workspaceAiDeployments.workspaceId, workspaceAiDeployments.id],
    }),
    foreignKey({
      name: "ai_compliance_snapshots_workspace_assessment_fk",
      columns: [t.workspaceId, t.assessmentId],
      foreignColumns: [aiRiskAssessments.workspaceId, aiRiskAssessments.id],
    }),
    // Migration 29 mục 3: provider_profile_id / data_profile_id phải cùng
    // workspace với provider/data profile cha tương ứng — composite FK, VÀ
    // validated ngay (không NOT VALID) vì cột hoàn toàn mới + backfill chỉ
    // set giá trị verified (xem migration 29 up.sql mục 3).
    foreignKey({
      name: "ai_compliance_snapshots_workspace_provider_fk",
      columns: [t.workspaceId, t.providerProfileId],
      foreignColumns: [aiProviderProfiles.workspaceId, aiProviderProfiles.id],
    }),
    foreignKey({
      name: "ai_compliance_snapshots_workspace_data_profile_fk",
      columns: [t.workspaceId, t.dataProfileId],
      foreignColumns: [aiDataProcessingProfiles.workspaceId, aiDataProcessingProfiles.id],
    }),
  ]
);

