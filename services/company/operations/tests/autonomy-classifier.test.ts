import { describe, it, expect } from "vitest";
import {
  classifyItem,
  routeOwnerProfile,
  validateFounderOverride,
  FORBIDDEN_CAPABILITY_RE,
} from "../services/autonomy-classifier";

describe("classifyItem", () => {
  it("no capability -> FOUNDER_ONLY", () => {
    expect(
      classifyItem({ expectedCapability: null, capabilityRisk: null, tenantPolicyDecision: null })
    ).toEqual({ autonomyClass: "FOUNDER_ONLY", source: "classifier_default" });
  });

  it("forbidden capability -> NEEDS_APPROVAL even when tenant policy is ALLOW", () => {
    expect(
      classifyItem({
        expectedCapability: "engagement.message.send",
        capabilityRisk: "MEDIUM",
        tenantPolicyDecision: "ALLOW",
      })
    ).toEqual({ autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" });
  });

  it("tenant policy DENY -> FOUNDER_ONLY", () => {
    expect(
      classifyItem({
        expectedCapability: "operations.sop.draft",
        capabilityRisk: "LOW",
        tenantPolicyDecision: "DENY",
      })
    ).toEqual({ autonomyClass: "FOUNDER_ONLY", source: "tenant_policy" });
  });

  it("tenant policy REQUIRE_APPROVAL -> NEEDS_APPROVAL", () => {
    expect(
      classifyItem({
        expectedCapability: "operations.task.create_draft",
        capabilityRisk: "MEDIUM",
        tenantPolicyDecision: "REQUIRE_APPROVAL",
      })
    ).toEqual({ autonomyClass: "NEEDS_APPROVAL", source: "tenant_policy" });
  });

  it("tenant policy ALLOW (non-forbidden) -> AUTO", () => {
    expect(
      classifyItem({
        expectedCapability: "operations.task.list",
        capabilityRisk: "LOW",
        tenantPolicyDecision: "ALLOW",
      })
    ).toEqual({ autonomyClass: "AUTO", source: "tenant_policy" });
  });

  it("default: LOW risk read/draft capability -> AUTO", () => {
    expect(
      classifyItem({
        expectedCapability: "operations.task.list",
        capabilityRisk: "LOW",
        tenantPolicyDecision: null,
      })
    ).toEqual({ autonomyClass: "AUTO", source: "classifier_default" });
  });

  it("default: MEDIUM risk -> NEEDS_APPROVAL", () => {
    expect(
      classifyItem({
        expectedCapability: "operations.task.create_draft",
        capabilityRisk: "MEDIUM",
        tenantPolicyDecision: null,
      }).autonomyClass
    ).toBe("NEEDS_APPROVAL");
  });

  it("default: HIGH / unknown risk -> NEEDS_APPROVAL", () => {
    expect(
      classifyItem({
        expectedCapability: "some.capability.run",
        capabilityRisk: null,
        tenantPolicyDecision: null,
      }).autonomyClass
    ).toBe("NEEDS_APPROVAL");
  });

  it("default: LOW risk but non-safe suffix -> NEEDS_APPROVAL", () => {
    expect(
      classifyItem({
        expectedCapability: "operations.task.reassign",
        capabilityRisk: "LOW",
        tenantPolicyDecision: null,
      }).autonomyClass
    ).toBe("NEEDS_APPROVAL");
  });

  it("FORBIDDEN_CAPABILITY_RE matches the known dangerous prefixes", () => {
    for (const c of [
      "billing.charge",
      "finance.write.payout",
      "commercial.opportunity.close",
      "commercial.lead.write",
      "engagement.message.send",
      "legal.write.contract",
      "infra.deploy",
      "operations.task.delete",
      "workspace.settings.update",
    ]) {
      expect(FORBIDDEN_CAPABILITY_RE.test(c)).toBe(true);
    }
    for (const c of ["operations.task.list", "operations.sop.draft", "finance.runway.read"]) {
      expect(FORBIDDEN_CAPABILITY_RE.test(c)).toBe(false);
    }
  });
});

describe("routeOwnerProfile", () => {
  it("routes by capability prefix", () => {
    expect(routeOwnerProfile("finance.runway.read", "operations")).toBe("finance");
    expect(routeOwnerProfile("engagement.message.draft", null)).toBe("operations");
    expect(routeOwnerProfile("marketing.gtm.plan", null)).toBe("marketing");
    expect(routeOwnerProfile("research.deep_research.run", null)).toBe("marketing");
  });

  it("no capability + domain matches keyword -> domain profile", () => {
    expect(routeOwnerProfile(null, "marketing campaign")).toBe("marketing");
    expect(routeOwnerProfile(null, "cash runway review")).toBe("finance");
    expect(routeOwnerProfile(null, "process / SOP work")).toBe("operations");
  });

  it("no capability + unknown domain -> null (founder)", () => {
    expect(routeOwnerProfile(null, "legal review with lawyer")).toBeNull();
    expect(routeOwnerProfile(null, null)).toBeNull();
  });
});

describe("validateFounderOverride", () => {
  it("blocks raising a forbidden capability to AUTO", () => {
    const r = validateFounderOverride("AUTO", {
      expectedCapability: "billing.charge",
      capabilityRisk: "HIGH",
      tenantPolicyDecision: "ALLOW",
    });
    expect(r.ok).toBe(false);
  });

  it("blocks AUTO when tenant policy is not ALLOW", () => {
    expect(
      validateFounderOverride("AUTO", {
        expectedCapability: "operations.sop.draft",
        capabilityRisk: "LOW",
        tenantPolicyDecision: "REQUIRE_APPROVAL",
      }).ok
    ).toBe(false);
  });

  it("blocks AUTO when no capability attached", () => {
    expect(
      validateFounderOverride("AUTO", {
        expectedCapability: null,
        capabilityRisk: null,
        tenantPolicyDecision: null,
      }).ok
    ).toBe(false);
  });

  it("allows AUTO for a safe capability with tenant policy ALLOW", () => {
    expect(
      validateFounderOverride("AUTO", {
        expectedCapability: "operations.task.list",
        capabilityRisk: "LOW",
        tenantPolicyDecision: "ALLOW",
      }).ok
    ).toBe(true);
  });

  it("always allows downgrade to FOUNDER_ONLY / NEEDS_APPROVAL", () => {
    const input = {
      expectedCapability: "operations.task.list",
      capabilityRisk: "LOW" as const,
      tenantPolicyDecision: "ALLOW" as const,
    };
    expect(validateFounderOverride("FOUNDER_ONLY", input).ok).toBe(true);
    expect(validateFounderOverride("NEEDS_APPROVAL", input).ok).toBe(true);
  });
});
