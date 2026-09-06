import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assertOpenPostingPeriod } from "./posting-guard.service";
import { BookEntryCategory } from "./accounting-mapping";

const { accountingBookEntries } = schema;

export interface BookEntryView {
  id: string;
  workspaceId: string;
  legalEntityId: string;
  periodId: string;
  documentId: string | null;
  item: string;
  category: BookEntryCategory;
  amountMinor: string;
  currency: string;
  effectiveDate: string;
  source: string;
  version: number;
}

export interface CreateBookEntryInput {
  legalEntityId: string;
  periodId: string;
  documentId?: string;
  item: string;
  category: BookEntryCategory;
  amountMinor: string;
  currency?: string;
  effectiveDate: string;
  source: string;
}

function toBookEntryView(row: typeof accountingBookEntries.$inferSelect): BookEntryView {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    legalEntityId: String(row.legalEntityId),
    periodId: String(row.periodId),
    documentId: row.documentId ? String(row.documentId) : null,
    item: row.item,
    category: row.category as BookEntryCategory,
    amountMinor: row.amountMinor,
    currency: row.currency,
    effectiveDate: String(row.effectiveDate),
    source: row.source,
    version: row.version,
  };
}

export async function createBookEntryService(
  ctx: TenantContext,
  input: CreateBookEntryInput
): Promise<BookEntryView> {
  const amount = BigInt(input.amountMinor);
  if (amount <= 0n) {
    throw APIError.invalidArgument("amountMinor must be positive");
  }

  return db.transaction(async (tx) => {
    await assertOpenPostingPeriod(tx, {
      workspaceId: ctx.workspaceId,
      legalEntityId: input.legalEntityId,
      postingDate: input.effectiveDate,
    });

    const [row] = await tx
      .insert(accountingBookEntries)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(ctx.workspaceId),
        legalEntityId: BigInt(input.legalEntityId),
        periodId: BigInt(input.periodId),
        documentId: input.documentId ? BigInt(input.documentId) : null,
        item: input.item,
        category: input.category,
        amountMinor: input.amountMinor,
        currency: input.currency ?? "VND",
        effectiveDate: input.effectiveDate,
        source: input.source,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create book entry");
    return toBookEntryView(row);
  });
}

export interface ListBookEntriesParams {
  legalEntityId: string;
  periodId: string;
}

export async function listBookEntriesService(
  ctx: TenantContext,
  params: ListBookEntriesParams
): Promise<BookEntryView[]> {
  const rows = await db
    .select()
    .from(accountingBookEntries)
    .where(
      and(
        eq(accountingBookEntries.workspaceId, BigInt(ctx.workspaceId)),
        eq(accountingBookEntries.legalEntityId, BigInt(params.legalEntityId)),
        eq(accountingBookEntries.periodId, BigInt(params.periodId))
      )
    );

  return rows.map(toBookEntryView);
}
