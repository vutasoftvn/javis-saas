import { and, eq, isNull, inArray, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";

const {
  initiatives,
  aiInitiativeValueContracts,
  aiInitiativeDataReadinessAssessments,
  aiInitiativeBudgetPolicies,
  aiInitiativeDecisions,
  aiInitiativeValueMeasurements,
} = schema;

export interface AiInitiativePortfolioItem {
  initiativeId: string;
  initiativeRevision: number;
  title: string;
  description?: string;
  lifecycleState: string;
  riskTier: string;
  autonomyTier: string;
  businessOwnerMemberId: string;
  technicalOwnerMemberId?: string;
  riskOwnerMemberId?: string;
  baselineMetricValue: string | null;
  targetMetricValue: string | null;
  latestOutcomeValue: string | null;
  metricUnit?: string;
  costBudgetStatus: "OK" | "EXCEEDED" | "NO_BUDGET" | "NOT_CONFIGURED";
  adoptionStatus: "HEALTHY" | "LAGGING" | "NO_DATA";
  qualityStatus: "PASSED" | "FAILED" | "PENDING_EVAL" | "NO_EVAL";
  dataReadinessStatus: string;
  nextRequiredGate: string;
  blockingReasons: string[];
  authorizedActions: string[];
  latestDecisionId?: string;
}

export interface AiInitiativePortfolioResponse {
  projectId: string;
  workspaceId: string;
  items: AiInitiativePortfolioItem[];
  totalCount: number;
}

export async function getAiInitiativePortfolio(
  ctx: TenantContext,
  projectId: string
): Promise<AiInitiativePortfolioResponse> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  // Scoped query: Only initiatives for this workspace + project
  const initiativeRows = await db
    .select()
    .from(initiatives)
    .where(
      and(
        eq(initiatives.workspaceId, wsId),
        eq(initiatives.projectId, projId),
        isNull(initiatives.deletedAt),
        eq(initiatives.initiativeKind, "AI")
      )
    )
    .orderBy(desc(initiatives.createdAt));

  if (initiativeRows.length === 0) {
    return {
      projectId,
      workspaceId: ctx.workspaceId,
      items: [],
      totalCount: 0,
    };
  }

  const initIds = initiativeRows.map((r) => r.id);

  // Batch query evidence tables to avoid N+1 queries
  const [
    valueContracts,
    dataAssessments,
    budgetPolicies,
    decisions,
    measurements,
  ] = await Promise.all([
    db
      .select()
      .from(aiInitiativeValueContracts)
      .where(
        and(
          eq(aiInitiativeValueContracts.workspaceId, wsId),
          eq(aiInitiativeValueContracts.projectId, projId),
          inArray(aiInitiativeValueContracts.initiativeId, initIds)
        )
      )
      .orderBy(desc(aiInitiativeValueContracts.revision)),
    db
      .select()
      .from(aiInitiativeDataReadinessAssessments)
      .where(
        and(
          eq(aiInitiativeDataReadinessAssessments.workspaceId, wsId),
          eq(aiInitiativeDataReadinessAssessments.projectId, projId),
          inArray(aiInitiativeDataReadinessAssessments.initiativeId, initIds)
        )
      )
      .orderBy(desc(aiInitiativeDataReadinessAssessments.revision)),
    db
      .select()
      .from(aiInitiativeBudgetPolicies)
      .where(
        and(
          eq(aiInitiativeBudgetPolicies.workspaceId, wsId),
          eq(aiInitiativeBudgetPolicies.projectId, projId),
          inArray(aiInitiativeBudgetPolicies.initiativeId, initIds)
        )
      )
      .orderBy(desc(aiInitiativeBudgetPolicies.revision)),
    db
      .select()
      .from(aiInitiativeDecisions)
      .where(
        and(
          eq(aiInitiativeDecisions.workspaceId, wsId),
          eq(aiInitiativeDecisions.projectId, projId),
          inArray(aiInitiativeDecisions.initiativeId, initIds)
        )
      )
      .orderBy(desc(aiInitiativeDecisions.decidedAt)),
    db
      .select()
      .from(aiInitiativeValueMeasurements)
      .where(
        and(
          eq(aiInitiativeValueMeasurements.workspaceId, wsId),
          eq(aiInitiativeValueMeasurements.projectId, projId),
          inArray(aiInitiativeValueMeasurements.initiativeId, initIds)
        )
      )
      .orderBy(desc(aiInitiativeValueMeasurements.observedAt)),
  ]);

  // Group evidence by initiativeId
  const valueContractMap = new Map<string, typeof valueContracts[0]>();
  for (const vc of valueContracts) {
    const key = vc.initiativeId.toString();
    if (!valueContractMap.has(key)) valueContractMap.set(key, vc);
  }

  const dataAssessmentMap = new Map<string, typeof dataAssessments[0]>();
  for (const da of dataAssessments) {
    const key = da.initiativeId.toString();
    if (!dataAssessmentMap.has(key)) dataAssessmentMap.set(key, da);
  }

  const budgetPolicyMap = new Map<string, typeof budgetPolicies[0]>();
  for (const bp of budgetPolicies) {
    const key = bp.initiativeId.toString();
    if (!budgetPolicyMap.has(key)) budgetPolicyMap.set(key, bp);
  }

  const decisionMap = new Map<string, typeof decisions[0]>();
  for (const d of decisions) {
    const key = d.initiativeId.toString();
    if (!decisionMap.has(key)) decisionMap.set(key, d);
  }

  const measurementMap = new Map<string, typeof measurements[0]>();
  for (const m of measurements) {
    const key = m.initiativeId.toString();
    if (!measurementMap.has(key)) measurementMap.set(key, m);
  }

  const items: AiInitiativePortfolioItem[] = initiativeRows.map((r) => {
    const initIdStr = r.id.toString();
    const vc = valueContractMap.get(initIdStr);
    const da = dataAssessmentMap.get(initIdStr);
    const bp = budgetPolicyMap.get(initIdStr);
    const dec = decisionMap.get(initIdStr);
    const vm = measurementMap.get(initIdStr);

    const baselineVal = vc?.baselineValue != null ? String(vc.baselineValue).replace(/\.?0+$/, "") : null;
    const targetVal = vc?.targetValue != null ? String(vc.targetValue).replace(/\.?0+$/, "") : null;
    const outcomeVal = vm?.observedValue != null ? String(vm.observedValue).replace(/\.?0+$/, "") : null;

    let nextGate = "VALIDATION_BASELINE_AND_METRICS";
    const blockingReasons: string[] = [];
    const authorizedActions: string[] = [];

    switch (r.lifecycleState) {
      case "DISCOVER":
        nextGate = "PILOT_PROMOTION_APPROVAL";
        if (r.approvalStatus !== "APPROVED") {
          blockingReasons.push("Approval status is not APPROVED");
        } else {
          authorizedActions.push("promote_to_pilot");
        }
        break;
      case "PILOT":
        nextGate = "VALIDATION_BASELINE_AND_METRICS";
        if (baselineVal == null) {
          blockingReasons.push("Missing baseline metric");
        } else {
          authorizedActions.push("promote_to_validate");
        }
        break;
      case "VALIDATE":
        nextGate = "SCALE_EVALUATION_AND_BUDGET";
        if (!bp) {
          blockingReasons.push("Missing budget policy");
        }
        if (!da) {
          blockingReasons.push("Missing data readiness assessment");
        }
        if (baselineVal != null && bp && da) {
          authorizedActions.push("promote_to_scale_candidate");
        }
        break;
      case "SCALE_CANDIDATE":
        nextGate = "SCALED_HUMAN_ESCALATION";
        if (baselineVal != null && bp && da) {
          authorizedActions.push("scale_initiative");
        } else {
          blockingReasons.push("Prerequisites incomplete for scale");
        }
        break;
      case "SCALED":
        nextGate = "CONTINUOUS_MONITORING";
        authorizedActions.push("review_initiative");
        break;
    }

    return {
      initiativeId: initIdStr,
      initiativeRevision: r.revision,
      title: r.title,
      description: r.description ?? undefined,
      lifecycleState: r.lifecycleState,
      riskTier: r.riskTier,
      autonomyTier: r.autonomyTier,
      businessOwnerMemberId: (r.ownerMemberId ?? "").toString(),
      technicalOwnerMemberId: r.technicalOwnerMemberId ? r.technicalOwnerMemberId.toString() : undefined,
      riskOwnerMemberId: r.riskOwnerMemberId ? r.riskOwnerMemberId.toString() : undefined,
      baselineMetricValue: baselineVal,
      targetMetricValue: targetVal,
      latestOutcomeValue: outcomeVal,
      metricUnit: vc?.unit ?? undefined,
      costBudgetStatus: bp ? "OK" : "NOT_CONFIGURED",
      adoptionStatus: vm ? "HEALTHY" : "NO_DATA",
      qualityStatus: "PASSED",
      dataReadinessStatus: da?.assessmentStatus ?? "NO_ASSESSMENT",
      nextRequiredGate: nextGate,
      blockingReasons,
      authorizedActions,
      latestDecisionId: dec?.id.toString(),
    };
  });

  return {
    projectId,
    workspaceId: ctx.workspaceId,
    items,
    totalCount: items.length,
  };
}
