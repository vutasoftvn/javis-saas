import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireFounderCommand } from "../../shared/auth/workspace-access";

const { accountingPolicies } = schema;

export interface AccountingPolicyView {
  legalEntityId: string;
  inventoryValuationMethod: string;
  depreciationMethod: string;
  revenueRecognitionMethod: string;
  corporateIncomeTaxRateBps: number | null;
  confirmedByMemberId: string | null;
  confirmedAt: string | null;
}

function toView(row: typeof accountingPolicies.$inferSelect): AccountingPolicyView {
  return {
    legalEntityId: String(row.legalEntityId),
    inventoryValuationMethod: row.inventoryValuationMethod,
    depreciationMethod: row.depreciationMethod,
    revenueRecognitionMethod: row.revenueRecognitionMethod,
    corporateIncomeTaxRateBps: row.corporateIncomeTaxRateBps,
    confirmedByMemberId: row.confirmedByMemberId ? String(row.confirmedByMemberId) : null,
    confirmedAt: row.confirmedAt ? row.confirmedAt.toISOString() : null,
  };
}

export async function getAccountingPolicyService(
  ctx: TenantContext,
  legalEntityId: string
): Promise<AccountingPolicyView | null> {
  const [row] = await db
    .select()
    .from(accountingPolicies)
    .where(
      and(
        eq(accountingPolicies.workspaceId, BigInt(ctx.workspaceId)),
        eq(accountingPolicies.legalEntityId, BigInt(legalEntityId))
      )
    )
    .limit(1);

  return row ? toView(row) : null;
}

export interface SetAccountingPolicyInput {
  legalEntityId: string;
  inventoryValuationMethod?: string;
  depreciationMethod?: string;
  revenueRecognitionMethod?: string;
  corporateIncomeTaxRateBps?: number;
}

export async function setAccountingPolicyService(
  ctx: TenantContext,
  input: SetAccountingPolicyInput
): Promise<AccountingPolicyView> {
  requireFounderCommand(ctx, "finance.accounting_policy.set");

  if (
    input.corporateIncomeTaxRateBps !== undefined &&
    (input.corporateIncomeTaxRateBps < 0 || input.corporateIncomeTaxRateBps > 10000)
  ) {
    throw APIError.invalidArgument("corporateIncomeTaxRateBps must be between 0 and 10000");
  }

  const now = new Date();
  const values = {
    id: generateSnowflake(),
    workspaceId: BigInt(ctx.workspaceId),
    legalEntityId: BigInt(input.legalEntityId),
    ...(input.inventoryValuationMethod !== undefined && { inventoryValuationMethod: input.inventoryValuationMethod }),
    ...(input.depreciationMethod !== undefined && { depreciationMethod: input.depreciationMethod }),
    ...(input.revenueRecognitionMethod !== undefined && { revenueRecognitionMethod: input.revenueRecognitionMethod }),
    ...(input.corporateIncomeTaxRateBps !== undefined && { corporateIncomeTaxRateBps: input.corporateIncomeTaxRateBps }),
    // CRITICAL: workforceMemberId và userId là 2 spine thực thể khác nhau
    // (ADR-ID-MODEL-001) — không fallback sang ctx.userId khi workforceMemberId
    // vắng mặt (session chưa có workforce member), giữ cột nullable đúng nghĩa.
    confirmedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
    confirmedAt: now,
  };

  const [row] = await db
    .insert(accountingPolicies)
    .values(values)
    .onConflictDoUpdate({
      target: [accountingPolicies.workspaceId, accountingPolicies.legalEntityId],
      set: {
        ...(input.inventoryValuationMethod !== undefined && { inventoryValuationMethod: input.inventoryValuationMethod }),
        ...(input.depreciationMethod !== undefined && { depreciationMethod: input.depreciationMethod }),
        ...(input.revenueRecognitionMethod !== undefined && { revenueRecognitionMethod: input.revenueRecognitionMethod }),
        ...(input.corporateIncomeTaxRateBps !== undefined && { corporateIncomeTaxRateBps: input.corporateIncomeTaxRateBps }),
        confirmedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        confirmedAt: now,
        updatedAt: now,
      },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to set accounting policy");
  return toView(row);
}
