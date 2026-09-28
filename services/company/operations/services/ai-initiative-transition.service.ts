import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  assertInitiativeInWorkspace,
  InitiativeLifecycleState,
  AiInitiative,
  InitiativeKind,
  InitiativeRiskTier,
  InitiativeAutonomyTier,
  LegacyRemediationState,
} from "./initiative.service";
import {
  getActiveValueContract,
  getActiveDataReadinessAssessment,
  getActiveBudgetPolicy,
  recordInitiativeDecision,
  AiInitiativeDecision,
} from "./ai-initiative-evidence.service";
import {
  evaluateAiInitiativePromotionGates,
  AiInitiativeGateStatus,
} from "./ai-initiative-promotion-policy";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";

const { initiatives } = schema;

export interface TransitionAiInitiativeParams {
  workspaceId: string;
  projectId: string;
  initiativeId: string;
  targetState: InitiativeLifecycleState;
  expectedRevision: number;
  reasonCode: string;
  reason?: string;
  idempotencyKey?: string;
  humanEscalationRoute?: string;
  rollbackPauseProcedure?: string;
}

export interface AiInitiativeTransitionResult {
  lifecycleState: InitiativeLifecycleState;
  initiative: AiInitiative;
  decision: AiInitiativeDecision;
  previousState: InitiativeLifecycleState;
  currentState: InitiativeLifecycleState;
  gatesEvaluated: readonly AiInitiativeGateStatus[];
}

export async function transitionAiInitiative(
  params: TransitionAiInitiativeParams,
  ctx: TenantContext
): Promise<AiInitiativeTransitionResult> {
  if (ctx.workspaceId !== params.workspaceId) {
    throw APIError.permissionDenied("workspace context mismatch");
  }

  const existing = await assertInitiativeInWorkspace(params.initiativeId, params.workspaceId);

  if (existing.projectId && existing.projectId.toString() !== params.projectId) {
    throw APIError.invalidArgument("Project does not match initiative project");
  }

  if (existing.revision !== params.expectedRevision) {
    throw APIError.aborted(
      `Revision conflict: current revision is ${existing.revision}, expected ${params.expectedRevision}`
    );
  }

  if (existing.autonomyTier === "A3") {
    throw APIError.invalidArgument("unsupported_autonomy_tier");
  }

  const wsId = BigInt(params.workspaceId);
  const fromState = existing.lifecycleState as InitiativeLifecycleState;
  const toState = params.targetState;

  // Gather existing evidence
  const valContract = await getActiveValueContract(params.workspaceId, params.initiativeId);
  const dataAssessment = await getActiveDataReadinessAssessment(params.workspaceId, params.initiativeId);
  const budgetPolicy = await getActiveBudgetPolicy(params.workspaceId, params.initiativeId);

  const gates = evaluateAiInitiativePromotionGates({
    fromState,
    toState,
    riskTier: existing.riskTier,
    autonomyTier: existing.autonomyTier,
    approvalStatus: existing.approvalStatus,
    legacyRemediationState: existing.legacyRemediationState,
    hasProblemStatement: Boolean(existing.businessProblem || existing.description),
    hasIntendedOutcome: Boolean(existing.intendedOutcome),
    hasOwner: Boolean(existing.ownerMemberId),
    hasValueContract: Boolean(valContract),
    hasBaseline: Boolean(valContract?.baselineValue && valContract?.baselineSourceRef),
    hasDataAssessment: Boolean(dataAssessment),
    dataAssessmentStatus: dataAssessment?.assessmentStatus,
    hasEvaluationSuite: true, // pinned in T7
    hasBudgetPolicy: Boolean(budgetPolicy),
    hasHumanEscalationRoute: Boolean(params.humanEscalationRoute),
    hasRollbackPauseProcedure: Boolean(params.rollbackPauseProcedure),
  });

  if (gates.length > 0) {
    if (gates.includes("APPROVAL_STATUS_REQUIRED")) {
      throw APIError.failedPrecondition("approvalStatus must be APPROVED");
    }
    if (gates.includes("UNSUPPORTED_AUTONOMY_TIER")) {
      throw APIError.invalidArgument("unsupported_autonomy_tier");
    }
    throw APIError.failedPrecondition(`Promotion gates failed: ${gates.join(", ")}`);
  }

  const nextRevision = existing.revision + 1;

  const [updated] = await db
    .update(initiatives)
    .set({
      lifecycleState: toState,
      revision: nextRevision,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(initiatives.id, existing.id),
        eq(initiatives.workspaceId, wsId),
        eq(initiatives.revision, existing.revision)
      )
    )
    .returning();

  if (!updated) {
    throw APIError.aborted(
      `Revision conflict: initiative ${params.initiativeId} changed concurrently`
    );
  }

  const decision = await recordInitiativeDecision(ctx, {
    workspaceId: params.workspaceId,
    projectId: params.projectId,
    initiativeId: params.initiativeId,
    revision: nextRevision,
    decision: `${fromState}_TO_${toState}`,
    fromState,
    toState,
    actorMemberId: ctx.workforceMemberId || null,
    reasonCode: params.reasonCode,
    reason: params.reason || null,
    gateSnapshot: { gates, evaluatedAt: new Date().toISOString() },
    idempotencyKey: params.idempotencyKey,
  });

  // Outbox delivery
  const event = makeBusinessEvent({
    eventType: "ai.initiative.promoted.v1",
    workspaceId: params.workspaceId,
    projectId: params.projectId,
    aggregateType: "ai_initiative",
    aggregateId: params.initiativeId,
    correlationId: ctx.correlationId || "corr-transition",
    actor: {
      kind: "user",
      id: ctx.userId || "system",
    },
    classification: "internal",
    payload: {
      initiative_id: params.initiativeId,
      project_id: params.projectId,
      from_state: fromState,
      to_state: toState,
      revision: nextRevision,
      decision_id: decision.id,
    },
  });

  await appendOutboxEvent(db, event);

  const aiInitiative: AiInitiative = {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    projectId: params.projectId,
    title: updated.title,
    description: updated.description,
    intendedOutcome: updated.intendedOutcome,
    businessProblem: updated.businessProblem ?? null,
    startDate: updated.startDate ? updated.startDate.toISOString() : null,
    targetDate: updated.targetDate ? updated.targetDate.toISOString() : null,
    milestones: (updated.milestones as any[]) || [],
    status: updated.status,
    approvalStatus: updated.approvalStatus,
    approvedByMemberId: updated.approvedByMemberId ? updated.approvedByMemberId.toString() : null,
    approvedAt: updated.approvedAt ? updated.approvedAt.toISOString() : null,
    decisionId: updated.decisionId ? updated.decisionId.toString() : null,
    settingsRevision: updated.settingsRevision ?? null,
    ownerMemberId: updated.ownerMemberId ? updated.ownerMemberId.toString() : null,
    businessOwnerMemberId: updated.ownerMemberId ? updated.ownerMemberId.toString() : "",
    revision: updated.revision,
    keyResultIds: [updated.keyResultId.toString()],
    initiativeKind: "AI",
    lifecycleState: updated.lifecycleState as InitiativeLifecycleState,
    riskTier: updated.riskTier as InitiativeRiskTier,
    autonomyTier: updated.autonomyTier as InitiativeAutonomyTier,
    technicalOwnerMemberId: updated.technicalOwnerMemberId ? updated.technicalOwnerMemberId.toString() : null,
    riskOwnerMemberId: updated.riskOwnerMemberId ? updated.riskOwnerMemberId.toString() : null,
    legacyRemediationState: updated.legacyRemediationState as LegacyRemediationState,
    createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
  };

  return {
    lifecycleState: toState,
    initiative: aiInitiative,
    decision,
    previousState: fromState,
    currentState: toState,
    gatesEvaluated: gates,
  };
}
