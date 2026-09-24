import { eq } from "drizzle-orm";
import { describe, it, expect, beforeEach, beforeAll } from "vitest";
import * as connectorSvc from "../services/workspace-connector.service";
import { db, schema } from "../models/db";
import {
  installConnectorEndpoint,
  registerAuthorizationEndpoint,
  grantConnectorEndpoint,
  revokeGrantEndpoint,
} from "../handlers/workspace-connector.handler";
import { setFakeCoreDefaultMembership, signPlatformToken, stableId } from "./support/test-identity";

const {
  workspaceConnectorInstallations,
  connectorAuthorizations,
  sessionConnectorGrants,
  users,
  workspaces,
  workspaceMemberships,
} = schema;

const TEST_USER_ID = 1001n;
const TEST_WORKSPACE_ID = 2001n;
const TEST_NON_MEMBER_USER_ID = 1002n;

beforeAll(async () => {
  // Clean up test data first
  await db.delete(workspaceMemberships);
  await db.delete(workspaces);
  await db.delete(users);

  // Create test user with membership
  await db.insert(users).values({
    id: TEST_USER_ID,
    email: "member@test.com",
    phone: null,
    hashedPassword: "dummy_hash",
    status: "active",
  });

  // Create test workspace
  await db.insert(workspaces).values({
    id: TEST_WORKSPACE_ID,
    workspaceName: "Test Workspace",
    status: "active",
    ownerId: TEST_USER_ID,
  });

  // Create membership for test user in test workspace
  await db.insert(workspaceMemberships).values({
    id: 3001n,
    workspaceId: TEST_WORKSPACE_ID,
    userId: TEST_USER_ID,
    roleId: "member",
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
    // Core (giả): mặc định mọi caller là thành viên (member); test không phải thành viên đặt null.
    setFakeCoreDefaultMembership("member");
  });

  it("installs connector and ensures idempotency for duplicate installs", async () => {
    const inst1 = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });
    expect(inst1.id).toBeDefined();
    expect(inst1.status).toBe("enabled");

    const inst2 = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });
    expect(inst2.id).toBe(inst1.id);
  });

  it("rejects unapproved connector keys fail-closed", async () => {
    await expect(
      connectorSvc.installWorkspaceConnector({
        workspaceId: stableId("ws_1"),
        connectorKey: "dangerous-desktop-control",
        installedBy: stableId("user_admin"),
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects secret_ref not matching required secret URI format", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        workspaceId: stableId("ws_1"),
        principalId: stableId("user_alice"),
        secretRef: "raw-access-token-12345",
        grantedScopes: ["read"],
        expiresAt: new Date(Date.now() + 3600000),
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects invalid ISO timestamp in registerAuthorizationEndpoint", async () => {
    await expect(
      registerAuthorizationEndpoint({
        authorization: `Bearer ${signPlatformToken(TEST_USER_ID.toString())}`,
        workspaceId: stableId("ws_test"),
        installationId: "missing",
        secretRef: "not-a-vault-ref",
        grantedScopes: ["read"],
        expiresAt: "not-an-iso-date",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects invalid ISO timestamp in grantConnectorEndpoint", async () => {
    await expect(
      grantConnectorEndpoint({
        authorization: `Bearer ${signPlatformToken(TEST_USER_ID.toString())}`,
        workspaceId: stableId("ws_test"),
        conversationId: "conversation",
        authorizationId: "authorization",
        expiresAt: "tomorrow-ish",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("registers authorization and does not leak raw credentials in response", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });

    const auth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId: stableId("ws_1"),
      principalId: stableId("user_alice"),
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
      workspaceId: stableId("ws_A"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });

    const authA = await connectorSvc.registerConnectorAuthorization({
      installationId: instA.id,
      workspaceId: stableId("ws_A"),
      principalId: stableId("user_alice"),
      secretRef: "secret://cosa-connectors/vault-key-a",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    // Try granting authA in company_B / ws_B -> reject with not_found
    await expect(
      connectorSvc.grantConnectorToSession({
        workspaceId: stableId("ws_B"),
        conversationId: "conv_b",
        authorizationId: authA.id,
        grantedBy: stableId("user_bob"),
        allowedActions: ["read"],
        callerPrincipalId: stableId("user_bob"),
        allowManageOthers: false,
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects registerConnectorAuthorization when installation is disabled", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });

    await db
      .update(workspaceConnectorInstallations)
      .set({ status: "disabled" })
      .where(eq(workspaceConnectorInstallations.id, inst.id));

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        workspaceId: stableId("ws_1"),
        principalId: stableId("user_alice"),
        secretRef: "secret://cosa-connectors/vault-key-1",
        grantedScopes: ["read"],
        expiresAt: new Date(Date.now() + 3600000),
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("assertConnectorInvocation returns connector_reauth_required when authorization or grant expired", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });

    // Expired authorization
    const expiredAuth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId: stableId("ws_1"),
      principalId: stableId("user_alice"),
      secretRef: "secret://cosa-connectors/vault-key-exp",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() - 1000), // in the past
    });

    // Directly insert grant or bypass check for test
    await db.insert(sessionConnectorGrants).values({
      id: "grant_exp_1",
      workspaceId: stableId("ws_1"),
      conversationId: "conv_1",
      authorizationId: expiredAuth.id,
      grantedBy: stableId("user_alice"),
      allowedActions: ["read"],
      state: "enabled",
    });

    const assertRes = await connectorSvc.assertConnectorInvocation({
      workspaceId: stableId("ws_1"),
      conversationId: "conv_1",
      connectorKey: "sandbox-read",
      requiredScope: "read:data",
    });

    expect(assertRes.ok).toBe(false);
    expect(assertRes.error).toBe("connector_reauth_required");
  });

  it("assertConnectorInvocation succeeds for active grant and correct scope", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      workspaceId: stableId("ws_1"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_admin"),
    });

    const authorization = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      workspaceId: stableId("ws_1"),
      principalId: stableId("user_alice"),
      secretRef: "secret://cosa-connectors/valid-vault-ref",
      grantedScopes: ["read", "metadata"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    const grant = await connectorSvc.grantConnectorToSession({
      workspaceId: stableId("ws_1"),
      conversationId: "conv_active",
      authorizationId: authorization.id,
      grantedBy: stableId("user_alice"),
      allowedActions: ["sandbox.read"],
      callerPrincipalId: stableId("user_alice"),
      allowManageOthers: false,
    });

    const successAssert = await connectorSvc.assertConnectorInvocation({
      workspaceId: stableId("ws_1"),
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
      workspaceId: stableId("ws_a"),
      connectorKey: "sandbox-read",
      installedBy: stableId("user_a"),
    });

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        workspaceId: stableId("ws_b"),
        principalId: stableId("user_b"),
        secretRef: "secret://cosa-connectors/sandbox-read/b",
        grantedScopes: ["read"],
        expiresAt: new Date(Date.now() + 3600_000),
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects installConnectorEndpoint when caller is not a member of workspace", async () => {
    // Core (giả) từ chối: caller không phải thành viên.
    setFakeCoreDefaultMembership(null);

    const tokenNonMember = signPlatformToken(TEST_NON_MEMBER_USER_ID.toString());
    await expect(
      installConnectorEndpoint({
        authorization: `Bearer ${tokenNonMember}`,
        workspaceId: stableId("ws_test"),
        connectorKey: "sandbox-read",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});

describe("Task 4: connector authorization ownership enforcement", () => {
  // Principal A ("user_a_task4") tries to manage authorizations owned by principal B
  // ("user_b_task4"). A workspace member relationship (Task 3's check) is not enough:
  // only the owner (or an audited founder/co-founder override) may grant/revoke.
  const PRINCIPAL_A = stableId("user_a_task4");
  const PRINCIPAL_B = stableId("user_b_task4");
  beforeEach(() => {
    // Role của caller do core (giả) quyết định (không tự khai trong token của caller).
    setFakeCoreDefaultMembership("member");
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
    const auth = await setupAuthorizationOwnedByB(stableId("ws_task4_grant_reject"));
    setFakeCoreDefaultMembership("member");
    const tokenA = signPlatformToken(PRINCIPAL_A);

    await expect(
      grantConnectorEndpoint({
        authorization: `Bearer ${tokenA}`,
        workspaceId: stableId("ws_task4_grant_reject"),
        conversationId: "conv_task4_grant_reject",
        authorizationId: auth.id,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("allows grantConnectorEndpoint when the owner (B) grants their own authorization", async () => {
    const auth = await setupAuthorizationOwnedByB(stableId("ws_task4_grant_owner"));
    setFakeCoreDefaultMembership("member");
    const tokenB = signPlatformToken(PRINCIPAL_B);

    const res = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: stableId("ws_task4_grant_owner"),
      conversationId: "conv_task4_grant_owner",
      authorizationId: auth.id,
    });

    expect(res.authorizationId).toBe(auth.id);
  });

  it("allows grantConnectorEndpoint when caller (A) has an audited founder override", async () => {
    const auth = await setupAuthorizationOwnedByB(stableId("ws_task4_grant_override"));
    setFakeCoreDefaultMembership("founder");
    const tokenA = signPlatformToken(PRINCIPAL_A);

    const res = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenA}`,
      workspaceId: stableId("ws_task4_grant_override"),
      conversationId: "conv_task4_grant_override",
      authorizationId: auth.id,
    });

    expect(res.authorizationId).toBe(auth.id);
  });

  it("rejects revokeGrantEndpoint when a non-owner member (A) revokes B's grant", async () => {
    const auth = await setupAuthorizationOwnedByB(stableId("ws_task4_revoke_reject"));
    setFakeCoreDefaultMembership("member");
    const tokenB = signPlatformToken(PRINCIPAL_B);
    const grant = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: stableId("ws_task4_revoke_reject"),
      conversationId: "conv_task4_revoke_reject",
      authorizationId: auth.id,
    });

    const tokenA = signPlatformToken(PRINCIPAL_A);
    await expect(
      revokeGrantEndpoint({
        authorization: `Bearer ${tokenA}`,
        workspaceId: stableId("ws_task4_revoke_reject"),
        conversationId: "conv_task4_revoke_reject",
        grantId: grant.id,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("allows revokeGrantEndpoint when the owner (B) revokes their own grant", async () => {
    const auth = await setupAuthorizationOwnedByB(stableId("ws_task4_revoke_owner"));
    setFakeCoreDefaultMembership("member");
    const tokenB = signPlatformToken(PRINCIPAL_B);
    const grant = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: stableId("ws_task4_revoke_owner"),
      conversationId: "conv_task4_revoke_owner",
      authorizationId: auth.id,
    });

    const res = await revokeGrantEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: stableId("ws_task4_revoke_owner"),
      conversationId: "conv_task4_revoke_owner",
      grantId: grant.id,
    });

    expect(res.ok).toBe(true);
  });

  it("rejects revokeGrantEndpoint when caller (A) has admin role (not an override role)", async () => {
    // Policy decision (review round 1/5, 2026-08-30): only founder/co-founder override,
    // matching getRolePermissions() in services/company/identity/services/tenant-context.service.ts,
    // which buckets "admin" with "member"/"user" (["read","write"]) rather than full ("*") access.
    const auth = await setupAuthorizationOwnedByB(stableId("ws_task4_revoke_override"));
    setFakeCoreDefaultMembership("member");
    const tokenB = signPlatformToken(PRINCIPAL_B);
    const grant = await grantConnectorEndpoint({
      authorization: `Bearer ${tokenB}`,
      workspaceId: stableId("ws_task4_revoke_override"),
      conversationId: "conv_task4_revoke_override",
      authorizationId: auth.id,
    });

    setFakeCoreDefaultMembership("admin");
    const tokenA = signPlatformToken(PRINCIPAL_A);
    await expect(
      revokeGrantEndpoint({
        authorization: `Bearer ${tokenA}`,
        workspaceId: stableId("ws_task4_revoke_override"),
        conversationId: "conv_task4_revoke_override",
        grantId: grant.id,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
