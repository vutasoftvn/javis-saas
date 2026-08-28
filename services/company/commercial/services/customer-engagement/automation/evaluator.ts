import { and, eq, or, isNull, gt, lte, asc, desc } from "drizzle-orm";
import { db } from "../../../db";
import { engagementAutomationRules } from "../../../../shared/db/schema/customer-engagement";
import type { TenantContext } from "../../../../shared/types/tenant_context";
import { AutomationFacts, buildAutomationFacts } from "./facts";
import { Predicate, evaluatePredicate } from "./predicate";
import { AutomationAction, applyAction, ApplicationOutcome } from "./actions";

export interface EvaluateRulesInput {
  trigger: string;
  threadId: string;
  dryRun?: boolean;
}

export interface EvaluateRulesResult {
  facts: AutomationFacts;
  matched: Array<{
    ruleKey: string;
    version: number;
    actions: AutomationAction[];
  }>;
  applied: Array<{
    ruleKey: string;
    version: number;
    actionIndex: number;
    outcome: ApplicationOutcome;
  }>;
}

export async function evaluateRules(
  input: EvaluateRulesInput,
  ctx: TenantContext
): Promise<EvaluateRulesResult> {
  const wsId = BigInt(ctx.workspaceId);
  const now = new Date();

  // 1. Load active rules for workspace and trigger, ordered by priority ASC, version DESC
  const ruleRows = await db
    .select()
    .from(engagementAutomationRules)
    .where(
      and(
        eq(engagementAutomationRules.workspaceId, wsId),
        eq(engagementAutomationRules.trigger, input.trigger),
        eq(engagementAutomationRules.enabled, true),
        lte(engagementAutomationRules.effectiveFrom, now),
        or(
          isNull(engagementAutomationRules.effectiveUntil),
          gt(engagementAutomationRules.effectiveUntil, now)
        )
      )
    )
    .orderBy(asc(engagementAutomationRules.priority), desc(engagementAutomationRules.version));

  // De-duplicate rules by ruleKey (latest version wins)
  const seenRuleKeys = new Set<string>();
  const activeRules: any[] = [];
  for (const r of ruleRows) {
    if (!seenRuleKeys.has(r.ruleKey)) {
      seenRuleKeys.add(r.ruleKey);
      activeRules.push(r);
    }
  }

  // 2. Build facts once
  const facts = await buildAutomationFacts(input.threadId, ctx);

  const matched: EvaluateRulesResult["matched"] = [];
  const applied: EvaluateRulesResult["applied"] = [];

  // 3. Evaluate rules sequentially
  for (const rule of activeRules) {
    const condition = rule.condition as Predicate;
    const isMatch = evaluatePredicate(condition, facts);

    if (isMatch) {
      const actions = rule.actions as AutomationAction[];
      matched.push({
        ruleKey: rule.ruleKey,
        version: rule.version,
        actions,
      });

      if (!input.dryRun) {
        for (let i = 0; i < actions.length; i++) {
          const action = actions[i];
          const applyRes = await applyAction(
            action,
            {
              threadId: input.threadId,
              ruleKey: rule.ruleKey,
              ruleVersion: rule.version,
              trigger: input.trigger,
              actionIndex: i,
              ruleCondition: condition,
            },
            ctx
          );

          applied.push({
            ruleKey: rule.ruleKey,
            version: rule.version,
            actionIndex: i,
            outcome: applyRes.outcome,
          });
        }
      }

      if (rule.stopOnMatch) {
        break;
      }
    }
  }

  return { facts, matched, applied };
}
