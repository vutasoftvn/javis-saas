import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assertOpenPostingPeriod, normalizeDate } from "./posting-guard.service";
import { BookEntryCategory } from "./accounting-mapping";

const { accountingBookEntries, accountingPeriods } = schema;

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

    // `assertOpenPostingPeriod` tìm kỳ bao phủ theo KHOẢNG NGÀY và không hề
    // nhìn tới `input.periodId` do caller gửi lên. Nếu chỉ dựa vào guard đó,
    // caller có thể gửi effectiveDate rơi vào một kỳ ĐANG MỞ (qua được guard)
    // kèm periodId trỏ tới một kỳ ĐÃ ĐÓNG, kỳ của pháp nhân khác hoặc kỳ của
    // workspace khác — bút toán lặng lẽ nằm dưới sai kỳ và làm sai sổ/báo cáo
    // của kỳ đó về sau. Vì vậy kiểm tra tường minh: periodId phải đúng là một
    // kỳ OPEN, thuộc workspace + pháp nhân này, và bao phủ chính effectiveDate.
    const dateStr = normalizeDate(input.effectiveDate);
    const [declaredPeriod] = await tx
      .select({
        id: accountingPeriods.id,
        legalEntityId: accountingPeriods.legalEntityId,
        status: accountingPeriods.status,
        startDate: accountingPeriods.startDate,
        endDate: accountingPeriods.endDate,
      })
      .from(accountingPeriods)
      .where(
        and(
          eq(accountingPeriods.id, BigInt(input.periodId)),
          eq(accountingPeriods.workspaceId, BigInt(ctx.workspaceId))
        )
      )
      .limit(1);

    if (!declaredPeriod) {
      throw APIError.failedPrecondition(
        `PERIOD_CLOSED: Kỳ kế toán ${input.periodId} không tồn tại trong workspace này`
      );
    }

    if (
      declaredPeriod.legalEntityId !== null &&
      declaredPeriod.legalEntityId !== BigInt(input.legalEntityId)
    ) {
      throw APIError.failedPrecondition(
        `PERIOD_CLOSED: Kỳ kế toán ${input.periodId} thuộc pháp nhân khác, không ghi sổ chéo pháp nhân`
      );
    }

    if (declaredPeriod.status !== "OPEN") {
      throw APIError.failedPrecondition(
        `PERIOD_CLOSED: Không thể ghi sổ vào kỳ kế toán ${input.periodId} (status ${declaredPeriod.status})`
      );
    }

    const periodStart = normalizeDate(declaredPeriod.startDate);
    const periodEnd = normalizeDate(declaredPeriod.endDate);
    if (dateStr < periodStart || dateStr > periodEnd) {
      throw APIError.failedPrecondition(
        `PERIOD_CLOSED: Ngày ghi sổ ${dateStr} nằm ngoài kỳ kế toán ${input.periodId} ` +
          `(${periodStart} → ${periodEnd})`
      );
    }

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
