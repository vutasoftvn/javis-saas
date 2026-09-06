import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { openAccountingPeriodService, closeAccountingPeriodService } from "../services/accounting-period.service";
import {
  createBookEntryService,
  listBookEntriesService,
} from "../services/accounting-books.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const ctx = await resolveTenantContext({
    authorization,
    workspaceId: session.workspaceId,
  });
  return { session, ctx, authorization, legalEntityId: entity.id };
}

describe("accounting-books.service", () => {
  it("creates a book entry inside an open period", async () => {
    const { ctx, authorization, legalEntityId } = await foundersSetup("Books Create Ws");
    const period = await openAccountingPeriodService(
      {
        workspaceId: ctx.workspaceId,
        legalEntityId,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );

    const entry = await createBookEntryService(ctx, {
      legalEntityId,
      periodId: period.id,
      item: "Góp vốn thành lập",
      category: "capital",
      amountMinor: "100000000",
      effectiveDate: "2026-01-05",
      source: "fixture:tt58-2026",
    });

    expect(entry.category).toBe("capital");
    expect(entry.amountMinor).toBe("100000000");

    const entries = await listBookEntriesService(ctx, { legalEntityId, periodId: period.id });
    expect(entries).toHaveLength(1);
  });

  it("rejects a book entry dated inside a closed period", async () => {
    const { ctx, authorization, legalEntityId } = await foundersSetup("Books Closed Ws");
    const period = await openAccountingPeriodService(
      {
        workspaceId: ctx.workspaceId,
        legalEntityId,
        startDate: "2025-01-01",
        endDate: "2025-12-31",
      },
      authorization
    );
    await closeAccountingPeriodService(period.id, authorization);

    await expect(
      createBookEntryService(ctx, {
        legalEntityId,
        periodId: period.id,
        item: "Chi phí muộn",
        category: "opex",
        amountMinor: "1000000",
        effectiveDate: "2025-06-15",
        source: "fixture:tt58-2026",
      })
    ).rejects.toThrow(/PERIOD_CLOSED/);
  });

  it("rejects an entry whose periodId points at a different (closed) period than the one its effectiveDate falls in", async () => {
    const { ctx, authorization, legalEntityId } = await foundersSetup("Books Period Mismatch Ws");

    // Kỳ 2025 đã đóng và kỳ 2026 đang mở, cùng một pháp nhân.
    const closedPeriod = await openAccountingPeriodService(
      {
        workspaceId: ctx.workspaceId,
        legalEntityId,
        startDate: "2025-01-01",
        endDate: "2025-12-31",
      },
      authorization
    );
    await closeAccountingPeriodService(closedPeriod.id, authorization);

    const openPeriod = await openAccountingPeriodService(
      {
        workspaceId: ctx.workspaceId,
        legalEntityId,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );

    // effectiveDate nằm trong kỳ 2026 ĐANG MỞ nên `assertOpenPostingPeriod`
    // (tìm kỳ theo khoảng ngày) cho qua — nhưng periodId lại trỏ tới kỳ 2025
    // ĐÃ ĐÓNG. Không được phép ghi: bút toán sẽ nằm sai kỳ và làm sai sổ/báo
    // cáo của kỳ đã đóng.
    await expect(
      createBookEntryService(ctx, {
        legalEntityId,
        periodId: closedPeriod.id,
        item: "Bút toán gán sai kỳ",
        category: "opex",
        amountMinor: "1000000",
        effectiveDate: "2026-06-15",
        source: "fixture:tt58-2026",
      })
    ).rejects.toThrow(/PERIOD_CLOSED/);

    // Kỳ đóng vẫn phải trống, và kỳ mở cũng không nhận bút toán nào.
    expect(
      await listBookEntriesService(ctx, { legalEntityId, periodId: closedPeriod.id })
    ).toHaveLength(0);
    expect(
      await listBookEntriesService(ctx, { legalEntityId, periodId: openPeriod.id })
    ).toHaveLength(0);
  });
});
