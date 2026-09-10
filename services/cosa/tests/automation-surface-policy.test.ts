import { describe, it, expect } from "vitest";
import { FOUNDER_TRIAL_SURFACE_POLICY, SURFACE_POLICY_VERSION } from "../services/surface-policy";

describe("automation surface policy", () => {
  const automation = FOUNDER_TRIAL_SURFACE_POLICY.filter((e) => e.moduleKey === "automation");

  it("registers an automation.library surface", () => {
    const lib = automation.find((e) => e.surfaceKey === "automation.library");
    expect(lib).toBeDefined();
  });

  it("promotes the automation library to PILOT with enabled capabilities", () => {
    const lib = automation.find((e) => e.surfaceKey === "automation.library")!;
    expect(lib.defaultStatus).toBe("PILOT");
    expect(lib.contractEndpoint).toBe("automation.definition.list");
    expect(lib.requiredCapabilities).toContain("automation.definition.list");
    expect(lib.requiredCapabilities).toContain("automation.run.inspector.read");
  });

  it("the surface policy version was bumped for the automation change", () => {
    expect(SURFACE_POLICY_VERSION >= "2026-09-10.3").toBe(true);
  });
});
