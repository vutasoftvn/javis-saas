import { APIError } from "encore.dev/api";
import { eq, and, desc, lte, or, isNull, gt } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { accountingRegimePolicies, accountingProfiles } = schema;

export interface AccountingRegimePolicyView {
  id: string;
  workspaceId: string;
  regulationVersionId: string;
  mode: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  requiresCoa: boolean;
  requiresDoubleEntry: boolean;
  createdAt: string;
  updatedAt: string;
}

export async function getAccountingRegimePolicyService(
  workspaceId: bigint,
  queryDate?: string
): Promise<AccountingRegimePolicyView | null> {
  const d = queryDate || new Date().toISOString().split("T")[0];

  const rows = await db
    .select()
    .from(accountingRegimePolicies)
    .where(eq(accountingRegimePolicies.workspaceId, workspaceId))
    .orderBy(desc(accountingRegimePolicies.effectiveFrom));

  const matched = rows.find((r) => {
    const effFrom = typeof r.effectiveFrom === "string" ? r.effectiveFrom : new Date(r.effectiveFrom).toISOString().split("T")[0];
    const effTo = r.effectiveTo ? (typeof r.effectiveTo === "string" ? r.effectiveTo : new Date(r.effectiveTo).toISOString().split("T")[0]) : null;
    return effFrom <= d && (effTo === null || effTo > d);
  });

  if (!matched) return null;

  return {
    id: String(matched.id),
    workspaceId: String(matched.workspaceId),
    regulationVersionId: String(matched.regulationVersionId),
    mode: matched.mode,
    effectiveFrom: typeof matched.effectiveFrom === "string" ? matched.effectiveFrom : new Date(matched.effectiveFrom).toISOString().split("T")[0],
    effectiveTo: matched.effectiveTo ? (typeof matched.effectiveTo === "string" ? matched.effectiveTo : new Date(matched.effectiveTo).toISOString().split("T")[0]) : null,
    requiresCoa: matched.requiresCoa,
    requiresDoubleEntry: matched.requiresDoubleEntry,
    createdAt: matched.createdAt.toISOString(),
    updatedAt: matched.updatedAt.toISOString(),
  };
}

export async function setAccountingRegimePolicyService(p: {
  workspaceId: bigint;
  regulationVersionId: bigint;
  mode: string;
  effectiveFrom: string;
  effectiveTo?: string;
  requiresCoa?: boolean;
  requiresDoubleEntry?: boolean;
}): Promise<AccountingRegimePolicyView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(accountingRegimePolicies)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      regulationVersionId: p.regulationVersionId,
      mode: p.mode,
      effectiveFrom: p.effectiveFrom as any,
      effectiveTo: p.effectiveTo ? (p.effectiveTo as any) : null,
      requiresCoa: p.requiresCoa ?? false,
      requiresDoubleEntry: p.requiresDoubleEntry ?? false,
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    regulationVersionId: String(created.regulationVersionId),
    mode: created.mode,
    effectiveFrom: typeof created.effectiveFrom === "string" ? created.effectiveFrom : new Date(created.effectiveFrom).toISOString().split("T")[0],
    effectiveTo: created.effectiveTo ? (typeof created.effectiveTo === "string" ? created.effectiveTo : new Date(created.effectiveTo).toISOString().split("T")[0]) : null,
    requiresCoa: created.requiresCoa,
    requiresDoubleEntry: created.requiresDoubleEntry,
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}
