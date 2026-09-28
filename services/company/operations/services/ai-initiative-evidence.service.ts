import { APIError } from "encore.dev/api";
import { eq, and, desc, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { assertInitiativeInWorkspace } from "./initiative.service";

const {
  aiInitiativeValueContracts,
  aiInitiativeDataReadinessAssessments,
  aiInitiativeBudgetPolicies,
  aiInitiativeDecisions,
  aiInitiativeValueMeasurements,
} = schema;

export interface AiValueContract {
  id: string;
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  revision: number;
  metricContractId: string;
  baselineValue: string;
  baselineObservedAt: string;
  baselineSourceRef: string;
  targetValue: string;
  targetBy: string;
  measurementWindow: string;
  unit: string;
  scoringDirection: string;
  expectedValueMethod: string;
  expectedValueAmount: string | null;
  currency: string;
  adoptionTarget: string | null;
  adoptionWindow: string | null;
  measurementOwnerMemberId: string;
  createdAt: string;
}

export interface RecordValueContractParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  metricContractId: string;
  baselineValue: string;
  baselineObservedAt: string;
  baselineSourceRef: string;
  targetValue: string;
  targetBy: string;
  measurementWindow: string;
  unit: string;
  scoringDirection?: "ASC" | "DESC";
  expectedValueMethod: string;
  expectedValueAmount?: string | null;
  currency?: string;
  adoptionTarget?: string | null;
  adoptionWindow?: string | null;
  measurementOwnerMemberId: string;
}

export interface AiDataReadinessAssessment {
  id: string;
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  revision: number;
  sourceRefs: string[];
  classification: string;
  accessAuthorityRef: string;
  freshnessSlo: string;
  qualityDimensions: Record<string, unknown>;
  metadataOwnerMemberId: string;
  retrievalMode: "none" | "lexical" | "semantic";
  knowledgeSnapshotRef: string | null;
  assessmentStatus: "NOT_READY" | "CONDITIONAL" | "READY";
  evidenceRefs: string[];
  createdAt: string;
}

export interface RecordDataReadinessAssessmentParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  sourceRefs: string[];
  classification: string;
  accessAuthorityRef: string;
  freshnessSlo: string;
  qualityDimensions?: Record<string, unknown>;
  metadataOwnerMemberId: string;
  retrievalMode?: "none" | "lexical" | "semantic";
  knowledgeSnapshotRef?: string | null;
  assessmentStatus: "NOT_READY" | "CONDITIONAL" | "READY";
  evidenceRefs?: string[];
}

export interface AiBudgetPolicy {
  id: string;
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  revision: number;
  period: "MONTHLY" | "WEEKLY" | "TOTAL";
  currency: string;
  softCostThreshold: string;
  hardCostThreshold: string;
  actionOnBreach: "WARN" | "REQUIRE_APPROVAL" | "PAUSE_INITIATIVE";
  allowedModels: string[];
  createdAt: string;
}

export interface SetBudgetPolicyParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  period?: "MONTHLY" | "WEEKLY" | "TOTAL";
  currency?: string;
  softCostThreshold: string;
  hardCostThreshold: string;
  actionOnBreach?: "WARN" | "REQUIRE_APPROVAL" | "PAUSE_INITIATIVE";
  allowedModels?: string[];
}

export interface AiInitiativeDecision {
  id: string;
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  revision: number;
  decision: string;
  fromState: string;
  toState: string;
  actorMemberId: string | null;
  reasonCode: string;
  reason: string | null;
  gateSnapshot: Record<string, unknown>;
  idempotencyKey: string | null;
  decidedAt: string;
}

export interface RecordDecisionParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  revision?: number;
  decision: string;
  fromState: string;
  toState: string;
  actorMemberId?: string | null;
  reasonCode: string;
  reason?: string | null;
  gateSnapshot?: Record<string, unknown>;
  idempotencyKey?: string | null;
}

export interface AiValueMeasurement {
  id: string;
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  metricContractId: string;
  observedValue: string | null;
  state: "PRESENT" | "UNAVAILABLE" | "INVALID";
  observedAt: string;
  windowStart: string;
  windowEnd: string;
  qualityState: string;
  missingDataState: string | null;
  measurementOwnerMemberId: string | null;
  createdAt: string;
}

export interface RecordMeasurementParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  metricContractId: string;
  observedValue?: string | null;
  state?: "PRESENT" | "UNAVAILABLE" | "INVALID";
  observedAt?: string;
  windowStart: string;
  windowEnd: string;
  qualityState?: string;
  missingDataState?: string | null;
  measurementOwnerMemberId?: string | null;
}

export async function recordValueContract(
  ctx: TenantContext,
  params: RecordValueContractParams
): Promise<AiValueContract> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context mismatch");
  }

  if (!params.baselineSourceRef || params.baselineSourceRef.trim().length === 0) {
    throw APIError.invalidArgument("baseline_source_ref is required");
  }

  await assertInitiativeInWorkspace(params.initiativeId, params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  // Compute next revision
  const [revRow] = await db
    .select({ maxRev: sql<number>`COALESCE(MAX(revision), 0)` })
    .from(aiInitiativeValueContracts)
    .where(eq(aiInitiativeValueContracts.initiativeId, initId));

  const nextRev = (Number(revRow?.maxRev) || 0) + 1;
  const id = generateSnowflake();

  const [row] = await db
    .insert(aiInitiativeValueContracts)
    .values({
      id,
      workspaceId: wsId,
      projectId: projId,
      initiativeId: initId,
      revision: nextRev,
      metricContractId: params.metricContractId,
      baselineValue: params.baselineValue,
      baselineObservedAt: new Date(params.baselineObservedAt),
      baselineSourceRef: params.baselineSourceRef.trim(),
      targetValue: params.targetValue,
      targetBy: new Date(params.targetBy),
      measurementWindow: params.measurementWindow,
      unit: params.unit,
      scoringDirection: params.scoringDirection || "ASC",
      expectedValueMethod: params.expectedValueMethod,
      expectedValueAmount: params.expectedValueAmount || null,
      currency: params.currency || "VND",
      adoptionTarget: params.adoptionTarget || null,
      adoptionWindow: params.adoptionWindow || null,
      measurementOwnerMemberId: BigInt(params.measurementOwnerMemberId),
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    metricContractId: row.metricContractId,
    baselineValue: String(row.baselineValue),
    baselineObservedAt: row.baselineObservedAt.toISOString(),
    baselineSourceRef: row.baselineSourceRef,
    targetValue: String(row.targetValue),
    targetBy: row.targetBy.toISOString(),
    measurementWindow: row.measurementWindow,
    unit: row.unit,
    scoringDirection: row.scoringDirection,
    expectedValueMethod: row.expectedValueMethod,
    expectedValueAmount: row.expectedValueAmount !== null ? String(row.expectedValueAmount) : null,
    currency: row.currency,
    adoptionTarget: row.adoptionTarget !== null ? String(row.adoptionTarget) : null,
    adoptionWindow: row.adoptionWindow,
    measurementOwnerMemberId: row.measurementOwnerMemberId.toString(),
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getActiveValueContract(
  workspaceId: string,
  initiativeId: string
): Promise<AiValueContract | null> {
  const wsId = BigInt(workspaceId);
  const initId = BigInt(initiativeId);

  const [row] = await db
    .select()
    .from(aiInitiativeValueContracts)
    .where(
      and(
        eq(aiInitiativeValueContracts.workspaceId, wsId),
        eq(aiInitiativeValueContracts.initiativeId, initId)
      )
    )
    .orderBy(desc(aiInitiativeValueContracts.revision))
    .limit(1);

  if (!row) return null;

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    metricContractId: row.metricContractId,
    baselineValue: String(row.baselineValue),
    baselineObservedAt: row.baselineObservedAt.toISOString(),
    baselineSourceRef: row.baselineSourceRef,
    targetValue: String(row.targetValue),
    targetBy: row.targetBy.toISOString(),
    measurementWindow: row.measurementWindow,
    unit: row.unit,
    scoringDirection: row.scoringDirection,
    expectedValueMethod: row.expectedValueMethod,
    expectedValueAmount: row.expectedValueAmount !== null ? String(row.expectedValueAmount) : null,
    currency: row.currency,
    adoptionTarget: row.adoptionTarget !== null ? String(row.adoptionTarget) : null,
    adoptionWindow: row.adoptionWindow,
    measurementOwnerMemberId: row.measurementOwnerMemberId.toString(),
    createdAt: row.createdAt.toISOString(),
  };
}

export async function recordDataReadinessAssessment(
  ctx: TenantContext,
  params: RecordDataReadinessAssessmentParams
): Promise<AiDataReadinessAssessment> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context mismatch");
  }

  await assertInitiativeInWorkspace(params.initiativeId, params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  const [revRow] = await db
    .select({ maxRev: sql<number>`COALESCE(MAX(revision), 0)` })
    .from(aiInitiativeDataReadinessAssessments)
    .where(eq(aiInitiativeDataReadinessAssessments.initiativeId, initId));

  const nextRev = (Number(revRow?.maxRev) || 0) + 1;
  const id = generateSnowflake();

  const [row] = await db
    .insert(aiInitiativeDataReadinessAssessments)
    .values({
      id,
      workspaceId: wsId,
      projectId: projId,
      initiativeId: initId,
      revision: nextRev,
      sourceRefs: params.sourceRefs || [],
      classification: params.classification,
      accessAuthorityRef: params.accessAuthorityRef,
      freshnessSlo: params.freshnessSlo,
      qualityDimensions: params.qualityDimensions || {},
      metadataOwnerMemberId: BigInt(params.metadataOwnerMemberId),
      retrievalMode: params.retrievalMode || "none",
      knowledgeSnapshotRef: params.knowledgeSnapshotRef || null,
      assessmentStatus: params.assessmentStatus,
      evidenceRefs: params.evidenceRefs || [],
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    sourceRefs: row.sourceRefs as string[],
    classification: row.classification,
    accessAuthorityRef: row.accessAuthorityRef,
    freshnessSlo: row.freshnessSlo,
    qualityDimensions: row.qualityDimensions as Record<string, unknown>,
    metadataOwnerMemberId: row.metadataOwnerMemberId.toString(),
    retrievalMode: row.retrievalMode as "none" | "lexical" | "semantic",
    knowledgeSnapshotRef: row.knowledgeSnapshotRef,
    assessmentStatus: row.assessmentStatus as "NOT_READY" | "CONDITIONAL" | "READY",
    evidenceRefs: row.evidenceRefs as string[],
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getActiveDataReadinessAssessment(
  workspaceId: string,
  initiativeId: string
): Promise<AiDataReadinessAssessment | null> {
  const wsId = BigInt(workspaceId);
  const initId = BigInt(initiativeId);

  const [row] = await db
    .select()
    .from(aiInitiativeDataReadinessAssessments)
    .where(
      and(
        eq(aiInitiativeDataReadinessAssessments.workspaceId, wsId),
        eq(aiInitiativeDataReadinessAssessments.initiativeId, initId)
      )
    )
    .orderBy(desc(aiInitiativeDataReadinessAssessments.revision))
    .limit(1);

  if (!row) return null;

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    sourceRefs: row.sourceRefs as string[],
    classification: row.classification,
    accessAuthorityRef: row.accessAuthorityRef,
    freshnessSlo: row.freshnessSlo,
    qualityDimensions: row.qualityDimensions as Record<string, unknown>,
    metadataOwnerMemberId: row.metadataOwnerMemberId.toString(),
    retrievalMode: row.retrievalMode as "none" | "lexical" | "semantic",
    knowledgeSnapshotRef: row.knowledgeSnapshotRef,
    assessmentStatus: row.assessmentStatus as "NOT_READY" | "CONDITIONAL" | "READY",
    evidenceRefs: row.evidenceRefs as string[],
    createdAt: row.createdAt.toISOString(),
  };
}

export async function setBudgetPolicy(
  ctx: TenantContext,
  params: SetBudgetPolicyParams
): Promise<AiBudgetPolicy> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context mismatch");
  }

  await assertInitiativeInWorkspace(params.initiativeId, params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  const [revRow] = await db
    .select({ maxRev: sql<number>`COALESCE(MAX(revision), 0)` })
    .from(aiInitiativeBudgetPolicies)
    .where(eq(aiInitiativeBudgetPolicies.initiativeId, initId));

  const nextRev = (Number(revRow?.maxRev) || 0) + 1;
  const id = generateSnowflake();

  const [row] = await db
    .insert(aiInitiativeBudgetPolicies)
    .values({
      id,
      workspaceId: wsId,
      projectId: projId,
      initiativeId: initId,
      revision: nextRev,
      period: params.period || "MONTHLY",
      currency: params.currency || "USD",
      softCostThreshold: params.softCostThreshold,
      hardCostThreshold: params.hardCostThreshold,
      actionOnBreach: params.actionOnBreach || "WARN",
      allowedModels: params.allowedModels || [],
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    period: row.period as "MONTHLY" | "WEEKLY" | "TOTAL",
    currency: row.currency,
    softCostThreshold: String(row.softCostThreshold),
    hardCostThreshold: String(row.hardCostThreshold),
    actionOnBreach: row.actionOnBreach as "WARN" | "REQUIRE_APPROVAL" | "PAUSE_INITIATIVE",
    allowedModels: row.allowedModels as string[],
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getActiveBudgetPolicy(
  workspaceId: string,
  initiativeId: string
): Promise<AiBudgetPolicy | null> {
  const wsId = BigInt(workspaceId);
  const initId = BigInt(initiativeId);

  const [row] = await db
    .select()
    .from(aiInitiativeBudgetPolicies)
    .where(
      and(
        eq(aiInitiativeBudgetPolicies.workspaceId, wsId),
        eq(aiInitiativeBudgetPolicies.initiativeId, initId)
      )
    )
    .orderBy(desc(aiInitiativeBudgetPolicies.revision))
    .limit(1);

  if (!row) return null;

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    period: row.period as "MONTHLY" | "WEEKLY" | "TOTAL",
    currency: row.currency,
    softCostThreshold: String(row.softCostThreshold),
    hardCostThreshold: String(row.hardCostThreshold),
    actionOnBreach: row.actionOnBreach as "WARN" | "REQUIRE_APPROVAL" | "PAUSE_INITIATIVE",
    allowedModels: row.allowedModels as string[],
    createdAt: row.createdAt.toISOString(),
  };
}

export async function recordInitiativeDecision(
  ctx: TenantContext,
  params: RecordDecisionParams
): Promise<AiInitiativeDecision> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context mismatch");
  }

  const existingInit = await assertInitiativeInWorkspace(params.initiativeId, params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  // Idempotency check
  if (params.idempotencyKey) {
    const [existing] = await db
      .select()
      .from(aiInitiativeDecisions)
      .where(
        and(
          eq(aiInitiativeDecisions.initiativeId, initId),
          eq(aiInitiativeDecisions.idempotencyKey, params.idempotencyKey)
        )
      )
      .limit(1);

    if (existing) {
      return {
        id: existing.id.toString(),
        workspaceId: existing.workspaceId.toString(),
        projectId: existing.projectId.toString(),
        initiativeId: existing.initiativeId.toString(),
        revision: existing.revision,
        decision: existing.decision,
        fromState: existing.fromState,
        toState: existing.toState,
        actorMemberId: existing.actorMemberId ? existing.actorMemberId.toString() : null,
        reasonCode: existing.reasonCode,
        reason: existing.reason,
        gateSnapshot: existing.gateSnapshot as Record<string, unknown>,
        idempotencyKey: existing.idempotencyKey,
        decidedAt: existing.decidedAt.toISOString(),
      };
    }
  }

  const id = generateSnowflake();
  const revision = params.revision !== undefined ? params.revision : existingInit.revision;
  const actorId = params.actorMemberId
    ? BigInt(params.actorMemberId)
    : ctx.workforceMemberId
    ? BigInt(ctx.workforceMemberId)
    : ctx.userId
    ? BigInt(ctx.userId)
    : null;

  const [row] = await db
    .insert(aiInitiativeDecisions)
    .values({
      id,
      workspaceId: wsId,
      projectId: projId,
      initiativeId: initId,
      revision,
      decision: params.decision,
      fromState: params.fromState,
      toState: params.toState,
      actorMemberId: actorId,
      reasonCode: params.reasonCode,
      reason: params.reason || null,
      gateSnapshot: params.gateSnapshot || {},
      idempotencyKey: params.idempotencyKey || null,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    revision: row.revision,
    decision: row.decision,
    fromState: row.fromState,
    toState: row.toState,
    actorMemberId: row.actorMemberId ? row.actorMemberId.toString() : null,
    reasonCode: row.reasonCode,
    reason: row.reason,
    gateSnapshot: row.gateSnapshot as Record<string, unknown>,
    idempotencyKey: row.idempotencyKey,
    decidedAt: row.decidedAt.toISOString(),
  };
}

export async function listInitiativeDecisions(
  workspaceId: string,
  initiativeId: string
): Promise<AiInitiativeDecision[]> {
  const wsId = BigInt(workspaceId);
  const initId = BigInt(initiativeId);

  const rows = await db
    .select()
    .from(aiInitiativeDecisions)
    .where(
      and(
        eq(aiInitiativeDecisions.workspaceId, wsId),
        eq(aiInitiativeDecisions.initiativeId, initId)
      )
    )
    .orderBy(desc(aiInitiativeDecisions.decidedAt));

  return rows.map((r) => ({
    id: r.id.toString(),
    workspaceId: r.workspaceId.toString(),
    projectId: r.projectId.toString(),
    initiativeId: r.initiativeId.toString(),
    revision: r.revision,
    decision: r.decision,
    fromState: r.fromState,
    toState: r.toState,
    actorMemberId: r.actorMemberId ? r.actorMemberId.toString() : null,
    reasonCode: r.reasonCode,
    reason: r.reason,
    gateSnapshot: r.gateSnapshot as Record<string, unknown>,
    idempotencyKey: r.idempotencyKey,
    decidedAt: r.decidedAt.toISOString(),
  }));
}

export async function recordMeasurement(
  ctx: TenantContext,
  params: RecordMeasurementParams
): Promise<AiValueMeasurement> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context mismatch");
  }

  await assertInitiativeInWorkspace(params.initiativeId, params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const projId = BigInt(params.projectId);
  const initId = BigInt(params.initiativeId);

  const id = generateSnowflake();
  const state = params.state || "PRESENT";
  const observedVal = (state === "PRESENT" && params.observedValue !== undefined) ? params.observedValue : null;

  const [row] = await db
    .insert(aiInitiativeValueMeasurements)
    .values({
      id,
      workspaceId: wsId,
      projectId: projId,
      initiativeId: initId,
      metricContractId: params.metricContractId,
      observedValue: observedVal,
      state,
      observedAt: params.observedAt ? new Date(params.observedAt) : new Date(),
      windowStart: new Date(params.windowStart),
      windowEnd: new Date(params.windowEnd),
      qualityState: params.qualityState || "GOOD",
      missingDataState: params.missingDataState || null,
      measurementOwnerMemberId: params.measurementOwnerMemberId ? BigInt(params.measurementOwnerMemberId) : null,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    metricContractId: row.metricContractId,
    observedValue: row.observedValue !== null ? String(row.observedValue) : null,
    state: row.state as "PRESENT" | "UNAVAILABLE" | "INVALID",
    observedAt: row.observedAt.toISOString(),
    windowStart: row.windowStart.toISOString(),
    windowEnd: row.windowEnd.toISOString(),
    qualityState: row.qualityState,
    missingDataState: row.missingDataState,
    measurementOwnerMemberId: row.measurementOwnerMemberId ? row.measurementOwnerMemberId.toString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getLatestMeasurement(
  workspaceId: string,
  initiativeId: string,
  metricContractId?: string
): Promise<AiValueMeasurement | null> {
  const wsId = BigInt(workspaceId);
  const initId = BigInt(initiativeId);

  const conditions = [
    eq(aiInitiativeValueMeasurements.workspaceId, wsId),
    eq(aiInitiativeValueMeasurements.initiativeId, initId),
  ];

  if (metricContractId) {
    conditions.push(eq(aiInitiativeValueMeasurements.metricContractId, metricContractId));
  }

  const [row] = await db
    .select()
    .from(aiInitiativeValueMeasurements)
    .where(and(...conditions))
    .orderBy(desc(aiInitiativeValueMeasurements.observedAt))
    .limit(1);

  if (!row) return null;

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    initiativeId: row.initiativeId.toString(),
    metricContractId: row.metricContractId,
    observedValue: row.observedValue !== null ? String(row.observedValue) : null,
    state: row.state as "PRESENT" | "UNAVAILABLE" | "INVALID",
    observedAt: row.observedAt.toISOString(),
    windowStart: row.windowStart.toISOString(),
    windowEnd: row.windowEnd.toISOString(),
    qualityState: row.qualityState,
    missingDataState: row.missingDataState,
    measurementOwnerMemberId: row.measurementOwnerMemberId ? row.measurementOwnerMemberId.toString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}
