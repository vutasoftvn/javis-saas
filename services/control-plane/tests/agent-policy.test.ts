import { describe, it, expect } from "vitest";
import { registerPlatform } from "../handlers/auth.handler";
import { getTenantPolicy, setTenantPolicy } from "../handlers/agent-policy.handler";

describe("Agent Policy (TenantPolicy, roadmap Phase 10a)", () => {
  it("returns no decision when a company has not configured any policy", async () => {
    const res = await registerPlatform({
      email: `policy_none_${Date.now()}@example.com`,
      password: "password123",
      full_name: "No Policy Founder",
      company_name: "No Policy Co",
    });

    const result = await getTenantPolicy({ companyId: res.company_id!, toolName: "commercial.lead.create" });
    expect(result.decision).toBeNull();
  });

  it("returns exact tool match decision over wildcard", async () => {
    const res = await registerPlatform({
      email: `policy_exact_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Exact Policy Founder",
      company_name: "Exact Policy Co",
    });
    const companyId = res.company_id!;

    await setTenantPolicy({ companyId, toolPattern: "*", decision: "ALLOW" });
    await setTenantPolicy({
      companyId,
      toolPattern: "commercial.notification.slack_send",
      decision: "DENY",
      reason: "Company policy blocks all outbound Slack messages",
    });

    const exactResult = await getTenantPolicy({ companyId, toolName: "commercial.notification.slack_send" });
    expect(exactResult.decision).toBe("DENY");
    expect(exactResult.matchedPattern).toBe("commercial.notification.slack_send");
    expect(exactResult.reason).toContain("Slack");

    const wildcardResult = await getTenantPolicy({ companyId, toolName: "commercial.lead.create" });
    expect(wildcardResult.decision).toBe("ALLOW");
    expect(wildcardResult.matchedPattern).toBe("*");
  });

  it("matches prefix wildcard patterns like 'finance.*'", async () => {
    const res = await registerPlatform({
      email: `policy_prefix_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Prefix Policy Founder",
      company_name: "Prefix Policy Co",
    });
    const companyId = res.company_id!;

    await setTenantPolicy({ companyId, toolPattern: "finance.*", decision: "REQUIRE_APPROVAL" });

    const result = await getTenantPolicy({ companyId, toolName: "finance.transfer.funds" });
    expect(result.decision).toBe("REQUIRE_APPROVAL");
    expect(result.matchedPattern).toBe("finance.*");
  });

  it("upsert overwrites an existing rule for the same company + tool_pattern", async () => {
    const res = await registerPlatform({
      email: `policy_upsert_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Upsert Policy Founder",
      company_name: "Upsert Policy Co",
    });
    const companyId = res.company_id!;

    await setTenantPolicy({ companyId, toolPattern: "ops.deploy.prod", decision: "ALLOW" });
    await setTenantPolicy({ companyId, toolPattern: "ops.deploy.prod", decision: "DENY", reason: "frozen" });

    const result = await getTenantPolicy({ companyId, toolName: "ops.deploy.prod" });
    expect(result.decision).toBe("DENY");
    expect(result.reason).toBe("frozen");
  });

  it("isolates policy rules per company (no cross-tenant leakage)", async () => {
    const resA = await registerPlatform({
      email: `policy_iso_a_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Company A Founder",
      company_name: "Company A",
    });
    const resB = await registerPlatform({
      email: `policy_iso_b_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Company B Founder",
      company_name: "Company B",
    });

    await setTenantPolicy({ companyId: resA.company_id!, toolPattern: "*", decision: "DENY" });

    const resultA = await getTenantPolicy({ companyId: resA.company_id!, toolName: "commercial.lead.create" });
    const resultB = await getTenantPolicy({ companyId: resB.company_id!, toolName: "commercial.lead.create" });

    expect(resultA.decision).toBe("DENY");
    expect(resultB.decision).toBeNull();
  });
});
