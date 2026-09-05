import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { financialSnapshots, bankTransactions } = schema;

export interface FinancialSnapshotView {
  id: string;
  workspaceId: string;
  legalEntityId: string | null;
  snapshotDate: string;
  currency: string;
  cashIn: string;
  cashOut: string;
  netBurn: string;
  runwayMonths: string | null;
  openingBalance: string;
  currentCash: string | null;
  monthlyNetBurn: string | null;
  burnWindowMonths: number;
  cashFlowPositive: boolean;
  createdAt: string;
}

type SnapshotRow = typeof financialSnapshots.$inferSelect;

function toView(r: SnapshotRow): FinancialSnapshotView {
  return {
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    legalEntityId: r.legalEntityId ? String(r.legalEntityId) : null,
    snapshotDate:
      typeof r.snapshotDate === "string"
        ? r.snapshotDate
        : new Date(r.snapshotDate).toISOString().split("T")[0],
    currency: r.currency || "VND",
    cashIn: String(r.cashIn),
    cashOut: String(r.cashOut),
    netBurn: String(r.netBurn),
    runwayMonths: r.runwayMonths != null ? String(r.runwayMonths) : null,
    openingBalance: String(r.openingBalance),
    currentCash: r.currentCash != null ? String(r.currentCash) : null,
    monthlyNetBurn: r.monthlyNetBurn != null ? String(r.monthlyNetBurn) : null,
    burnWindowMonths: r.burnWindowMonths,
    cashFlowPositive: r.cashFlowPositive,
    createdAt: r.createdAt.toISOString(),
  };
}

export async function getFinancialSnapshotsService(
  workspaceId: bigint
): Promise<FinancialSnapshotView[]> {
  const rows = await db
    .select()
    .from(financialSnapshots)
    .where(eq(financialSnapshots.workspaceId, workspaceId))
    .orderBy(desc(financialSnapshots.snapshotDate));

  return rows.map(toView);
}

export interface CalculateSnapshotParams {
  workspaceId: bigint;
  legalEntityId?: bigint | string;
  currency?: string; // Mặc định "VND"
  snapshotDate: string; // YYYY-MM-DD
  openingBalance?: string; // số dư đầu kỳ trước mọi transaction đã biết (mặc định 0)
  burnWindowMonths?: number; // cửa sổ tính burn trailing (mặc định 3)
}

export interface SnapshotCalcResult {
  cashInLifetime: number; // Σ IN toàn lịch sử tới snapshotDate
  cashOutLifetime: number;
  currentCash: number; // openingBalance + cashInLifetime - cashOutLifetime
  periodNetBurn: number; // burn trong cửa sổ trailing (OUT - IN, loại trừ transfer/capital/loan)
  monthlyNetBurn: number; // periodNetBurn / burnWindowMonths
  cashFlowPositive: boolean; // monthlyNetBurn <= 0
  runwayMonths: number | null; // null khi cashFlowPositive; BỎ hard-code 99
  currency: string;
}

const NON_OPERATING_CATEGORIES = new Set([
  "TRANSFER",
  "INTERNAL_TRANSFER",
  "CAPITAL",
  "CAPITAL_CONTRIBUTION",
  "LOAN",
  "FINANCING",
  "EQUITY",
]);

/**
 * M7 §8 & F09 — tính cash/burn/runway ĐÚNG:
 *  - currentCash = opening balance + Σ transactions (signed) cùng currency tới snapshotDate.
 *  - monthlyNetBurn = burn trong cửa sổ trailing N tháng (chỉ tính operating flow, loại trừ transfer/capital/loan).
 *  - runway = currentCash / monthlyNetBurn khi monthlyNetBurn > 0; cash-flow dương ⇒ runway = null.
 */
export function computeSnapshot(
  txns: Array<{
    amount: string | number;
    direction: string;
    postedAt: Date | string;
    currency?: string;
    category?: string | null;
  }>,
  opts: {
    snapshotDate: string;
    openingBalance?: number;
    burnWindowMonths?: number;
    currency?: string;
  }
): SnapshotCalcResult {
  const windowMonths = opts.burnWindowMonths ?? 3;
  const targetCurrency = (opts.currency || "VND").toUpperCase();
  const snapEnd = new Date(`${opts.snapshotDate}T23:59:59.999Z`);
  const windowStart = new Date(snapEnd);
  windowStart.setUTCMonth(windowStart.getUTCMonth() - windowMonths);

  let cashInLifetime = 0;
  let cashOutLifetime = 0;
  let periodIn = 0;
  let periodOut = 0;

  for (const t of txns) {
    const txnCurrency = (t.currency || "VND").toUpperCase();
    if (txnCurrency !== targetCurrency) {
      // F09: Không cộng các currency khác nhau nếu không cùng loại tiền
      continue;
    }

    const amt = Math.abs(parseFloat(String(t.amount)) || 0);
    const posted = t.postedAt instanceof Date ? t.postedAt : new Date(t.postedAt);
    if (posted.getTime() > snapEnd.getTime()) continue;

    const isIn = t.direction === "IN";
    if (isIn) cashInLifetime += amt;
    else cashOutLifetime += amt;

    const categoryUpper = (t.category || "").toUpperCase();
    const isOperating = !NON_OPERATING_CATEGORIES.has(categoryUpper);

    if (posted.getTime() >= windowStart.getTime() && isOperating) {
      // Chỉ operating cash flow mới tính vào net burn
      if (isIn) periodIn += amt;
      else periodOut += amt;
    }
  }

  const openingBalance = opts.openingBalance ?? 0;
  const currentCash = openingBalance + cashInLifetime - cashOutLifetime;
  const periodNetBurn = periodOut - periodIn;
  const monthlyNetBurn = periodNetBurn / windowMonths;
  const cashFlowPositive = monthlyNetBurn <= 0;

  let runwayMonths: number | null = null;
  if (!cashFlowPositive) {
    runwayMonths = currentCash > 0
      ? parseFloat((currentCash / monthlyNetBurn).toFixed(2))
      : 0;
  }

  return {
    cashInLifetime,
    cashOutLifetime,
    currentCash,
    periodNetBurn,
    monthlyNetBurn,
    cashFlowPositive,
    runwayMonths,
    currency: targetCurrency,
  };
}

export async function calculateAndSaveSnapshotService(
  p: CalculateSnapshotParams
): Promise<FinancialSnapshotView> {
  const targetCurrency = (p.currency || "VND").toUpperCase();
  const legalEntityId = p.legalEntityId ? BigInt(p.legalEntityId) : null;

  const conditions = [
    eq(bankTransactions.workspaceId, p.workspaceId),
    eq(bankTransactions.currency, targetCurrency),
  ];

  const txns = await db
    .select()
    .from(bankTransactions)
    .where(and(...conditions));

  const windowMonths = p.burnWindowMonths ?? 3;
  const openingBalance = parseFloat(p.openingBalance ?? "0") || 0;
  const c = computeSnapshot(txns, {
    snapshotDate: p.snapshotDate,
    openingBalance,
    burnWindowMonths: windowMonths,
    currency: targetCurrency,
  });

  const values = {
    cashIn: String(c.cashInLifetime),
    cashOut: String(c.cashOutLifetime),
    netBurn: String(c.periodNetBurn),
    runwayMonths: c.runwayMonths != null ? String(c.runwayMonths) : null,
    openingBalance: String(openingBalance),
    currentCash: String(c.currentCash),
    monthlyNetBurn: String(c.monthlyNetBurn),
    burnWindowMonths: windowMonths,
    cashFlowPositive: c.cashFlowPositive,
    currency: targetCurrency,
    legalEntityId,
  } as const;

  const existingConditions = [
    eq(financialSnapshots.workspaceId, p.workspaceId),
    eq(financialSnapshots.snapshotDate, p.snapshotDate as unknown as string),
    eq(financialSnapshots.currency, targetCurrency),
  ];
  if (legalEntityId) {
    existingConditions.push(eq(financialSnapshots.legalEntityId, legalEntityId));
  }

  const [existing] = await db
    .select()
    .from(financialSnapshots)
    .where(and(...existingConditions));

  if (existing) {
    const [updated] = await db
      .update(financialSnapshots)
      .set(values as never)
      .where(eq(financialSnapshots.id, existing.id))
      .returning();
    return toView(updated);
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(financialSnapshots)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      snapshotDate: p.snapshotDate as unknown as string,
      ...values,
    } as never)
    .returning();

  return toView(created);
}
