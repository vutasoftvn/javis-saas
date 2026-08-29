import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { financialSnapshots, bankTransactions } = schema;

export interface FinancialSnapshotView {
  id: string;
  workspaceId: string;
  snapshotDate: string;
  cashIn: string;
  cashOut: string;
  netBurn: string;
  runwayMonths: string | null;
  // M7 §8
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
    snapshotDate:
      typeof r.snapshotDate === "string"
        ? r.snapshotDate
        : new Date(r.snapshotDate).toISOString().split("T")[0],
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
  snapshotDate: string; // YYYY-MM-DD
  openingBalance?: string; // số dư đầu kỳ trước mọi transaction đã biết (mặc định 0)
  burnWindowMonths?: number; // cửa sổ tính burn trailing (mặc định 3)
}

export interface SnapshotCalcResult {
  cashInLifetime: number; // Σ IN toàn lịch sử tới snapshotDate
  cashOutLifetime: number;
  currentCash: number; // openingBalance + cashInLifetime - cashOutLifetime
  periodNetBurn: number; // burn trong cửa sổ trailing (OUT - IN)
  monthlyNetBurn: number; // periodNetBurn / burnWindowMonths
  cashFlowPositive: boolean; // monthlyNetBurn <= 0
  runwayMonths: number | null; // null khi cashFlowPositive; BỎ hard-code 99
}

/**
 * M7 §8 — tính cash/burn/runway ĐÚNG:
 *  - currentCash = opening balance + Σ transactions (signed) tới snapshotDate.
 *  - monthlyNetBurn = burn trong cửa sổ trailing N tháng (không tổng lịch sử).
 *  - runway = currentCash / monthlyNetBurn khi monthlyNetBurn > 0; cash-flow dương
 *    ⇒ runway = null (KHÔNG 99).
 * Hàm thuần để test không cần DB.
 */
export function computeSnapshot(
  txns: Array<{ amount: string | number; direction: string; postedAt: Date | string }>,
  opts: { snapshotDate: string; openingBalance?: number; burnWindowMonths?: number }
): SnapshotCalcResult {
  const windowMonths = opts.burnWindowMonths ?? 3;
  const snapEnd = new Date(`${opts.snapshotDate}T23:59:59.999Z`);
  const windowStart = new Date(snapEnd);
  windowStart.setUTCMonth(windowStart.getUTCMonth() - windowMonths);

  let cashInLifetime = 0;
  let cashOutLifetime = 0;
  let periodIn = 0;
  let periodOut = 0;

  for (const t of txns) {
    const amt = Math.abs(parseFloat(String(t.amount)) || 0);
    const posted = t.postedAt instanceof Date ? t.postedAt : new Date(t.postedAt);
    if (posted.getTime() > snapEnd.getTime()) continue;
    const isIn = t.direction === "IN";
    if (isIn) cashInLifetime += amt;
    else cashOutLifetime += amt;
    if (posted.getTime() >= windowStart.getTime()) {
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
  };
}

export async function calculateAndSaveSnapshotService(
  p: CalculateSnapshotParams
): Promise<FinancialSnapshotView> {
  const txns = await db
    .select()
    .from(bankTransactions)
    .where(eq(bankTransactions.workspaceId, p.workspaceId));

  const windowMonths = p.burnWindowMonths ?? 3;
  const openingBalance = parseFloat(p.openingBalance ?? "0") || 0;
  const c = computeSnapshot(txns, {
    snapshotDate: p.snapshotDate,
    openingBalance,
    burnWindowMonths: windowMonths,
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
  } as const;

  const [existing] = await db
    .select()
    .from(financialSnapshots)
    .where(
      and(
        eq(financialSnapshots.workspaceId, p.workspaceId),
        eq(financialSnapshots.snapshotDate, p.snapshotDate as unknown as string)
      )
    );

  if (existing) {
    const [updated] = await db
      .update(financialSnapshots)
      .set(values as never)
      .where(eq(financialSnapshots.id, existing.id))
      .returning();
    return toView(updated);
  }

  const [created] = await db
    .insert(financialSnapshots)
    .values({
      id: generateSnowflake(),
      workspaceId: p.workspaceId,
      snapshotDate: p.snapshotDate as unknown as string,
      ...values,
    } as never)
    .returning();
  return toView(created);
}
