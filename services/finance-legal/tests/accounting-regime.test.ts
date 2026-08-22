import { describe, it, expect } from "vitest";
import { createFiscalProfile, listFiscalProfiles, createCoaMapping } from "../handlers/accounting-regime.handler";

describe("Accounting Regime Vietnam (TT58/TT199) Service", () => {
  const workspaceId = Math.floor(Math.random() * 900000) + 100000;

  it("creates a fiscal profile and lists it", async () => {
    const profile = await createFiscalProfile({
      workspaceId,
      fiscalYear: 2026,
      regulationCode: "TT58_2026",
      mode: "TT58_MODE_1",
    });

    expect(profile.id).toBeDefined();
    expect(profile.workspaceId).toBe(workspaceId);
    expect(profile.fiscalYear).toBe(2026);
    expect(profile.regulationCode).toBe("TT58_2026");
    expect(profile.status).toBe("ACTIVE");

    const list = await listFiscalProfiles({ workspaceId });
    expect(list.profiles.some((p) => p.id === profile.id)).toBe(true);
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
