import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { generateReportService } from "./accounting-reports.service";

const { taxObligationInstances } = schema;

const COMPUTED_CIT_TAX_NAME = "Thuế TNDN";

export interface TaxObligationView {
  id: string;
  taxName: string;
  incurredMinor: string;
  paidMinor: string;
  closingDebtMinor: string;
  source: "MANUAL" | "COMPUTED_CIT";
}

export interface TaxObligationSummaryView {
  taxes: TaxObligationView[];
  totalBalanceDueMinor: string;
}

function toView(row: typeof taxObligationInstances.$inferSelect): TaxObligationView {
  const closing = BigInt(row.incurredMinor) - BigInt(row.paidMinor);
  return {
    id: String(row.id),
    taxName: row.taxName,
    incurredMinor: row.incurredMinor,
    paidMinor: row.paidMinor,
    closingDebtMinor: String(closing),
    source: row.source as "MANUAL" | "COMPUTED_CIT",
  };
}

/**
 * Hành động RIÊNG, tường minh — KHÔNG gọi từ getTaxObligationsService.
 * generateReportService luôn ghi 1 dòng mới vào accounting_report_snapshots,
 * nên việc gọi nó phải là một sự kiện có chủ đích (giống POST
 * /finance/reports/generate đã có), không phải side-effect của một lần đọc —
 * nếu không, mỗi lần tải màn hình F01 sẽ âm thầm phình audit log vô hạn.
 */
export async function syncComputedCorporateIncomeTaxService(
  ctx: TenantContext,
  legalEntityId: string,
  periodId: string
): Promise<TaxObligationView | null> {
  const b02 = await generateReportService(ctx, { legalEntityId, periodId, reportCode: "B02" });
  const citLine = b02.lines.find((l) => l.lineCode === "THUE_TNDN");
  if (!citLine) return null;

  const [row] = await db
    .insert(taxObligationInstances)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: BigInt(legalEntityId),
      periodId: BigInt(periodId),
      taxName: COMPUTED_CIT_TAX_NAME,
      incurredMinor: citLine.amountMinor,
      source: "COMPUTED_CIT",
    })
    .onConflictDoUpdate({
      target: [
        taxObligationInstances.workspaceId,
        taxObligationInstances.legalEntityId,
        taxObligationInstances.periodId,
        taxObligationInstances.taxName,
      ],
      set: { incurredMinor: citLine.amountMinor, updatedAt: new Date() },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to sync computed CIT tax obligation");
  return toView(row);
}

/**
 * ĐỌC THUẦN TÚY — không gọi generateReportService, không ghi gì. Muốn số
 * thuế TNDN mới nhất, caller phải gọi syncComputedCorporateIncomeTaxService
 * riêng trước (xem doc comment ở trên).
 */
export async function getTaxObligationsService(
  ctx: TenantContext,
  legalEntityId: string,
  periodId: string
): Promise<TaxObligationSummaryView> {
  const rows = await db
    .select()
    .from(taxObligationInstances)
    .where(
      and(
        eq(taxObligationInstances.workspaceId, BigInt(ctx.workspaceId)),
        eq(taxObligationInstances.legalEntityId, BigInt(legalEntityId)),
        eq(taxObligationInstances.periodId, BigInt(periodId))
      )
    );

  const taxes = rows.map(toView);
  const totalBalanceDueMinor = taxes.reduce((sum, t) => sum + BigInt(t.closingDebtMinor), 0n);

  return { taxes, totalBalanceDueMinor: String(totalBalanceDueMinor) };
}

export interface UpsertTaxObligationInput {
  legalEntityId: string;
  periodId: string;
  taxName: string;
  incurredMinor?: string;
  paidMinor?: string;
}

export async function upsertManualTaxObligationService(
  ctx: TenantContext,
  input: UpsertTaxObligationInput
): Promise<TaxObligationView> {
  if (input.taxName === COMPUTED_CIT_TAX_NAME) {
    throw APIError.invalidArgument(
      `"${COMPUTED_CIT_TAX_NAME}" is a reserved tax name computed automatically from B02 — use a different taxName`
    );
  }

  const [row] = await db
    .insert(taxObligationInstances)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: BigInt(input.legalEntityId),
      periodId: BigInt(input.periodId),
      taxName: input.taxName,
      incurredMinor: input.incurredMinor ?? "0",
      paidMinor: input.paidMinor ?? "0",
      source: "MANUAL",
    })
    .onConflictDoUpdate({
      target: [
        taxObligationInstances.workspaceId,
        taxObligationInstances.legalEntityId,
        taxObligationInstances.periodId,
        taxObligationInstances.taxName,
      ],
      set: {
        ...(input.incurredMinor !== undefined && { incurredMinor: input.incurredMinor }),
        ...(input.paidMinor !== undefined && { paidMinor: input.paidMinor }),
        updatedAt: new Date(),
      },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to upsert tax obligation");
  return toView(row);
}
