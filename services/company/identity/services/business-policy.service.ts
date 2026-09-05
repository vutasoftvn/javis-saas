import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db } from "../models/db";
import { coreWorkspacePolicyVersions } from "../../shared/db/schema/identity";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  authorizeBusinessAction,
  ResourceScope,
  RuleDecision,
} from "./business-authorization.service";

export interface EvaluateBusinessPolicyInput {
  ctx: TenantContext;
  action: string;
  resourceRef?: string;
  version?: number;
  runRef?: string;
  scope?: ResourceScope;
  facts?: Record<string, any>;
}

export interface EvaluateBusinessPolicyResult {
  decision: RuleDecision;
  policyVersion: number;
  policyHash: string;
  resourceVersion: number;
  evaluatedAt: string;
  expiresAt: string;
}

export async function evaluateBusinessPolicyService(
  input: EvaluateBusinessPolicyInput
): Promise<EvaluateBusinessPolicyResult> {
  const wsId = BigInt(input.ctx.workspaceId);

  const [latestPolicy] = await db
    .select({
      version: coreWorkspacePolicyVersions.version,
      policyHash: coreWorkspacePolicyVersions.policyHash,
    })
    .from(coreWorkspacePolicyVersions)
    .where(eq(coreWorkspacePolicyVersions.workspaceId, wsId))
    .orderBy(desc(coreWorkspacePolicyVersions.version))
    .limit(1);

  const policyVersion = latestPolicy?.version ?? 1;
  const policyHash = latestPolicy?.policyHash ?? `policy-hash-${wsId}-${policyVersion}`;

  const decision = await authorizeBusinessAction(
    input.ctx,
    input.action,
    input.scope || { workspaceId: input.ctx.workspaceId },
    input.facts
  );

  const now = new Date();
  const expiresAt = new Date(now.getTime() + 5 * 60 * 1000); // 5 minutes cache validity

  return {
    decision,
    policyVersion,
    policyHash,
    resourceVersion: input.version || 1,
    evaluatedAt: now.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };
}
