import { describe, expect, it } from "vitest";
import { and, eq } from "drizzle-orm";
import fixture from "./fixtures/tt58-2026/basic-entity.json";
import { db, schema } from "../models/db";
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

    // confirmMappingService là idempotent TOÀN CỤC theo (regimeCode,
    // mappingVersion) — bảng accounting_mapping_confirmations không có
    // workspaceId (xem comment trong accounting-reports.service.ts: xác
    // nhận nội dung mapping đối chiếu văn bản luật chỉ cần làm 1 lần, không
    // phải theo từng workspace). Vì test này chạy trên Postgres dev DÙNG
    // CHUNG, persistent giữa các lần chạy test khác nhau (không có
    // truncate), dọn sạch xác nhận cũ của đúng mapping này trước khi assert
    // "chưa xác nhận" — tránh test phụ thuộc thứ tự chạy file test khác
    // (vd. accounting-mapping-confirmation.test.ts) đã từng xác nhận mapping
    // này trong lịch sử.
    await db
      .delete(schema.accountingMappingConfirmations)
      .where(
        and(
          eq(schema.accountingMappingConfirmations.regimeCode, TT58_2026_MAPPING.regimeCode),
          eq(schema.accountingMappingConfirmations.mappingVersion, TT58_2026_MAPPING.mappingVersion)
        )
      );

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
    expect(report.status).toBe("VERIFIED");
    expect(report.issues).toEqual([]);

    const byLineCode = Object.fromEntries(report.lines.map((l) => [l.lineCode, l.amountMinor]));
    expect(byLineCode["TS"]).toBe(fixture.expected.cashMinor);
    expect(byLineCode["PHAI_THU"]).toBe(fixture.expected.receivableMinor);
    expect(byLineCode["NO_VAY"]).toBe(fixture.expected.loanMinor);
    expect(byLineCode["VON_GOP"]).toBe("100000000");

    const assetsMinor = BigInt(byLineCode["TS"]) + BigInt(byLineCode["PHAI_THU"]);
    const liabilitiesMinor = BigInt(byLineCode["NO_VAY"]);
    const b02 = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B02",
    });
    const profitLine = b02.lines.find((l) => l.lineCode === "LOI_NHUAN")!;
    const equityMinor = BigInt(byLineCode["VON_GOP"]) + BigInt(profitLine.amountMinor);

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
