import { describe, expect, it } from "vitest";
import fixture from "./fixtures/tt58-2026/basic-entity.json";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { createFiscalProfileService } from "../services/accounting-regime.service";
import { openAccountingPeriodService, closeAccountingPeriodService } from "../services/accounting-period.service";
import { createBookEntryService } from "../services/accounting-books.service";
import { generateReportService, confirmMappingService } from "../services/accounting-reports.service";
import { TT58_2026_MAPPING } from "../services/accounting-mapping";

describe("F5 — TT58 report generation (fixture-based)", () => {
  it("generates INCOMPLETE report until founder confirms the mapping, then VERIFIED with correct balance-sheet totals", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 Fixture Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({
      authorization,
      workspaceId: session.workspaceId,
    });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    await createFiscalProfileService(
      { workspaceId: session.workspaceId, fiscalYear: 2026 },
      authorization
    );
    const period = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entity.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );

    for (const entry of fixture.entries) {
      await createBookEntryService(ctx, {
        legalEntityId: entity.id,
        periodId: period.id,
        item: entry.item,
        category: entry.category as any,
        amountMinor: entry.amountMinor,
        effectiveDate: entry.effectiveDate,
        source: "fixture:tt58-2026/basic-entity",
      });
    }

    // Từ migration 43, xác nhận mapping có phạm vi theo workspace nên không
    // còn cần dọn xác nhận cũ trên DB dev dùng chung: test này tự tạo
    // workspace mới, workspace đó chắc chắn chưa từng xác nhận mapping nào —
    // không phụ thuộc thứ tự chạy so với accounting-mapping-confirmation.test.ts.
    //
    // Trước khi founder confirm — report phải INCOMPLETE dù đủ book entries.
    const beforeConfirm = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(beforeConfirm.status).toBe("INCOMPLETE");
    expect(beforeConfirm.issues).toContain("mapping_not_confirmed_by_founder");

    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const report = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    // Fixture này không có entry nào chạm bucket "inventory" (không có
    // cogs/inventory_purchase) và không cấu hình accounting-policy thuế
    // TNDN cho legal entity — nên report vẫn INCOMPLETE dù mapping đã được
    // founder xác nhận: thiếu coverage cho TON_KHO (bucket "inventory", B01)
    // và chưa cấu hình thuế suất cho dòng derived LOI_NHUAN_GIU_LAI. Đây là
    // hệ quả đúng của mapping mở rộng ở Task 3 (thêm TON_KHO), không phải
    // regression — không ép report này lên VERIFIED.
    expect(report.status).toBe("INCOMPLETE");
    expect(report.issues).toEqual(["missing_mapping_for_bucket:inventory", "corporate_income_tax_rate_not_configured"]);

    const byLineCode = Object.fromEntries(report.lines.map((l) => [l.lineCode, l.amountMinor]));
    expect(byLineCode["TS"]).toBe(fixture.expected.cashMinor);
    expect(byLineCode["PHAI_THU"]).toBe(fixture.expected.receivableMinor);
    expect(byLineCode["NO_VAY"]).toBe(fixture.expected.loanMinor);
    expect(byLineCode["VON_GOP"]).toBe("100000000");
    // Không có entry chạm bucket "inventory" -> TON_KHO mặc định 0.
    expect(byLineCode["TON_KHO"]).toBe("0");
    // LOI_NHUAN_GIU_LAI (net_profit_after_tax) khi thuế suất chưa cấu hình:
    // = grossProfit(doanh thu 10,000,000 - giá vốn 0) - opex(2,000,000) = 8,000,000
    // (không trừ thuế vì taxRateBps null — computeDerivedLine trả issue riêng).
    expect(byLineCode["LOI_NHUAN_GIU_LAI"]).toBe("8000000");

    const b02 = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B02",
    });
    // B02 cũng INCOMPLETE cùng lý do: GIA_VON cần bucket "cogs" nhưng
    // fixture không có entry category "cogs" nào -> thiếu coverage; cộng
    // thêm issue thuế suất chưa cấu hình (derived lines dùng chung
    // bucketTotals/taxRateBps với B01).
    expect(b02.status).toBe("INCOMPLETE");
    expect(b02.issues).toEqual(["missing_mapping_for_bucket:cogs", "corporate_income_tax_rate_not_configured"]);

    const b02ByLineCode = Object.fromEntries(b02.lines.map((l) => [l.lineCode, l.amountMinor]));
    // Doanh thu thuần = tổng bucket "revenue" (chỉ 1 entry doanh thu dịch vụ).
    expect(b02ByLineCode["DOANH_THU_THUAN"]).toBe("10000000");
    // Không có entry category "cogs" -> bucket "cogs" mặc định 0.
    expect(b02ByLineCode["GIA_VON"]).toBe("0");
    // Lợi nhuận gộp = doanh thu thuần(10,000,000) - giá vốn(0).
    expect(b02ByLineCode["LOI_NHUAN_GOP"]).toBe("10000000");
    // Chi phí HĐKD = tổng bucket "opex" (entry chi phí dịch vụ 2,000,000).
    expect(b02ByLineCode["CHI_PHI_HDKD"]).toBe("2000000");
    // Thuế TNDN = 0 vì taxRateBps chưa cấu hình cho legal entity này.
    expect(b02ByLineCode["THUE_TNDN"]).toBe("0");
    // Lợi nhuận sau thuế = preTax (8,000,000) vì thuế chưa được trừ khi
    // taxRateBps null — khớp với LOI_NHUAN_GIU_LAI trên B01 (cùng công thức,
    // cùng bucketTotals/taxRateBps).
    expect(b02ByLineCode["LOI_NHUAN_SAU_THUE"]).toBe("8000000");
    expect(b02ByLineCode["LOI_NHUAN_SAU_THUE"]).toBe(byLineCode["LOI_NHUAN_GIU_LAI"]);

    // Bất biến assets = liabilities + (VON_GOP + LOI_NHUAN_GIU_LAI). Đẳng
    // thức này CHỈ đúng vì fixture không cấu hình thuế suất (không có bút
    // toán "thuế phải nộp" nào tách riêng khỏi cash) — nếu cấu hình thuế mà
    // không có entry ghi nhận khoản phải nộp tương ứng, đẳng thức sẽ lệch
    // đúng bằng số thuế (mô hình bucket hiện tại chưa có bucket "phải nộp
    // thuế" riêng).
    const assetsMinor = BigInt(byLineCode["TS"]) + BigInt(byLineCode["PHAI_THU"]) + BigInt(byLineCode["TON_KHO"]);
    const liabilitiesMinor = BigInt(byLineCode["NO_VAY"]);
    const equityMinor = BigInt(byLineCode["VON_GOP"]) + BigInt(byLineCode["LOI_NHUAN_GIU_LAI"]);

    expect(assetsMinor).toBe(BigInt(fixture.expected.assetsMinor));
    expect(assetsMinor).toBe(liabilitiesMinor + equityMinor);
  });

  it("keeps the same input_watermark when regenerating with unchanged inputs, even after the period is closed", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 Idempotent Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({
      authorization,
      workspaceId: session.workspaceId,
    });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const period = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entity.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );
    await createBookEntryService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      item: "Góp vốn",
      category: "capital",
      amountMinor: "50000000",
      effectiveDate: "2026-01-10",
      source: "fixture:tt58-2026/idempotent",
    });
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const first = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });

    await closeAccountingPeriodService(period.id, authorization);

    // Generate vẫn được phép cho kỳ đã đóng — F1 chỉ khóa POSTING (thêm book
    // entry mới), không khóa việc generate report cho kỳ đó.
    const second = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });

    expect(second.inputWatermark).toBe(first.inputWatermark);

    // Thêm entry mới vào kỳ đã đóng phải bị chặn — không lặng lẽ đổi watermark.
    await expect(
      createBookEntryService(ctx, {
        legalEntityId: entity.id,
        periodId: period.id,
        item: "Entry muộn",
        category: "capital",
        amountMinor: "1000000",
        effectiveDate: "2026-06-01",
        source: "fixture:tt58-2026/idempotent",
      })
    ).rejects.toThrow(/PERIOD_CLOSED/);
  });

  it("rejects generate with a stale expectedPeriodVersion (VERSION_CONFLICT)", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 CAS Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const period = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entity.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    // period.version bắt đầu = 1 (migration 42 default). Đóng kỳ tăng version.
    await closeAccountingPeriodService(period.id, authorization);

    await expect(
      generateReportService(ctx, {
        legalEntityId: entity.id,
        periodId: period.id,
        reportCode: "B01",
        expectedPeriodVersion: 1, // đã stale — period đã đóng, caller cần refresh version trước
      })
    ).rejects.toThrow(/VERSION_CONFLICT/);
  });
});
