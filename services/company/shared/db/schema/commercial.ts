import { pgSchema, text, bigint, timestamp, boolean, doublePrecision, jsonb, varchar, date, integer } from "drizzle-orm/pg-core";

export const salesSchema = pgSchema("sales");
export const commercialSchema = pgSchema("commercial");

export const accounts = salesSchema.table("accounts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: text("name").notNull(),
  domain: text("domain"),
  industry: text("industry"),
  sizeSegment: text("size_segment"),
  country: text("country"),
  source: text("source"),
  lifecycleStatus: text("lifecycle_status").default("TARGET").notNull(),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  tags: jsonb("tags"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const contacts = salesSchema.table("contacts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  accountId: bigint("account_id", { mode: "bigint" }).references(() => accounts.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  title: text("title"),
  phone: text("phone"),
  email: text("email"),
  source: text("source"),
  consentStatus: text("consent_status"),
  doNotContact: boolean("do_not_contact").default(false).notNull(),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const salesLeads = salesSchema.table("sales_leads", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  keyResultId: bigint("key_result_id", { mode: "bigint" }),
  accountId: bigint("account_id", { mode: "bigint" }).references(() => accounts.id, { onDelete: "set null" }),
  contactId: bigint("contact_id", { mode: "bigint" }).references(() => contacts.id, { onDelete: "set null" }),
  name: text("name").notNull(),
  company: text("company"),
  stage: text("stage").default("NEW").notNull(),
  value: doublePrecision("value"),
  source: text("source"),
  sourceCampaignId: bigint("source_campaign_id", { mode: "bigint" }),
  sourceExperimentId: bigint("source_experiment_id", { mode: "bigint" }),
  utmSource: text("utm_source"),
  utmMedium: text("utm_medium"),
  utmCampaign: text("utm_campaign"),
  utmContent: text("utm_content"),
  utmTerm: text("utm_term"),
  fitScore: doublePrecision("fit_score"),
  intentScore: doublePrecision("intent_score"),
  engagementScore: doublePrecision("engagement_score"),
  qualificationStatus: text("qualification_status"),
  disqualificationReason: text("disqualification_reason"),
  nextActionAt: timestamp("next_action_at", { withTimezone: true }),
  nextActionType: text("next_action_type"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const salesOpportunities = salesSchema.table("sales_opportunities", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  cycleId: bigint("cycle_id", { mode: "bigint" }),
  accountId: bigint("account_id", { mode: "bigint" }).notNull().references(() => accounts.id, { onDelete: "cascade" }),
  primaryContactId: bigint("primary_contact_id", { mode: "bigint" }).references(() => contacts.id, { onDelete: "set null" }),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  sourceLeadId: bigint("source_lead_id", { mode: "bigint" }).references(() => salesLeads.id, { onDelete: "set null" }),
  product: text("product"),
  stage: text("stage").default("DISCOVERY").notNull(),
  estimatedValue: doublePrecision("estimated_value"),
  currency: text("currency").default("VND").notNull(),
  probability: doublePrecision("probability"),
  expectedCloseDate: date("expected_close_date"),
  painPoints: jsonb("pain_points"),
  needs: jsonb("needs"),
  objections: jsonb("objections"),
  competitors: jsonb("competitors"),
  nextAction: text("next_action"),
  nextActionDueAt: timestamp("next_action_due_at", { withTimezone: true }),
  wonReason: text("won_reason"),
  lostReason: text("lost_reason"),
  lostReasonDetail: text("lost_reason_detail"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const customers = salesSchema.table("customers", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  accountId: bigint("account_id", { mode: "bigint" }).notNull().references(() => accounts.id, { onDelete: "cascade" }),
  acquiredFromOpportunityId: bigint("acquired_from_opportunity_id", { mode: "bigint" }).references(() => salesOpportunities.id, { onDelete: "set null" }),
  lifecycleStatus: text("lifecycle_status").default("ONBOARDING").notNull(),
  activationStatus: text("activation_status"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  firstPurchaseAt: timestamp("first_purchase_at", { withTimezone: true }),
  renewalDate: date("renewal_date"),
  healthStatus: text("health_status").default("HEALTHY").notNull(),
  lastSuccessInteractionAt: timestamp("last_success_interaction_at", { withTimezone: true }),
  nextSuccessActionAt: timestamp("next_success_action_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingContexts = commercialSchema.table("marketing_contexts", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  revision: integer("revision").default(1).notNull(),
  status: text("status").default("draft").notNull(),
  updatedByUserId: bigint("updated_by_user_id", { mode: "bigint" }),
  reviewedByUserId: bigint("reviewed_by_user_id", { mode: "bigint" }),
  reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
  sourceSkillId: varchar("source_skill_id", { length: 100 }),
  sourceSkillVersion: varchar("source_skill_version", { length: 50 }),
  sourceSkillHash: varchar("source_skill_hash", { length: 64 }),
  offerArchitecture: jsonb("offer_architecture"),
  twelveWeekPlan: jsonb("twelve_week_plan"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingContextRevisions = commercialSchema.table("marketing_context_revisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  contextId: bigint("context_id", { mode: "bigint" }).notNull().references(() => marketingContexts.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  revision: integer("revision").notNull(),
  snapshot: jsonb("snapshot").notNull(),
  createdByUserId: bigint("created_by_user_id", { mode: "bigint" }),
  sourceSkillId: varchar("source_skill_id", { length: 100 }),
  sourceSkillVersion: varchar("source_skill_version", { length: 50 }),
  sourceSkillHash: varchar("source_skill_hash", { length: 64 }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingProductMarketing = commercialSchema.table("marketing_product_marketing", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  contextId: bigint("context_id", { mode: "bigint" }).notNull().references(() => marketingContexts.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  category: varchar("category", { length: 255 }),
  positioningStatement: text("positioning_statement"),
  alternatives: jsonb("alternatives").default([]),
  differentiators: jsonb("differentiators").default([]),
  brandVoice: jsonb("brand_voice").default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingIcpSegments = commercialSchema.table("marketing_icp_segments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  contextId: bigint("context_id", { mode: "bigint" }).notNull().references(() => marketingContexts.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  segment: text("segment").notNull(),
  confidence: varchar("confidence", { length: 20 }).default("medium").notNull(),
  evidenceIds: jsonb("evidence_ids").default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingCustomerResearchThemes = commercialSchema.table("marketing_customer_research_themes", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  contextId: bigint("context_id", { mode: "bigint" }).notNull().references(() => marketingContexts.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  type: varchar("type", { length: 50 }).notNull(),
  summary: text("summary").notNull(),
  confidence: varchar("confidence", { length: 20 }).default("medium").notNull(),
  evidenceIds: jsonb("evidence_ids").default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingCustomerLanguage = commercialSchema.table("marketing_customer_language", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  contextId: bigint("context_id", { mode: "bigint" }).notNull().references(() => marketingContexts.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  quote: text("quote").notNull(),
  sourceId: varchar("source_id", { length: 100 }),
  capturedAt: timestamp("captured_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingContextEvidence = commercialSchema.table("marketing_context_evidence", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  contextId: bigint("context_id", { mode: "bigint" }).notNull().references(() => marketingContexts.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  evidenceId: varchar("evidence_id", { length: 100 }).notNull(),
  kind: varchar("kind", { length: 50 }).notNull(),
  sourceUrl: text("source_url"),
  capturedAt: timestamp("captured_at", { withTimezone: true }),
  capturedBy: varchar("captured_by", { length: 100 }),
  confidence: varchar("confidence", { length: 20 }).default("medium").notNull(),
  trust: varchar("trust", { length: 20 }).default("unreviewed").notNull(),
  sensitivity: varchar("sensitivity", { length: 20 }).default("internal").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingCampaigns = commercialSchema.table("marketing_campaigns", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  funnelStage: varchar("funnel_stage", { length: 50 }).default("discover").notNull(),
  channels: jsonb("channels"),
  budget: doublePrecision("budget"),
  status: varchar("status", { length: 50 }).default("draft").notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const campaignAssets = commercialSchema.table("campaign_assets", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  campaignId: bigint("campaign_id", { mode: "bigint" }).notNull().references(() => marketingCampaigns.id, { onDelete: "cascade" }),
  assetType: varchar("asset_type", { length: 50 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  content: text("content").notNull(),
  status: varchar("status", { length: 50 }).default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingForms = commercialSchema.table("marketing_forms", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  slug: varchar("slug", { length: 255 }).notNull(),
  fieldsSchema: jsonb("fields_schema").default([]).notNull(),
  isPublished: boolean("is_published").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingLeadIntakes = commercialSchema.table("marketing_lead_intakes", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  formId: bigint("form_id", { mode: "bigint" }).references(() => marketingForms.id, { onDelete: "set null" }),
  contactData: jsonb("contact_data").default({}).notNull(),
  source: varchar("source", { length: 100 }),
  status: varchar("status", { length: 50 }).default("new").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const invoices = commercialSchema.table("invoices", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  customerId: bigint("customer_id", { mode: "bigint" }).references(() => customers.id, { onDelete: "set null" }),
  invoiceNumber: varchar("invoice_number", { length: 100 }).notNull(),
  amount: doublePrecision("amount").notNull(),
  currency: varchar("currency", { length: 10 }).default("VND").notNull(),
  status: varchar("status", { length: 50 }).default("draft").notNull(),
  dueDate: timestamp("due_date", { withTimezone: true }),
  paidAt: timestamp("paid_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const subscriptions = commercialSchema.table("subscriptions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  customerId: bigint("customer_id", { mode: "bigint" }).references(() => customers.id, { onDelete: "set null" }),
  planName: varchar("plan_name", { length: 100 }).notNull(),
  billingCycle: varchar("billing_cycle", { length: 50 }).default("monthly").notNull(),
  price: doublePrecision("price").notNull(),
  currency: varchar("currency", { length: 10 }).default("VND").notNull(),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  currentPeriodStart: timestamp("current_period_start", { withTimezone: true }),
  currentPeriodEnd: timestamp("current_period_end", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingObjectives = commercialSchema.table("marketing_objectives", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  targetMetric: varchar("target_metric", { length: 100 }),
  targetValue: doublePrecision("target_value"),
  currentValue: doublePrecision("current_value"),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingExperiments = commercialSchema.table("marketing_experiments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  campaignId: bigint("campaign_id", { mode: "bigint" }).references(() => marketingCampaigns.id, { onDelete: "set null" }),
  name: varchar("name", { length: 255 }).notNull(),
  hypothesis: text("hypothesis").notNull(),
  status: varchar("status", { length: 50 }).default("draft").notNull(),
  baselineMetric: varchar("baseline_metric", { length: 100 }),
  baselineValue: doublePrecision("baseline_value"),
  targetMetric: varchar("target_metric", { length: 100 }),
  targetValue: doublePrecision("target_value"),
  actualValue: doublePrecision("actual_value"),
  conclusion: text("conclusion"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const marketingLearnings = commercialSchema.table("marketing_learnings", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  experimentId: bigint("experiment_id", { mode: "bigint" }).references(() => marketingExperiments.id, { onDelete: "set null" }),
  title: varchar("title", { length: 255 }).notNull(),
  insight: text("insight").notNull(),
  impact: varchar("impact", { length: 50 }).default("medium").notNull(),
  actionItems: jsonb("action_items").default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingMetricDefinitions = commercialSchema.table("marketing_metric_definitions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: varchar("name", { length: 100 }).notNull(),
  unit: varchar("unit", { length: 50 }).default("count").notNull(),
  description: text("description"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingMetricObservations = commercialSchema.table("marketing_metric_observations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  metricId: bigint("metric_id", { mode: "bigint" }).notNull().references(() => marketingMetricDefinitions.id, { onDelete: "cascade" }),
  providerKey: text("provider_key").notNull(),
  sourceRecordId: text("source_record_id").notNull(),
  payloadHash: text("payload_hash").notNull(),
  observedAt: timestamp("observed_at", { withTimezone: true }).notNull(),
  ingestedAt: timestamp("ingested_at", { withTimezone: true }).defaultNow().notNull(),
  value: doublePrecision("value").notNull(),
  metadata: jsonb("metadata").default({}).notNull(),
});

export const marketingAttributions = commercialSchema.table("marketing_attributions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  campaignId: bigint("campaign_id", { mode: "bigint" }).references(() => marketingCampaigns.id, { onDelete: "set null" }),
  channel: varchar("channel", { length: 100 }).notNull(),
  touchpointType: varchar("touchpoint_type", { length: 50 }).notNull(),
  conversions: doublePrecision("conversions").default(0).notNull(),
  revenue: doublePrecision("revenue").default(0).notNull(),
  observedAt: timestamp("observed_at", { withTimezone: true }).defaultNow().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingDecisions = commercialSchema.table("marketing_decisions", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  campaignId: bigint("campaign_id", { mode: "bigint" }).references(() => marketingCampaigns.id, { onDelete: "set null" }),
  title: varchar("title", { length: 255 }).notNull(),
  rationale: text("rationale").notNull(),
  decisionType: varchar("decision_type", { length: 50 }).notNull(),
  status: varchar("status", { length: 50 }).default("active").notNull(),
  createdBy: varchar("created_by", { length: 255 }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const marketingProposals = commercialSchema.table("marketing_proposals", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  proposalType: varchar("proposal_type", { length: 50 }).notNull(),
  origin: varchar("origin", { length: 50 }).notNull(),
  status: varchar("status", { length: 50 }).notNull(),
  sourceRefs: jsonb("source_refs").default([]).notNull(),
  body: jsonb("body").default({}).notNull(),
  createdBy: varchar("created_by", { length: 255 }).notNull(),
  reviewedBy: varchar("reviewed_by", { length: 255 }),
  reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
