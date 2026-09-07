import { describe, expect, it } from "vitest";
import fixture from "./fixtures/tt58-2026/basic-entity.json";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { createFiscalProfileService } from "../services/accounting-regime.service";
import { openAccountingPeriodService, closeAccountingPeriodService } from "../services/accounting-period.service";
import { createBookEntryService } from "../services/accounting-books.service";
import { setAccountingPolicyService } from "../services/accounting-policy.service";
import {
  generateReportService,
  confirmMappingService,
  listReportSnapshotsService,
} from "../services/accounting-reports.service";
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
    // Fixture này không cấu hình accounting-policy thuế TNDN cho legal
    // entity — nên report vẫn INCOMPLETE dù mapping đã được founder xác
    // nhận: dòng derived LOI_NHUAN_GIU_LAI thiếu thuế suất.
    //
    // Việc fixture không có entry nào chạm bucket "inventory" KHÔNG còn là
    // issue: coverage theo bucket đã bị gỡ khỏi việc gán status (xem
    // computeReportStatus) vì nó đánh đồng "mapping thiếu cấu hình" với
    // "doanh nghiệp hợp lệ khi không có giao dịch ở bucket đó".
    expect(report.status).toBe("INCOMPLETE");
    expect(report.issues).toEqual(["corporate_income_tax_rate_not_configured"]);

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
    // B02 INCOMPLETE cùng một lý do duy nhất với B01: thuế suất chưa cấu
    // hình (derived lines dùng chung bucketTotals/taxRateBps với B01).
    // Việc fixture không có entry category "cogs" không còn sinh issue.
    expect(b02.status).toBe("INCOMPLETE");
    expect(b02.issues).toEqual(["corporate_income_tax_rate_not_configured"]);

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

  it("reaches VERIFIED for a pure-service business that never touches inventory/cogs", async () => {
    // Đây là kịch bản lõi mà việc gỡ bucket-coverage khỏi status tồn tại để
    // sửa: doanh nghiệp thuần dịch vụ (phần lớn doanh nghiệp siêu nhỏ VN)
    // không bao giờ có giao dịch inventory/cogs. Trước đây B01/B02 vĩnh viễn
    // INCOMPLETE với `missing_mapping_for_bucket:inventory`/`:cogs` dù dữ
    // liệu đầy đủ và founder đã xác nhận mapping.
    const session = await createTestSession({ role: "founder", displayName: "TT58 Service-Only Ws" });
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

    // Chỉ doanh thu dịch vụ + chi phí hoạt động — không hề có cogs hay
    // inventory_purchase.
    await createBookEntryService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      item: "Doanh thu dịch vụ tư vấn",
      category: "revenue",
      amountMinor: "30000000",
      effectiveDate: "2026-02-01",
      source: "test:service-only",
    });
    await createBookEntryService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      item: "Chi phí vận hành",
      category: "opex",
      amountMinor: "10000000",
      effectiveDate: "2026-02-02",
      source: "test:service-only",
    });

    // Cấu hình thuế suất -> loại bỏ issue của dòng derived; xác nhận mapping
    // -> loại bỏ issue xác nhận. Không còn issue nào khác được phép tồn tại.
    await setAccountingPolicyService(ctx, { legalEntityId: entity.id, corporateIncomeTaxRateBps: 2000 });
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const b01 = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(b01.issues).toEqual([]);
    expect(b01.status).toBe("VERIFIED");

    const b02 = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B02",
    });
    expect(b02.issues).toEqual([]);
    expect(b02.status).toBe("VERIFIED");

    // Dòng tồn kho/giá vốn vẫn hiện diện với giá trị 0 — báo cáo đầy đủ dòng
    // theo mapping, chỉ là không có số liệu, đúng bản chất doanh nghiệp dịch vụ.
    const b01ByLineCode = Object.fromEntries(b01.lines.map((l) => [l.lineCode, l.amountMinor]));
    expect(b01ByLineCode["TON_KHO"]).toBe("0");
    const b02ByLineCode = Object.fromEntries(b02.lines.map((l) => [l.lineCode, l.amountMinor]));
    expect(b02ByLineCode["GIA_VON"]).toBe("0");
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

  /**
   * GHIM hành vi HIỆN TẠI, đã biết là chưa hoàn chỉnh — KHÔNG phải mô tả
   * hành vi mong muốn.
   *
   * B01 không có dòng/bucket nào cho `payable` (chi phí dồn tích chưa trả),
   * `advance`, hay thuế phải nộp. Nên hễ kỳ kế toán kết thúc mà còn khoản
   * opex chưa thanh toán, hoặc có thuế TNDN đã tính, thì đẳng thức
   * `Tài sản = Nợ + Vốn CSH` LỆCH đúng bằng tổng hai khoản đó. Đây là lỗ
   * hổng cấu trúc kế thừa từ thiết kế 5 bucket của F5, không phải do F6b gây
   * ra — F6b chỉ là code đầu tiên quan tâm tới đẳng thức này.
   *
   * Test này tồn tại để không ai vô tình "sửa" mà không nhận ra, và để khi
   * nào sửa thật thì đã có sẵn một test đỏ rõ ràng cần chuyển sang xanh.
   */
  it("PINS the known balance-equation gap: unpaid opex + CIT are missing from B01 liabilities", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 Balance Gap Ws" });
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

    // Vốn góp 100tr -> cash +100tr, capital +100tr.
    await createBookEntryService(ctx, {
      legalEntityId: entity.id, periodId: period.id, item: "Góp vốn",
      category: "capital", amountMinor: "100000000", effectiveDate: "2026-01-05", source: "test:balance-gap",
    });
    // Doanh thu 30tr (dồn tích) -> receivable +30tr, revenue +30tr.
    await createBookEntryService(ctx, {
      legalEntityId: entity.id, periodId: period.id, item: "Doanh thu dịch vụ",
      category: "revenue", amountMinor: "30000000", effectiveDate: "2026-02-01", source: "test:balance-gap",
    });
    // Chi phí 10tr CHƯA THANH TOÁN -> payable +10tr, opex +10tr. Không có
    // entry category "payable" nào đối trừ, nên cuối kỳ vẫn còn nợ 10tr.
    await createBookEntryService(ctx, {
      legalEntityId: entity.id, periodId: period.id, item: "Chi phí thuê ngoài chưa trả",
      category: "opex", amountMinor: "10000000", effectiveDate: "2026-03-01", source: "test:balance-gap",
    });

    await setAccountingPolicyService(ctx, { legalEntityId: entity.id, corporateIncomeTaxRateBps: 2000 });
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const b01 = await generateReportService(ctx, {
      legalEntityId: entity.id, periodId: period.id, reportCode: "B01",
    });

    // Báo cáo tự nhận là VERIFIED — status KHÔNG hề biết gì về việc đẳng
    // thức cân đối đang lệch. Đó chính là điều làm lỗ hổng này âm thầm.
    expect(b01.status).toBe("VERIFIED");
    expect(b01.issues).toEqual([]);

    const line = Object.fromEntries(b01.lines.map((l) => [l.lineCode, l.amountMinor]));
    // preTax = revenue(30tr) - cogs(0) - opex(10tr) = 20tr
    // thuế TNDN = 20tr * 20% = 4tr; lợi nhuận sau thuế = 16tr
    expect(line["LOI_NHUAN_GIU_LAI"]).toBe("16000000");

    const assets = BigInt(line["TS"]) + BigInt(line["PHAI_THU"]) + BigInt(line["TON_KHO"]);
    const liabilities = BigInt(line["NO_VAY"]);
    const equity = BigInt(line["VON_GOP"]) + BigInt(line["LOI_NHUAN_GIU_LAI"]);

    expect(assets).toBe(130000000n); // cash 100tr + receivable 30tr
    expect(liabilities).toBe(0n); // B01 chỉ có NO_VAY; payable 10tr vô hình
    expect(equity).toBe(116000000n); // vốn góp 100tr + lãi sau thuế 16tr

    // LỆCH 14tr = payable chưa trả (10tr) + thuế TNDN phải nộp (4tr) —
    // đúng hai bucket mà B01 hiện chưa có dòng nào biểu diễn.
    expect(assets - (liabilities + equity)).toBe(14000000n);
    expect(assets).not.toBe(liabilities + equity);
  });

  it("does not write a redundant snapshot when nothing changed, but does when the data changes", async () => {
    // Tab TT58 ở Flutter gọi generate mỗi lần mở màn hình — insert vô điều
    // kiện làm bảng audit phình ra chỉ vì người dùng xem báo cáo.
    const session = await createTestSession({ role: "founder", displayName: "TT58 Dedup Ws" });
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
    await createBookEntryService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      item: "Góp vốn",
      category: "capital",
      amountMinor: "50000000",
      effectiveDate: "2026-01-10",
      source: "test:dedup",
    });
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const first = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });
    const second = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });

    // Lần 2 trả về ĐÚNG dòng cũ, không tạo dòng mới.
    expect(second.id).toBe(first.id);
    const afterTwoReads = await listReportSnapshotsService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(afterTwoReads.length).toBe(1);

    // Dữ liệu đổi thật (watermark đổi) -> phải ghi snapshot mới.
    await createBookEntryService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      item: "Doanh thu dịch vụ",
      category: "revenue",
      amountMinor: "7000000",
      effectiveDate: "2026-03-01",
      source: "test:dedup",
    });
    const third = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });
    expect(third.id).not.toBe(first.id);
    expect(third.inputWatermark).not.toBe(first.inputWatermark);

    const afterChange = await listReportSnapshotsService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(afterChange.length).toBe(2);
  });

  it("writes a new snapshot when only the status changed, even though the watermark is identical", async () => {
    // `inputWatermark` không mã hóa trạng thái xác nhận mapping, nên nếu chỉ
    // so watermark thì việc founder xác nhận SAU đó sẽ bị che mất: người dùng
    // vẫn nhận lại snapshot INCOMPLETE cũ.
    const session = await createTestSession({ role: "founder", displayName: "TT58 Dedup Status Ws" });
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

    const before = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });
    expect(before.issues).toContain("mapping_not_confirmed_by_founder");

    // Không đụng vào book entry nào -> watermark giữ nguyên, chỉ status đổi.
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);
    const after = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });

    expect(after.inputWatermark).toBe(before.inputWatermark);
    expect(after.id).not.toBe(before.id);
    expect(after.issues).not.toContain("mapping_not_confirmed_by_founder");

    const snapshots = await listReportSnapshotsService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(snapshots.length).toBe(2);
  });

  it("rejects generate when the period belongs to a different legal entity", async () => {
    // Trước đây cặp (periodId, legalEntityId) lệch nhau chỉ lặng lẽ trả về 0
    // book entry -> báo cáo toàn số 0 trông như báo cáo thật.
    const session = await createTestSession({ role: "founder", displayName: "TT58 Entity Mismatch Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
    const entityA = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const entityB = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const periodA = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entityA.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );

    await expect(
      generateReportService(ctx, {
        legalEntityId: entityB.id,
        periodId: periodA.id,
        reportCode: "B01",
      })
    ).rejects.toThrow(/belongs to a different legal entity/);

    // Đúng cặp entity/period thì vẫn chạy bình thường.
    const ok = await generateReportService(ctx, {
      legalEntityId: entityA.id,
      periodId: periodA.id,
      reportCode: "B01",
    });
    expect(ok.periodId).toBe(periodA.id);
  });

  it("rejects generate for a period id that does not exist in this workspace", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 Unknown Period Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });

    await expect(
      generateReportService(ctx, {
        legalEntityId: entity.id,
        periodId: "999999999999999",
        reportCode: "B01",
      })
    ).rejects.toThrow(/not found/);
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
