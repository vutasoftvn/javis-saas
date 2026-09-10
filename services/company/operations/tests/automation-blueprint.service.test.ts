import { describe, it, expect } from "vitest";
import {
  listCuratedBlueprints,
  getCuratedBlueprintView,
  assertBlueprintConfigWithinBounds,
} from "../services/automation-blueprint.service";

describe("automation blueprint registry — read-only, non-overridable", () => {
  it("exposes exactly the four curated blueprints", () => {
    const keys = listCuratedBlueprints().data.map((b) => b.key).sort();
    expect(keys).toEqual(
      [
        "commercial.outbound-draft",
        "operating.weekly-review",
        "operations.task-follow-up",
        "strategy.initiative-health",
      ].sort()
    );
  });

  it("commercial.outbound-draft declares no delivery capability and never delivers", () => {
    const b = getCuratedBlueprintView("commercial.outbound-draft").data;
    expect(b.autonomyClass).toBe("draft_only");
    expect(b.deliversExternally).toBe(false);
    for (const cap of b.capabilityIds) {
      expect(cap).not.toMatch(/send|deliver|email|sms/i);
    }
  });

  it("rejects an unknown key", () => {
    expect(() => getCuratedBlueprintView("operating.nope")).toThrow();
  });

  it("rejects a configuration that tries to override a locked field", () => {
    for (const field of [
      "capabilityIds",
      "approvalRequired",
      "evidenceContract",
      "runtimeRequirement",
      "endpoint",
      "model",
      "prompt",
    ]) {
      expect(() =>
        assertBlueprintConfigWithinBounds("operating.weekly-review", { [field]: "x" })
      ).toThrow(/fixed by the curated blueprint/);
    }
  });

  it("accepts a configuration with only typed form fields", () => {
    expect(() =>
      assertBlueprintConfigWithinBounds("operating.weekly-review", { projectId: "p1", lookbackWeeks: 2 })
    ).not.toThrow();
  });
});
