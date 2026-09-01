import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { isJsonObject, JsonValue, toJsonArray } from "./strategy-json";

const { gateEvaluations, stagePolicies, evidence } = schema;

export interface StagePolicyRule {
  key: string;
  description?: string;
  minCount?: number;
  minStrength?: number;
  sourceType?: string;
}

export interface StagePolicyData {
  id?: number | bigint | string;
  stageKey: string;
  minimumEvidenceScore: number;
  requirements: StagePolicyRule[];
  blockingRiskRules?: JsonValue[];
  invalidRequirementCount?: number;
}

export interface EvidenceItem {
  id?: number | bigint | string;
  sourceType: string;
  strength: number;
  confidence: number;
  supportsOrRefutes: "supports" | "refutes" | "neutral" | string;
}

export interface BlockingRiskItem {
  riskKey: string;
  severity: "high" | "critical" | "medium" | "low" | string;
  resolved: boolean;
  notes?: string;
}

export interface GateEvaluationInput {
  policy: StagePolicyData;
  evidenceList: EvidenceItem[];
  blockingRisks?: BlockingRiskItem[];
  humanOverride?: boolean;
}

export interface GateEvaluationOutput {
  requirementsMet: boolean;
  evidenceScore: number;
  blockingRisks: BlockingRiskItem[];
  result: "passed" | "failed" | "conditional";
  rationale: string;
  humanOverride: boolean;
}

export interface GateEvaluation {
  id: string;
  workspaceId: string;
  projectId: string;
  stagePolicyId: string | null;
  requirementsMet: boolean;
  evidenceScore: number;
  blockingRisks: BlockingRiskItem[];
  result: string;
  rationale: string;
  humanOverride: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RunGateEvaluationInput {
  projectId: string | number;
  stagePolicyId: string | number;
  blockingRisks?: BlockingRiskItem[];
}

export interface ListGateEvaluationsInput {
  projectId?: string | number;
}

function isStagePolicyRule(value: unknown): value is StagePolicyRule {
  if (!isJsonObject(value) || typeof value.key !== "string") {
    return false;
  }

  return (
    (value.description === undefined || typeof value.description === "string") &&
    (value.minCount === undefined || typeof value.minCount === "number") &&
    (value.minStrength === undefined || typeof value.minStrength === "number") &&
    (value.sourceType === undefined || typeof value.sourceType === "string")
  );
}

export function parseStagePolicyRules(value: unknown): {
  rules: StagePolicyRule[];
  invalidCount: number;
} {
  if (!Array.isArray(value)) {
    return { rules: [], invalidCount: 1 };
  }

  const rules: StagePolicyRule[] = [];
  let invalidCount = 0;
  for (const item of value) {
    if (isStagePolicyRule(item)) {
      rules.push(item);
    } else {
      invalidCount += 1;
    }
  }
  return { rules, invalidCount };
}

export function toStagePolicyRules(value: unknown): StagePolicyRule[] {
  return parseStagePolicyRules(value).rules;
}

function isBlockingRiskItem(value: unknown): value is BlockingRiskItem {
  return (
    isJsonObject(value) &&
    typeof value.riskKey === "string" &&
    typeof value.severity === "string" &&
    typeof value.resolved === "boolean" &&
    (value.notes === undefined || typeof value.notes === "string")
  );
}

function toBlockingRiskItems(value: unknown): BlockingRiskItem[] {
  const risks: BlockingRiskItem[] = [];
  for (const item of toJsonArray(value)) {
    if (isBlockingRiskItem(item)) risks.push(item);
  }
  return risks;
}

export function toGateEvaluation(row: typeof gateEvaluations.$inferSelect): GateEvaluation {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    stagePolicyId: row.stagePolicyId ? row.stagePolicyId.toString() : null,
    requirementsMet: row.requirementsMet,
    evidenceScore: row.evidenceScore,
    blockingRisks: toBlockingRiskItems(row.blockingRisks),
    result: row.result,
    rationale: row.rationale,
    humanOverride: row.humanOverride,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

/**
 * Đánh giá Stage Gate hoàn toàn tất định (100% deterministic), KHÔNG gọi LLM.
 * Các tiêu chí:
 * 1. Average evidence strength của các supporting evidence >= policy.minimumEvidenceScore
 * 2. Từng requirement trong policy.requirements được kiểm tra
 * 3. Không có rủi ro cản trở (blocking risks) chưa được giải quyết ở mức high/critical
 */
export function evaluateGate(input: GateEvaluationInput): GateEvaluationOutput {
  const { policy, evidenceList, blockingRisks = [], humanOverride = false } = input;

  const supporting = evidenceList.filter((e) => e.supportsOrRefutes === "supports");
  const refuting = evidenceList.filter((e) => e.supportsOrRefutes === "refutes");

  // 1. Calculate average evidence score
  let evidenceScore = 0;
  if (supporting.length > 0) {
    const totalScore = supporting.reduce((acc, curr) => acc + (curr.strength * curr.confidence), 0);
    evidenceScore = Math.round((totalScore / supporting.length) * 10000) / 10000;
  }

  // 2. Check blocking risks
  const unresolvedBlockingRisks = blockingRisks.filter(
    (r) => !r.resolved && (r.severity === "high" || r.severity === "critical")
  );

  // 3. Check requirements
  const rawRequirements: StagePolicyRule[] = Array.isArray(policy.requirements) ? policy.requirements : [];
  const failedRequirements: string[] = [];

  if ((policy.invalidRequirementCount ?? 0) > 0) {
    failedRequirements.push(`Stage policy has ${policy.invalidRequirementCount} invalid requirement(s).`);
  }

  for (const req of rawRequirements) {
    if (req.minCount) {
      let count = supporting.length;
      if (req.sourceType) {
        count = supporting.filter((e) => e.sourceType.toLowerCase() === req.sourceType?.toLowerCase()).length;
      }
      if (count < req.minCount) {
        failedRequirements.push(`Requirement '${req.description || req.key}': requires at least ${req.minCount} items, found ${count}.`);
      }
    }
    if (req.minStrength && evidenceScore < req.minStrength) {
      failedRequirements.push(`Requirement '${req.description || req.key}': requires average strength >= ${req.minStrength}, got ${evidenceScore}.`);
    }
  }

  const scoreMet = evidenceScore >= (policy.minimumEvidenceScore || 0);
  if (!scoreMet && (policy.minimumEvidenceScore || 0) > 0) {
    failedRequirements.push(`Overall evidence score ${evidenceScore} is below minimum requirement ${policy.minimumEvidenceScore}.`);
  }

  const hasExcessiveRefutation = refuting.length > supporting.length && refuting.length > 0;
  if (hasExcessiveRefutation) {
    failedRequirements.push(`Refuting evidence (${refuting.length}) exceeds supporting evidence (${supporting.length}).`);
  }

  const requirementsMet = failedRequirements.length === 0 && unresolvedBlockingRisks.length === 0;

  let result: "passed" | "failed" | "conditional" = "failed";
  let rationale = "";

  if (humanOverride) {
    result = "passed";
    rationale = `Gate passed via human override. (Auto-evaluation notes: requirementsMet=${requirementsMet}, evidenceScore=${evidenceScore}).`;
  } else if (requirementsMet) {
    result = "passed";
    rationale = `All gate requirements met for stage ${policy.stageKey}. Evidence score: ${evidenceScore} (min: ${policy.minimumEvidenceScore}). Supporting evidence items: ${supporting.length}.`;
  } else if (unresolvedBlockingRisks.length > 0) {
    result = "failed";
    rationale = `Gate failed due to ${unresolvedBlockingRisks.length} unresolved critical/high blocking risk(s). ${failedRequirements.join(" ")}`.trim();
  } else if (!scoreMet || failedRequirements.length > 0) {
    result = "failed";
    rationale = `Gate failed: ${failedRequirements.join(" ")}`;
  }

  return {
    requirementsMet,
    evidenceScore,
    blockingRisks: unresolvedBlockingRisks,
    result,
    rationale,
    humanOverride,
  };
}

export async function runGateEvaluationInWorkspace(
  ctx: TenantContext,
  params: RunGateEvaluationInput
): Promise<GateEvaluation> {
  if (!params.projectId || !params.stagePolicyId) {
    throw APIError.invalidArgument("projectId and stagePolicyId are required");
  }
  const wsId = BigInt(ctx.workspaceId);

  // Xác nhận project thuộc workspace này
  await getProjectInWorkspace(params.projectId, ctx);

  // 1. Fetch stage policy from workspace
  const [policyRow] = await db
    .select()
    .from(stagePolicies)
    .where(and(eq(stagePolicies.id, BigInt(params.stagePolicyId)), eq(stagePolicies.workspaceId, wsId), isNull(stagePolicies.deletedAt)))
    .limit(1);

  if (!policyRow) throw APIError.notFound("Stage policy not found");

  // 2. Fetch approved project evidence from workspace (candidate evidence is ignored by gates until approved)
  const now = new Date();
  const allApprovedEvidence = await db
    .select()
    .from(evidence)
    .where(and(eq(evidence.projectId, BigInt(params.projectId)), eq(evidence.workspaceId, wsId), eq(evidence.status, "approved"), isNull(evidence.deletedAt)));

  // Filter out stale/expired evidence based on freshUntil
  const freshEvidenceRows = allApprovedEvidence.filter((e) => {
    if (e.freshUntil && new Date(e.freshUntil) < now) {
      return false;
    }
    return true;
  });

  // 3. Evaluate deterministically without LLM - recommendation only
  const parsedRequirements = parseStagePolicyRules(policyRow.requirements);
  const evaluation = evaluateGate({
    policy: {
      id: policyRow.id.toString(),
      stageKey: policyRow.stageKey,
      minimumEvidenceScore: policyRow.minimumEvidenceScore,
      requirements: parsedRequirements.rules,
      blockingRiskRules: toJsonArray(policyRow.blockingRiskRules),
      invalidRequirementCount: parsedRequirements.invalidCount,
    },
    evidenceList: freshEvidenceRows.map((e) => ({
      id: e.id.toString(),
      sourceType: e.sourceType,
      strength: e.strength,
      confidence: e.confidence,
      supportsOrRefutes: e.supportsOrRefutes,
    })),
    blockingRisks: params.blockingRisks,
    humanOverride: false,
  });

  // 4. Save evaluation record (recommendation-only: never alters project stage or writes outbox)
  const [saved] = await db
    .insert(gateEvaluations)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      stagePolicyId: BigInt(params.stagePolicyId),
      requirementsMet: evaluation.requirementsMet,
      evidenceScore: evaluation.evidenceScore,
      blockingRisks: evaluation.blockingRisks,
      result: evaluation.result,
      rationale: evaluation.rationale,
      humanOverride: false,
    })
    .returning();

  if (!saved) throw APIError.internal("failed to save gate evaluation");
  return toGateEvaluation(saved);
}

export async function getGateEvaluationInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<GateEvaluation> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(gateEvaluations)
    .where(and(eq(gateEvaluations.id, BigInt(id)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Gate evaluation not found");
  return toGateEvaluation(row);
}

export async function listGateEvaluationsInWorkspace(
  ctx: TenantContext,
  params: ListGateEvaluationsInput
): Promise<{ items: GateEvaluation[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)];

  if (params.projectId) {
    conditions.push(eq(gateEvaluations.projectId, BigInt(params.projectId)));
  }

  const rows = await db
    .select()
    .from(gateEvaluations)
    .where(and(...conditions));

  return {
    items: rows.map(toGateEvaluation),
  };
}

export async function updateGateEvaluationInWorkspace(
  ctx: TenantContext,
  id: string | number,
  params: { humanOverride?: boolean; rationale?: string }
): Promise<GateEvaluation> {
  if (params.humanOverride !== undefined) {
    throw APIError.invalidArgument("Gate evaluation cannot be overridden directly; use stage transition endpoint with approval");
  }

  const wsId = BigInt(ctx.workspaceId);
  const updateValues = {
    updatedAt: new Date(),
    ...(params.rationale !== undefined ? { rationale: params.rationale } : {}),
  };

  const [row] = await db
    .update(gateEvaluations)
    .set(updateValues)
    .where(and(eq(gateEvaluations.id, BigInt(id)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Gate evaluation not found");
  return toGateEvaluation(row);
}

export async function deleteGateEvaluationInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .update(gateEvaluations)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(gateEvaluations.id, BigInt(id)), eq(gateEvaluations.workspaceId, wsId), isNull(gateEvaluations.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Gate evaluation not found");
  return { success: true };
}
