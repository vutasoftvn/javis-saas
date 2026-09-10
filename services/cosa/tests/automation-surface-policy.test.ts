import { describe, it, expect } from "vitest";
import { FOUNDER_TRIAL_SURFACE_POLICY, SURFACE_POLICY_VERSION } from "../services/surface-policy";

describe("automation surface policy", () => {
  const automation = FOUNDER_TRIAL_SURFACE_POLICY.filter((e) => e.moduleKey === "automation");

  it("registers an automation.library surface", () => {
    const lib = automation.find((e) => e.surfaceKey === "automation.library");
    expect(lib).toBeDefined();
  });

  it("keeps the automation library PLANNED until the capabilities are enabled", () => {
    const lib = automation.find((e) => e.surfaceKey === "automation.library")!;
    // The startup validator (mvp-contract-policy) requires PLANNED surfaces to
    // carry no live capability and a null contract endpoint — a live surface
    // referencing a still-disabled automation.* capability would fail cosa boot.
    expect(lib.defaultStatus).toBe("PLANNED");
    expect(lib.contractEndpoint).toBeNull();
    expect(lib.requiredCapabilities).toEqual([]);
  });

  it("the surface policy version was bumped for the automation change", () => {
    expect(SURFACE_POLICY_VERSION >= "2026-09-10.2").toBe(true);
  });
});
