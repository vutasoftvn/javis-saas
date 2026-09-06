import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { openAccountingPeriodService } from "../services/accounting-period.service";
import { confirmMappingService, generateReportService } from "../services/accounting-reports.service";
import { TT58_2026_MAPPING } from "../services/accounting-mapping";

describe("accounting-reports.service — confirmMappingService", () => {
  it("requires founder role", async () => {
    const session = await createTestSession({ role: "member", displayName: "Non-founder confirm" });
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });

    await expect(
      confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion)
    ).rejects.toThrow(/Missing authority/);
  });

  it("records confirmation for a founder", async () => {
    const session = await createTestSession({ role: "founder", displayName: "Founder confirm" });
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });

    const result = await confirmMappingService(
      ctx,
      TT58_2026_MAPPING.regimeCode,
      TT58_2026_MAPPING.mappingVersion
    );
    expect(result.confirmedAt).toBeTruthy();
  });

  it("does not let one workspace's founder confirmation verify another workspace's report", async () => {
    // Workspace A: founder xác nhận mapping.
    const sessionA = await createTestSession({ role: "founder", displayName: "Confirm Tenant A" });
    const ctxA = await resolveTenantContext({
      authorization: `Bearer ${sessionA.accessToken}`,
      workspaceId: sessionA.workspaceId,
    });
    await confirmMappingService(ctxA, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    // Workspace B: KHÔNG ai xác nhận. Founder của A không có thẩm quyền gì với
    // B, nên report của B phải vẫn INCOMPLETE.
    const sessionB = await createTestSession({ role: "founder", displayName: "Confirm Tenant B" });
    const authorizationB = `Bearer ${sessionB.accessToken}`;
    const ctxB = await resolveTenantContext({
      authorization: authorizationB,
      workspaceId: sessionB.workspaceId,
    });
    const entityB = await createLegalEntityProfile({
      workspaceId: BigInt(sessionB.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const periodB = await openAccountingPeriodService(
      {
        workspaceId: sessionB.workspaceId,
        legalEntityId: entityB.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorizationB
    );

    const reportB = await generateReportService(ctxB, {
      legalEntityId: entityB.id,
      periodId: periodB.id,
      reportCode: "B01",
    });
    expect(reportB.status).toBe("INCOMPLETE");
    expect(reportB.issues).toContain("mapping_not_confirmed_by_founder");

    // Sau khi chính founder của B xác nhận thì issue đó mới biến mất.
    await confirmMappingService(ctxB, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);
    const reportBAfter = await generateReportService(ctxB, {
      legalEntityId: entityB.id,
      periodId: periodB.id,
      reportCode: "B01",
    });
    expect(reportBAfter.issues).not.toContain("mapping_not_confirmed_by_founder");
  });
});
