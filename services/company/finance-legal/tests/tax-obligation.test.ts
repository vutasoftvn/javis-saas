import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { openAccountingPeriodService } from "../services/accounting-period.service";
import { setAccountingPolicyService } from "../services/accounting-policy.service";
import { createBookEntryService } from "../services/accounting-books.service";
import {
  getTaxObligationsService,
  upsertManualTaxObligationService,
} from "../services/tax-obligation.service";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
  const period = await openAccountingPeriodService(
    { workspaceId: session.workspaceId, legalEntityId: entity.id, startDate: "2026-01-01", endDate: "2026-12-31" },
    authorization
  );
  return { session, ctx, legalEntityId: entity.id, periodId: period.id };
}

describe("tax-obligation.service", () => {
  it("rejects a manual upsert using the reserved computed-CIT tax name", async () => {
    const { ctx, legalEntityId, periodId } = await foundersSetup("Tax Reserved Name Ws");
    await expect(
      upsertManualTaxObligationService(ctx, { legalEntityId, periodId, taxName: "Thuế TNDN", incurredMinor: "1000" })
    ).rejects.toThrow(/reserved/);
  });

  it("syncs the computed CIT row from B02 and combines it with a manual VAT entry", async () => {
    const { ctx, legalEntityId, periodId } = await foundersSetup("Tax Sync Ws");
    await setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: 2000 });
    await createBookEntryService(ctx, {
      legalEntityId, periodId, item: "Doanh thu", category: "revenue",
      amountMinor: "10000000", effectiveDate: "2026-03-01", source: "test",
    });
    await createBookEntryService(ctx, {
      legalEntityId, periodId, item: "Chi phí HĐ", category: "opex",
      amountMinor: "2000000", effectiveDate: "2026-03-02", source: "test",
    });

    await upsertManualTaxObligationService(ctx, {
      legalEntityId, periodId, taxName: "Thuế GTGT", incurredMinor: "500000", paidMinor: "500000",
    });

    const summary = await getTaxObligationsService(ctx, legalEntityId, periodId);
    const cit = summary.taxes.find((t) => t.taxName === "Thuế TNDN");
    // gross_profit = 10,000,000 (revenue - cogs=0); preTax = 10,000,000 - 2,000,000 = 8,000,000
    // tax = 8,000,000 * 2000/10000 = 1,600,000
    expect(cit?.incurredMinor).toBe("1600000");
    expect(cit?.source).toBe("COMPUTED_CIT");

    const vat = summary.taxes.find((t) => t.taxName === "Thuế GTGT");
    expect(vat?.closingDebtMinor).toBe("0");

    expect(summary.totalBalanceDueMinor).toBe("1600000"); // CIT chưa nộp + VAT đã nộp hết
  });
});
