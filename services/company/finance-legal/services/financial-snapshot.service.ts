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
  createdAt: string;
}

export async function getFinancialSnapshotsService(
  workspaceId: bigint
): Promise<FinancialSnapshotView[]> {
  const rows = await db
    .select()
    .from(financialSnapshots)
    .where(eq(financialSnapshots.workspaceId, workspaceId))
    .orderBy(desc(financialSnapshots.snapshotDate));

  return rows.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    snapshotDate: typeof r.snapshotDate === "string" ? r.snapshotDate : new Date(r.snapshotDate).toISOString().split("T")[0],
    cashIn: String(r.cashIn),
    cashOut: String(r.cashOut),
    netBurn: String(r.netBurn),
    runwayMonths: r.runwayMonths ? String(r.runwayMonths) : null,
    createdAt: r.createdAt.toISOString(),
  }));
}

export async function calculateAndSaveSnapshotService(p: {
  workspaceId: bigint;
  snapshotDate: string;
}): Promise<FinancialSnapshotView> {
  const txns = await db
    .select()
    .from(bankTransactions)
    .where(eq(bankTransactions.workspaceId, p.workspaceId));

  let cashIn = 0;
  let cashOut = 0;
  for (const t of txns) {
    const amt = parseFloat(String(t.amount)) || 0;
    if (t.direction === "IN") {
      cashIn += amt;
    } else {
      cashOut += amt;
    }
  }

  const netBurn = cashOut - cashIn;
  const currentCash = cashIn - cashOut;
  let runwayMonths: number | null = null;
  if (netBurn > 0 && currentCash > 0) {
    runwayMonths = parseFloat((currentCash / netBurn).toFixed(2));
  } else if (netBurn <= 0) {
    runwayMonths = 99.0; // Breakeven or cash flow positive
  } else {
    runwayMonths = 0.0;
  }

  // Idempotent upsert
  const [existing] = await db
    .select()
    .from(financialSnapshots)
    .where(
      and(
        eq(financialSnapshots.workspaceId, p.workspaceId),
        eq(financialSnapshots.snapshotDate, p.snapshotDate as any)
      )
    );

  if (existing) {
    const [updated] = await db
      .update(financialSnapshots)
      .set({
        cashIn: String(cashIn) as any,
        cashOut: String(cashOut) as any,
        netBurn: String(netBurn) as any,
        runwayMonths: runwayMonths !== null ? (String(runwayMonths) as any) : null,
      })
      .where(eq(financialSnapshots.id, existing.id))
      .returning();

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      snapshotDate: typeof updated.snapshotDate === "string" ? updated.snapshotDate : new Date(updated.snapshotDate).toISOString().split("T")[0],
      cashIn: String(updated.cashIn),
      cashOut: String(updated.cashOut),
      netBurn: String(updated.netBurn),
      runwayMonths: updated.runwayMonths ? String(updated.runwayMonths) : null,
      createdAt: updated.createdAt.toISOString(),
    };
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(financialSnapshots)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      snapshotDate: p.snapshotDate as any,
      cashIn: String(cashIn) as any,
      cashOut: String(cashOut) as any,
      netBurn: String(netBurn) as any,
      runwayMonths: runwayMonths !== null ? (String(runwayMonths) as any) : null,
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    snapshotDate: typeof created.snapshotDate === "string" ? created.snapshotDate : new Date(created.snapshotDate).toISOString().split("T")[0],
    cashIn: String(created.cashIn),
    cashOut: String(created.cashOut),
    netBurn: String(created.netBurn),
    runwayMonths: created.runwayMonths ? String(created.runwayMonths) : null,
    createdAt: created.createdAt.toISOString(),
  };
}
