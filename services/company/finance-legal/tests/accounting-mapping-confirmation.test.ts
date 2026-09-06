import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { confirmMappingService } from "../services/accounting-reports.service";
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
});
