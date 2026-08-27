import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { registerPlatform } from "../handlers/auth.handler";
import { getTenantPolicy, setTenantPolicy } from "../handlers/agent-policy.handler";
import { getTenantPolicySnapshotForCaller } from "../services/agent-policy.service";
import { verifyPlatformToken } from "../services/token.service";

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

describe("getTenantPolicySnapshotForCaller (COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.3 mục 1)", () => {
  const workspaceToCompanyMap = new Map<string, string>();

  beforeEach(() => {
    // Mock fetch to simulate services/company endpoint
    // Map workspace IDs to their corresponding company IDs
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      // Extract workspace ID from URL like /identity/workspaces/{workspaceId}/platform-company
      const match = url.match(/\/identity\/workspaces\/([^/]+)\/platform-company/);
      if (match) {
        const workspaceId = match[1];
        const companyId = workspaceToCompanyMap.get(workspaceId);

        if (!companyId) {
          // Unknown workspace - return 403
          return {
            status: 403,
            ok: false,
            json: async () => ({}),
          } as any;
        }

        return {
          status: 200,
          ok: true,
          json: async () => ({
            platformCompanyId: companyId,
            membershipRole: "founder",
          }),
        } as any;
      }

      // Default fallback
      return {
        status: 200,
        ok: true,
        json: async () => ({
          platformCompanyId: "1",
          membershipRole: "founder",
        }),
      } as any;
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    workspaceToCompanyMap.clear();
  });

  it("trả workspaceStatus/principalStatus active + rules rỗng khi company chưa cấu hình policy", async () => {
    const res = await registerPlatform({
      email: `policy_snapshot_none_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Snapshot Founder",
      company_name: "Snapshot Co",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const companyId = res.company_id!;
    const workspaceId = `ws_snapshot_none_${Date.now()}`;
    workspaceToCompanyMap.set(workspaceId, companyId);

    const snapshot = await getTenantPolicySnapshotForCaller(userId, workspaceId);
    expect(snapshot.workspaceStatus).toBe("active");
    expect(snapshot.principalStatus).toBe("active");
    expect(snapshot.rules).toEqual([]);
    expect(snapshot.snapshotHash).toBeTruthy();
  });

  it("trả đủ rules đã cấu hình trong snapshot", async () => {
    const res = await registerPlatform({
      email: `policy_snapshot_rules_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Snapshot Rules Founder",
      company_name: "Snapshot Rules Co",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const companyId = res.company_id!;
    const workspaceId = `ws_snapshot_rules_${Date.now()}`;
    workspaceToCompanyMap.set(workspaceId, companyId);

    await setTenantPolicy({ companyId, toolPattern: "finance.*", decision: "REQUIRE_APPROVAL" });
    await setTenantPolicy({ companyId, toolPattern: "commercial.lead.create", decision: "ALLOW" });

    const snapshot = await getTenantPolicySnapshotForCaller(userId, workspaceId);
    expect(snapshot.rules).toHaveLength(2);
    expect(snapshot.rules.map((r) => r.toolPattern).sort()).toEqual(["commercial.lead.create", "finance.*"]);
  });

  it("từ chối nếu caller không phải thành viên của workspaceId được yêu cầu", async () => {
    const resA = await registerPlatform({
      email: `policy_snapshot_iso_a_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Snapshot A Founder",
      company_name: "Snapshot A Co",
    });
    const resB = await registerPlatform({
      email: `policy_snapshot_iso_b_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Snapshot B Founder",
      company_name: "Snapshot B Co",
    });
    const userIdA = verifyPlatformToken(resA.access_token).sub;
    const workspaceIdB = `ws_snapshot_iso_b_${Date.now()}`;

    // Don't register workspaceIdB in the map - this simulates the user not being a member
    // The mock will return 403 for unknown workspaces

    await expect(getTenantPolicySnapshotForCaller(userIdA, workspaceIdB)).rejects.toThrow();
  });

  it("hai snapshot của cùng 1 workspace nhưng khác rule set phải có snapshotHash khác nhau", async () => {
    const res = await registerPlatform({
      email: `policy_snapshot_hash_${Date.now()}@example.com`,
      password: "password123",
      full_name: "Hash Founder",
      company_name: "Hash Co",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const companyId = res.company_id!;
    const workspaceId = `ws_snapshot_hash_${Date.now()}`;
    workspaceToCompanyMap.set(workspaceId, companyId);

    const before = await getTenantPolicySnapshotForCaller(userId, workspaceId);
    await setTenantPolicy({ companyId, toolPattern: "*", decision: "DENY" });
    const after = await getTenantPolicySnapshotForCaller(userId, workspaceId);

    expect(before.snapshotHash).not.toBe(after.snapshotHash);
  });
});
