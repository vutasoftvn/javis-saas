import jwt from "jsonwebtoken";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { registerPlatform } from "../handlers/auth.handler";
import { getMyTenantPolicySnapshot, getTenantPolicy, setTenantPolicy } from "../handlers/agent-policy.handler";
import { getTenantPolicySnapshotForCaller } from "../services/agent-policy.service";
import { verifyPlatformToken } from "../services/token.service";

const TEST_CONTROL_DELEGATION_SECRET = "test-control-delegation-secret-min-32-chars";

function signControlDelegation(opts: { sub: string; workspaceId: string; role?: string }): string {
  // Claim JWT thô là workspace_id (snake_case) — cùng convention với
  // mint_control_plane_delegation (apps/cosa/auth/jwt.py) qua wire thật.
  return jwt.sign(
    { sub: opts.sub, workspace_id: opts.workspaceId, role: opts.role ?? "member" },
    process.env.COSA_CONTROL_DELEGATION_SECRET || TEST_CONTROL_DELEGATION_SECRET,
    { audience: "cosa_control", issuer: "cosa_apps", expiresIn: "10m" }
  );
}

describe("Agent Policy (TenantPolicy, roadmap Phase 10a)", () => {
  it("returns no decision when a workspace has not configured any policy", async () => {
    const res = await registerPlatform({
      email: `policy_none_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "No Policy Founder",
      workspace_name: "No Policy WS",
    });

    const result = await getTenantPolicy({ workspaceId: res.platform_workspace_id!, toolName: "commercial.lead.create" });
    expect(result.decision).toBeNull();
  });

  it("returns exact tool match decision over wildcard", async () => {
    const res = await registerPlatform({
      email: `policy_exact_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Exact Policy Founder",
      workspace_name: "Exact Policy WS",
    });
    const workspaceId = res.platform_workspace_id!;

    await setTenantPolicy({ workspaceId, toolPattern: "*", decision: "ALLOW" });
    await setTenantPolicy({
      workspaceId,
      toolPattern: "commercial.notification.slack_send",
      decision: "DENY",
      reason: "Workspace policy blocks all outbound Slack messages",
    });

    const exactResult = await getTenantPolicy({ workspaceId, toolName: "commercial.notification.slack_send" });
    expect(exactResult.decision).toBe("DENY");
    expect(exactResult.matchedPattern).toBe("commercial.notification.slack_send");
    expect(exactResult.reason).toContain("Slack");

    const wildcardResult = await getTenantPolicy({ workspaceId, toolName: "commercial.lead.create" });
    expect(wildcardResult.decision).toBe("ALLOW");
    expect(wildcardResult.matchedPattern).toBe("*");
  });

  it("matches prefix wildcard patterns like 'finance.*'", async () => {
    const res = await registerPlatform({
      email: `policy_prefix_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Prefix Policy Founder",
      workspace_name: "Prefix Policy WS",
    });
    const workspaceId = res.platform_workspace_id!;

    await setTenantPolicy({ workspaceId, toolPattern: "finance.*", decision: "REQUIRE_APPROVAL" });

    const result = await getTenantPolicy({ workspaceId, toolName: "finance.transfer.funds" });
    expect(result.decision).toBe("REQUIRE_APPROVAL");
    expect(result.matchedPattern).toBe("finance.*");
  });

  it("upsert overwrites an existing rule for the same workspace + tool_pattern", async () => {
    const res = await registerPlatform({
      email: `policy_upsert_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Upsert Policy Founder",
      workspace_name: "Upsert Policy WS",
    });
    const workspaceId = res.platform_workspace_id!;

    await setTenantPolicy({ workspaceId, toolPattern: "ops.deploy.prod", decision: "ALLOW" });
    await setTenantPolicy({ workspaceId, toolPattern: "ops.deploy.prod", decision: "DENY", reason: "frozen" });

    const result = await getTenantPolicy({ workspaceId, toolName: "ops.deploy.prod" });
    expect(result.decision).toBe("DENY");
    expect(result.reason).toBe("frozen");
  });

  it("isolates policy rules per workspace (no cross-tenant leakage)", async () => {
    const resA = await registerPlatform({
      email: `policy_iso_a_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Workspace A Founder",
      workspace_name: "Workspace A",
    });
    const resB = await registerPlatform({
      email: `policy_iso_b_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Workspace B Founder",
      workspace_name: "Workspace B",
    });

    await setTenantPolicy({ workspaceId: resA.platform_workspace_id!, toolPattern: "*", decision: "DENY" });

    const resultA = await getTenantPolicy({ workspaceId: resA.platform_workspace_id!, toolName: "commercial.lead.create" });
    const resultB = await getTenantPolicy({ workspaceId: resB.platform_workspace_id!, toolName: "commercial.lead.create" });

    expect(resultA.decision).toBe("DENY");
    expect(resultB.decision).toBeNull();
  });
});

describe("getTenantPolicySnapshotForCaller", () => {
  const allowedWorkspaces = new Set<string>();

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      const match = url.match(/\/identity\/workspaces\/([^/]+)\/platform-company/);
      if (match) {
        const workspaceId = match[1];
        if (!allowedWorkspaces.has(workspaceId)) {
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
            platformCompanyId: workspaceId,
            membershipRole: "founder",
          }),
        } as any;
      }

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
    allowedWorkspaces.clear();
  });

  it("trả workspaceStatus/principalStatus active + rules rỗng khi workspace chưa cấu hình policy", async () => {
    const res = await registerPlatform({
      email: `policy_snapshot_none_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Snapshot Founder",
      workspace_name: "Snapshot WS",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const workspaceId = res.platform_workspace_id!;
    allowedWorkspaces.add(workspaceId);

    const snapshot = await getTenantPolicySnapshotForCaller(userId, workspaceId);
    expect(snapshot.workspaceStatus).toBe("active");
    expect(snapshot.principalStatus).toBe("active");
    expect(snapshot.rules).toEqual([]);
    expect(snapshot.snapshotHash).toBeTruthy();
  });

  it("trả đủ rules đã cấu hình trong snapshot", async () => {
    const res = await registerPlatform({
      email: `policy_snapshot_rules_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Snapshot Rules Founder",
      workspace_name: "Snapshot Rules WS",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const workspaceId = res.platform_workspace_id!;
    allowedWorkspaces.add(workspaceId);

    await setTenantPolicy({ workspaceId, toolPattern: "finance.*", decision: "REQUIRE_APPROVAL" });
    await setTenantPolicy({ workspaceId, toolPattern: "commercial.lead.create", decision: "ALLOW" });

    const snapshot = await getTenantPolicySnapshotForCaller(userId, workspaceId);
    expect(snapshot.rules).toHaveLength(2);
    expect(snapshot.rules.map((r) => r.toolPattern).sort()).toEqual(["commercial.lead.create", "finance.*"]);
  });

  it("từ chối nếu caller không phải thành viên của workspaceId được yêu cầu", async () => {
    const resA = await registerPlatform({
      email: `policy_snapshot_iso_a_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Snapshot A Founder",
      workspace_name: "Snapshot A WS",
    });
    const resB = await registerPlatform({
      email: `policy_snapshot_iso_b_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Snapshot B Founder",
      workspace_name: "Snapshot B WS",
    });
    const userIdA = verifyPlatformToken(resA.access_token).sub;
    const workspaceIdB = resB.platform_workspace_id!;

    await expect(getTenantPolicySnapshotForCaller(userIdA, workspaceIdB)).rejects.toThrow();
  });

  it("hai snapshot của cùng 1 workspace nhưng khác rule set phải có snapshotHash khác nhau", async () => {
    const res = await registerPlatform({
      email: `policy_snapshot_hash_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Hash Founder",
      workspace_name: "Hash WS",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const workspaceId = res.platform_workspace_id!;
    allowedWorkspaces.add(workspaceId);

    const before = await getTenantPolicySnapshotForCaller(userId, workspaceId);
    await setTenantPolicy({ workspaceId, toolPattern: "*", decision: "DENY" });
    const after = await getTenantPolicySnapshotForCaller(userId, workspaceId);

    expect(before.snapshotHash).not.toBe(after.snapshotHash);
  });
});

describe("getMyTenantPolicySnapshot handler — B5 control-plane delegation", () => {
  const originalSecret = process.env.COSA_CONTROL_DELEGATION_SECRET;

  beforeEach(() => {
    process.env.COSA_CONTROL_DELEGATION_SECRET = TEST_CONTROL_DELEGATION_SECRET;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    process.env.COSA_CONTROL_DELEGATION_SECRET = originalSecret;
  });

  it("trả snapshot đúng qua delegation, KHÔNG round-trip sang services/company (B5 fix)", async () => {
    const res = await registerPlatform({
      email: `policy_delegation_ok_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Delegation Founder",
      workspace_name: "Delegation WS",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const workspaceId = res.platform_workspace_id!;
    await setTenantPolicy({ workspaceId, toolPattern: "finance.*", decision: "REQUIRE_APPROVAL" });

    // Bằng chứng KHÔNG round-trip: fetch bị stub để throw nếu gọi tới — trước
    // B5 fix, đường verifyWorkspaceMembership LUÔN gọi fetch sang
    // services/company (và luôn fail vì khác secret). Đường delegation phải
    // build snapshot mà không đụng tới fetch.
    const fetchSpy = vi.fn(() => {
      throw new Error("must not call services/company when using control-plane delegation");
    });
    vi.stubGlobal("fetch", fetchSpy);

    const delegation = signControlDelegation({ sub: userId, workspaceId });
    const snapshot = await getMyTenantPolicySnapshot({
      workspaceId,
      authorization: `Bearer ${delegation}`,
    });

    expect(snapshot.workspaceId).toBe(workspaceId);
    expect(snapshot.rules).toHaveLength(1);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("từ chối delegation token scoped cho workspace khác (permission_denied)", async () => {
    const res = await registerPlatform({
      email: `policy_delegation_scope_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Delegation Scope Founder",
      workspace_name: "Delegation Scope WS",
    });
    const userId = verifyPlatformToken(res.access_token).sub;
    const workspaceId = res.platform_workspace_id!;

    const delegation = signControlDelegation({ sub: userId, workspaceId: "some_other_workspace" });

    await expect(
      getMyTenantPolicySnapshot({ workspaceId, authorization: `Bearer ${delegation}` })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("delegation ký sai secret KHÔNG được chấp nhận (fallback platform token vẫn phải qua verify thật)", async () => {
    const res = await registerPlatform({
      email: `policy_delegation_badsig_${Date.now()}@example.com`,
      password: "password1234",
      full_name: "Bad Sig Founder",
      workspace_name: "Bad Sig WS",
    });
    const workspaceId = res.platform_workspace_id!;

    const forged = jwt.sign(
      { sub: verifyPlatformToken(res.access_token).sub, workspace_id: workspaceId, role: "founder" },
      "wrong-secret-not-the-real-one-min-32-chars",
      { audience: "cosa_control", issuer: "cosa_apps", expiresIn: "10m" }
    );

    // Sai secret -> verifyControlDelegationToken fail -> fallback sang
    // verifyPlatformToken(token thô, KHÔNG phải platform token thật) -> 401.
    await expect(
      getMyTenantPolicySnapshot({ workspaceId, authorization: `Bearer ${forged}` })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });
});

