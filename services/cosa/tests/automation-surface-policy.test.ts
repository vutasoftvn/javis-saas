import { describe, it, expect } from "vitest";
import { FOUNDER_TRIAL_SURFACE_POLICY, SURFACE_POLICY_VERSION } from "../services/surface-policy";

describe("project operating loop surface policy", () => {
  const ops = FOUNDER_TRIAL_SURFACE_POLICY.filter((e) => e.moduleKey === "operations");

  it("registers a project.operating_loop surface", () => {
    const loop = ops.find((e) => e.surfaceKey === "project.operating_loop");
    expect(loop).toBeDefined();
    expect(loop!.defaultStatus).toBe("AVAILABLE");
    expect(loop!.contractEndpoint).toBe("project.loop.read");
    expect(loop!.requiredCapabilities).toContain("project.loop.read");
    expect(loop!.requiredCapabilities).toContain("project.task.write");
  });

  it("the surface policy version was bumped for Startup Core", () => {
    expect(SURFACE_POLICY_VERSION).toContain("startup-core");
  });
});
