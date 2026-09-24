import { beforeAll, describe, expect, it } from "vitest";
import {
  FOUNDER_TRIAL_SURFACE_POLICY,
  type SurfacePolicyEntry,
} from "../services/surface-policy";
import {
  loadEnabledMvpCapabilityIds,
  validateSurfacePolicyAgainstMvpContract,
} from "../services/mvp-contract-policy";
import { getWorkspaceCapabilityManifest } from "../handlers/workspace-settings.handler";
import { registerPlatformUser } from "./support/test-identity";

const enabledIds = loadEnabledMvpCapabilityIds();

function entry(over: Partial<SurfacePolicyEntry>): SurfacePolicyEntry {
  return {
    surfaceKey: "x.surface",
    moduleKey: "strategy",
    featureKey: "x",
    defaultStatus: "AVAILABLE",
    requiredCapabilities: [],
    requiredConnectorKeys: [],
    contractEndpoint: null,
    releaseNote: null,
    ...over,
  };
}

describe("Surface policy ↔ MVP contract binding", () => {
  it("rejects an AVAILABLE surface with no enabled contract capability", () => {
    expect(() =>
      validateSurfacePolicyAgainstMvpContract(
        [entry({ defaultStatus: "AVAILABLE", requiredCapabilities: [] })],
        enabledIds
      )
    ).toThrow(/requiredCapabilities/);
  });

  it("rejects a PILOT surface referencing an unknown capability id", () => {
    expect(() =>
      validateSurfacePolicyAgainstMvpContract(
        [
          entry({
            defaultStatus: "PILOT",
            requiredCapabilities: ["marketing.legacy.loop"],
            contractEndpoint: "marketing.legacy.loop",
          }),
        ],
        enabledIds
      )
    ).toThrow(/not an enabled MVP contract capability/);
  });

  it("rejects a PLANNED surface that still has a contractEndpoint", () => {
    expect(() =>
      validateSurfacePolicyAgainstMvpContract(
        [
          entry({
            defaultStatus: "PLANNED",
            requiredCapabilities: [],
            contractEndpoint: "strategy.founder_brief.read",
          }),
        ],
        enabledIds
      )
    ).toThrow(/null contractEndpoint/);
  });

  it("accepts the real Founder Trial surface policy against the generated contract", () => {
    expect(() =>
      validateSurfacePolicyAgainstMvpContract(FOUNDER_TRIAL_SURFACE_POLICY, enabledIds)
    ).not.toThrow();
  });

  it("every live policy entry declares capabilities that all exist in the contract", () => {
    const live = FOUNDER_TRIAL_SURFACE_POLICY.filter(
      (e) => e.defaultStatus !== "PLANNED"
    );
    expect(live.length).toBeGreaterThan(0);
    for (const e of live) {
      expect(e.requiredCapabilities.length).toBeGreaterThan(0);
      expect(e.contractEndpoint).not.toBeNull();
      for (const cap of e.requiredCapabilities) {
        expect(enabledIds.has(cap)).toBe(true);
      }
    }
  });
});

describe("Workspace capability manifest reflects the contract-bound policy", () => {
  let wsId: string;
  let token: string;

  beforeAll(async () => {
    const op = await registerPlatformUser({
      email: `cap-contract-${Date.now()}@test.io`,
      password: "SecurePassword123",
      workspace_name: "Capability Contract Workspace",
    });
    wsId = op.platform_workspace_id!;
    token = op.access_token;
  });

  it("gives every live surface a non-empty requiredCapabilities list", async () => {
    const res = await getWorkspaceCapabilityManifest({
      organizationId: wsId,
      authorization: `Bearer ${token}`,
    });
    for (const s of res.data.surfaces) {
      if (s.surfaceStatus === "PLANNED") {
        expect(s.contractEndpoint).toBeNull();
      } else {
        expect(s.requiredCapabilities.length).toBeGreaterThan(0);
        expect(s.contractEndpoint).not.toBeNull();
      }
    }
  });

  it("reports cash liquidity as CONFIGURATION_REQUIRED while CAS is not connected", async () => {
    const res = await getWorkspaceCapabilityManifest({
      organizationId: wsId,
      authorization: `Bearer ${token}`,
    });
    const cash = res.data.surfaces.find((s) => s.surfaceKey === "finance.cash_liquidity");
    expect(cash!.surfaceStatus).toBe("CONFIGURATION_REQUIRED");
    expect(cash!.reasons.some((r) => r.startsWith("connector_missing:cas"))).toBe(true);
  });
});
