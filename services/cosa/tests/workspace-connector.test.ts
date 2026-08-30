import { describe, it, expect, beforeEach, beforeAll, afterEach, vi } from "vitest";
import * as connectorSvc from "../services/workspace-connector.service";
import { db, schema } from "../models/db";
import { installConnectorEndpoint, grantConnectorEndpoint, revokeGrantEndpoint } from "../handlers/workspace-connector.handler";
import { signPlatformToken } from "../services/token.service";

const {
  workspaceConnectorInstallations,
  connectorAuthorizations,
  sessionConnectorGrants,
  users,
  companies,
  companyMemberships,
} = schema;

const TEST_USER_ID = 1001n;
const TEST_COMPANY_ID = 2001n;
const TEST_NON_MEMBER_USER_ID = 1002n;

beforeAll(async () => {
  // Clean up test data first
  await db.delete(companyMemberships);
  await db.delete(companies);
  await db.delete(users);

  // Create test user with membership
  await db.insert(users).values({
    id: TEST_USER_ID,
    email: "member@test.com",
    phone: null,
    hashedPassword: "dummy_hash",
    status: "active",
  });

  // Create test company
  await db.insert(companies).values({
    id: TEST_COMPANY_ID,
    slug: "test-company",
    name: "Test Company",
    status: "active",
    createdBy: TEST_USER_ID,
  });

  // Create membership for test user in test company
  await db.insert(companyMemberships).values({
    id: 3001n,
    companyId: TEST_COMPANY_ID,
    userId: TEST_USER_ID,
    roleId: "user",
  });

  // Create non-member user
  await db.insert(users).values({
    id: TEST_NON_MEMBER_USER_ID,
    email: "nonmember@test.com",
    phone: null,
    hashedPassword: "dummy_hash",
    status: "active",
  });
});

beforeEach(async () => {
  await db.delete(sessionConnectorGrants);
  await db.delete(connectorAuthorizations);
  await db.delete(workspaceConnectorInstallations);
});

describe("Workspace Connector Consent & Session Grants (Task 3)", () => {
  beforeEach(() => {
    // Mock fetch for workspace membership verification
    vi.stubGlobal("fetch", vi.fn(async (url: string, opts?: any) => {
      // For workspace membership checks, default to member (200)
      // The non-member test will override this
      return {
        status: 200,
        ok: true,
        json: async () => ({
          platformCompanyId: "1",
          membershipRole: "member",
        }),
      } as any;
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("installs connector and ensures idempotency for duplicate installs", async () => {
    const inst1 = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });
    expect(inst1.id).toBeDefined();
    expect(inst1.status).toBe("enabled");

    const inst2 = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });
    expect(inst2.id).toBe(inst1.id);
  });

  it("rejects unapproved connector keys fail-closed", async () => {
    await expect(
      connectorSvc.installWorkspaceConnector({
        workspaceId: "ws_1",
        connectorKey: "dangerous-desktop-control",
        installedBy: "user_admin",
      })
    ).rejects.toThrow(/not allowed/i);
  });

  it("rejects secret_ref not matching required secret URI format", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        workspaceId: "ws_1",
        principalId: "user_alice",
        secretRef: "raw-access-token-12345",
        grantedScopes: ["read"],
        expiresAt: new Date(Date.now() + 3600000),
      })
    ).rejects.toThrow(/must start with 'secret:\/\/cosa-connectors\/'/i);
  });

  it("registers authorization and does not leak raw credentials in response", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    const auth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId: "ws_1",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/vault-key-abc",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    expect(auth.id).toBeDefined();
    expect(auth.state).toBe("active");
    expect(auth.hasSecret).toBe(true);
    expect((auth as any).secretRef).toBeUndefined();
  });

  it("prevents cross-tenant authorization grants", async () => {
    const instA = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_A",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    const authA = await connectorSvc.registerConnectorAuthorization({
      installationId: instA.id,
      workspaceId: "ws_A",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/vault-key-a",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    // Try granting authA in company_B / ws_B -> reject
    await expect(
      connectorSvc.grantConnectorToSession({
        workspaceId: "ws_B",
        conversationId: "conv_b",
        authorizationId: authA.id,
        grantedBy: "user_bob",
        allowedActions: ["read"],
        callerPrincipalId: "user_bob",
        allowManageOthers: false,
      })
    ).rejects.toThrow(/mismatch/i);
  });

  it("assertConnectorInvocation returns connector_reauth_required when authorization or grant expired", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    // Expired authorization
    const expiredAuth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId: "ws_1",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/vault-key-exp",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() - 1000), // in the past
    });

    // Directly insert grant or bypass check for test
    await db.insert(sessionConnectorGrants).values({
      id: "grant_exp_1",
      workspaceId: "ws_1",
      conversationId: "conv_1",
      authorizationId: expiredAuth.id,
      grantedBy: "user_alice",
      allowedActions: ["read"],
      state: "enabled",
    });

    const assertRes = await connectorSvc.assertConnectorInvocation({
      workspaceId: "ws_1",
      conversationId: "conv_1",
      connectorKey: "sandbox-read",
      requiredScope: "read:data",
    });

    expect(assertRes.ok).toBe(false);
    expect(assertRes.error).toBe("connector_reauth_required");
  });

  it("assertConnectorInvocation succeeds for active grant and correct scope", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    const authorization = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId: "ws_1",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/valid-vault-ref",
      grantedScopes: ["read", "metadata"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    const grant = await connectorSvc.grantConnectorToSession({
      workspaceId: "ws_1",
      conversationId: "conv_active",
      authorizationId: authorization.id,
      grantedBy: "user_alice",
      allowedActions: ["sandbox.read"],
      callerPrincipalId: "user_alice",
      allowManageOthers: false,
    });

    const successAssert = await connectorSvc.assertConnectorInvocation({
      workspaceId: "ws_1",
      conversationId: "conv_active",
      connectorKey: "sandbox-read",
      action: "sandbox.read",
      requiredScope: "read",
    });

    expect(successAssert.ok).toBe(true);
    expect(successAssert.secretRef).toBe("secret://cosa-connectors/valid-vault-ref");
    expect(authorization.grantedScopes).toEqual(["read", "metadata"]);
    expect(grant.allowedActions).toEqual(["sandbox.read"]);
  });

  it("rejects registerConnectorAuthorization when installation belongs to a different company", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: "ws_a",
      connectorKey: "sandbox-read",
      installedBy: "user_a",
    });

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        workspaceId: "ws_b",
        principalId: "user_b",
        secretRef: "secret://cosa-connectors/sandbox-read/b",
        grantedScopes: ["read"],
        expiresAt: new Date(Date.now() + 3600_000),
      })
    ).rejects.toThrow(/not found/i);
  });

  it("rejects installConnectorEndpoint when caller is not a member of workspace", async () => {
    // Override the fetch mock to return 403 (not a member) for this test
    vi.stubGlobal("fetch", vi.fn(async (url: string, opts?: any) => {
      return {
        status: 403,
        ok: false,
        json: async () => ({}),
      } as any;
    }));

    const tokenNonMember = signPlatformToken(TEST_NON_MEMBER_USER_ID.toString());
    await expect(
      installConnectorEndpoint({
        authorization: `Bearer ${tokenNonMember}`,
        workspaceId: "ws_test",
        connectorKey: "sandbox-read",
      })
    ).rejects.toThrow();
  });
});

describe("Task 4: connector authorization ownership enforcement", () => {
  // Principal A ("user_a_task4") tries to manage authorizations owned by principal B
  // ("user_b_task4"). A workspace member relationship (Task 3's check) is not enough:
  // only the owner (or an audited founder/admin override) may grant/revoke.
  const PRINCIPAL_A = "user_a_task4";
  const PRINCIPAL_B = "user_b_task4";
  let currentCallerMembershipRole = "member";

  beforeEach(() => {
    // membershipRole simulates what services/company returns for the *caller* of the
    // current request (verified server-side, not self-declared in the caller's JWT).
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        return {
          status: 200,
          ok: true,
          json: async () => ({
            platformCompanyId: "1",
            membershipRole: currentCallerMembershipRole,
          }),
        } as any;
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    currentCallerMembershipRole = "member";
  });

  async function setupAuthorizationOwnedByB(workspaceId: string) {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId,
      connectorKey: "sandbox-read",
      installedBy: PRINCIPAL_B,
    });
    const auth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId,
      principalId: PRINCIPAL_B,
      secretRef: "secret://cosa-connectors/task4-b-secret",
      grantedScopes: ["read"],
      expiresAt: new Date(Date.now() + 3600000),
    });
    return auth;
  }

  it("rejects grantConnectorEndpoint when a non-owner member (A) grants B's authorization", async () => {
    const auth = await setupAuthorizationOwnedByB("ws_task4_grant_reject");
    currentCallerMembershipRole = "member";
    const tokenA = signPlatformToken(PRINCIPAL_A);

    await expect(
      grantConnectorEndpoint({
        authorization: `Bearer ${tokenA}`,
        workspaceId: "ws_task4_grant_reject",
        conversationId: "conv_task4_grant_reject",
        authorizationId: auth.id,
      })
    ).rejects.toThrow(/authorization owner/i);
  });

  it("allows grantConnectorEndpoint when the owner (B) grants their own authorization", async () => {
    const auth = await setupAuthorizationOwnedByB("ws_task4_grant_owner");
    currentCallerMembershipRole = "member";
    const tokenB = signPlatformToken(PRINCIPAL_B);

    const res = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: "ws_task4_grant_owner",
      conversationId: "conv_task4_grant_owner",
      authorizationId: auth.id,
    });

    expect(res.authorizationId).toBe(auth.id);
  });

  it("allows grantConnectorEndpoint when caller (A) has an audited founder override", async () => {
    const auth = await setupAuthorizationOwnedByB("ws_task4_grant_override");
    currentCallerMembershipRole = "founder";
    const tokenA = signPlatformToken(PRINCIPAL_A);

    const res = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenA}`,
      workspaceId: "ws_task4_grant_override",
      conversationId: "conv_task4_grant_override",
      authorizationId: auth.id,
    });

    expect(res.authorizationId).toBe(auth.id);
  });

  it("rejects revokeGrantEndpoint when a non-owner member (A) revokes B's grant", async () => {
    const auth = await setupAuthorizationOwnedByB("ws_task4_revoke_reject");
    currentCallerMembershipRole = "member";
    const tokenB = signPlatformToken(PRINCIPAL_B);
    const grant = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: "ws_task4_revoke_reject",
      conversationId: "conv_task4_revoke_reject",
      authorizationId: auth.id,
    });

    const tokenA = signPlatformToken(PRINCIPAL_A);
    await expect(
      revokeGrantEndpoint({
        authorization: `Bearer ${tokenA}`,
        workspaceId: "ws_task4_revoke_reject",
        conversationId: "conv_task4_revoke_reject",
        grantId: grant.id,
      })
    ).rejects.toThrow(/authorization owner/i);
  });

  it("allows revokeGrantEndpoint when the owner (B) revokes their own grant", async () => {
    const auth = await setupAuthorizationOwnedByB("ws_task4_revoke_owner");
    currentCallerMembershipRole = "member";
    const tokenB = signPlatformToken(PRINCIPAL_B);
    const grant = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: "ws_task4_revoke_owner",
      conversationId: "conv_task4_revoke_owner",
      authorizationId: auth.id,
    });

    const res = await revokeGrantEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: "ws_task4_revoke_owner",
      conversationId: "conv_task4_revoke_owner",
      grantId: grant.id,
    });

    expect(res.ok).toBe(true);
  });

  it("rejects revokeGrantEndpoint when caller (A) has admin role (not an override role)", async () => {
    // Policy decision (review round 1/5, 2026-08-30): only founder/co-founder override,
    // matching getRolePermissions() in services/company/identity/services/tenant-context.service.ts,
    // which buckets "admin" with "member"/"user" (["read","write"]) rather than full ("*") access.
    const auth = await setupAuthorizationOwnedByB("ws_task4_revoke_override");
    currentCallerMembershipRole = "member";
    const tokenB = signPlatformToken(PRINCIPAL_B);
    const grant = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: "ws_task4_revoke_override",
      conversationId: "conv_task4_revoke_override",
      authorizationId: auth.id,
    });

    currentCallerMembershipRole = "admin";
    const tokenA = signPlatformToken(PRINCIPAL_A);
    await expect(
      revokeGrantEndpoint({
        authorization: `Bearer ${tokenA}`,
        workspaceId: "ws_task4_revoke_override",
        conversationId: "conv_task4_revoke_override",
        grantId: grant.id,
      })
    ).rejects.toThrow(/authorization owner/i);
  });
});
