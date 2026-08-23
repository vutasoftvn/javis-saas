import { describe, it, expect } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createFiscalProfile, listFiscalProfiles, createCoaMapping } from "../handlers/accounting-regime.handler";

describe("Accounting Regime Vietnam (TT58/TT199) Service", () => {
  it("creates a fiscal profile and lists it", async () => {
    const user = await createTestSession({
      email: `regime-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Regime Test",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const profile = await createFiscalProfile({
      workspaceId: user.workspaceId,
      fiscalYear: 2026,
      regulationCode: "TT58_2026",
      mode: "TT58_MODE_1",
      authorization,
    });

    expect(profile.id).toBeDefined();
    expect(profile.workspaceId).toBe(user.workspaceId);
    expect(profile.fiscalYear).toBe(2026);
    expect(profile.regulationCode).toBe("TT58_2026");
    expect(profile.status).toBe("ACTIVE");

    const list = await listFiscalProfiles({ workspaceId: user.workspaceId, authorization });
    expect(list.profiles.some((p) => p.id === profile.id)).toBe(true);
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const owner = await createTestSession({
      email: `regime-owner-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Regime Owner",
    });
    const outsider = await createTestSession({
      email: `regime-outsider-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Regime Outsider",
    });

    await expect(
      createFiscalProfile({
        workspaceId: owner.workspaceId,
        fiscalYear: 2026,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("creates a COA mapping rule between TT58 and TT199", async () => {
    const mapping = await createCoaMapping({
      sourceRegulation: "TT58_2026",
      targetRegulation: "TT199_2026",
      sourceAccountCode: "111",
      targetAccountCode: "1111",
      mappingType: "DIRECT_1_1",
      description: "Tiền mặt VND",
    });

    expect(mapping.id).toBeDefined();
    expect(mapping.sourceAccountCode).toBe("111");
    expect(mapping.targetAccountCode).toBe("1111");
    expect(mapping.mappingType).toBe("DIRECT_1_1");
  });
});
