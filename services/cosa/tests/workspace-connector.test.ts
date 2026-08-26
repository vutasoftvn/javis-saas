import { describe, it, expect, beforeEach } from "vitest";
import * as connectorSvc from "../services/workspace-connector.service";
import { db, schema } from "../models/db";

const {
  workspaceConnectorInstallations,
  connectorAuthorizations,
  sessionConnectorGrants,
} = schema;

beforeEach(async () => {
  await db.delete(sessionConnectorGrants);
  await db.delete(connectorAuthorizations);
  await db.delete(workspaceConnectorInstallations);
});

describe("Workspace Connector Consent & Session Grants (Task 3)", () => {
  it("installs connector and ensures idempotency for duplicate installs", async () => {
    const inst1 = await connectorSvc.installWorkspaceConnector({
      companyId: "company_1",
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });
    expect(inst1.id).toBeDefined();
    expect(inst1.status).toBe("enabled");

    const inst2 = await connectorSvc.installWorkspaceConnector({
      companyId: "company_1",
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });
    expect(inst2.id).toBe(inst1.id);
  });

  it("rejects unapproved connector keys fail-closed", async () => {
    await expect(
      connectorSvc.installWorkspaceConnector({
        companyId: "company_1",
        workspaceId: "ws_1",
        connectorKey: "dangerous-desktop-control",
        installedBy: "user_admin",
      })
    ).rejects.toThrow(/not allowed/i);
  });

  it("rejects secret_ref not matching required secret URI format", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      companyId: "company_1",
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        companyId: "company_1",
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
      companyId: "company_1",
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    const auth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      companyId: "company_1",
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
      companyId: "company_A",
      workspaceId: "ws_A",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    const authA = await connectorSvc.registerConnectorAuthorization({
      installationId: instA.id,
      companyId: "company_A",
      workspaceId: "ws_A",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/vault-key-a",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    // Try granting authA in company_B / ws_B -> reject
    await expect(
      connectorSvc.grantConnectorToSession({
        companyId: "company_B",
        workspaceId: "ws_B",
        conversationId: "conv_b",
        authorizationId: authA.id,
        grantedBy: "user_bob",
        allowedActions: ["read"],
      })
    ).rejects.toThrow(/mismatch/i);
  });

  it("assertConnectorInvocation returns connector_reauth_required when authorization or grant expired", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      companyId: "company_1",
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    // Expired authorization
    const expiredAuth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      companyId: "company_1",
      workspaceId: "ws_1",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/vault-key-exp",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() - 1000), // in the past
    });

    // Directly insert grant or bypass check for test
    await db.insert(sessionConnectorGrants).values({
      id: "grant_exp_1",
      companyId: "company_1",
      workspaceId: "ws_1",
      conversationId: "conv_1",
      authorizationId: expiredAuth.id,
      grantedBy: "user_alice",
      allowedActions: ["read"],
      state: "enabled",
    });

    const assertRes = await connectorSvc.assertConnectorInvocation({
      companyId: "company_1",
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
      companyId: "company_1",
      workspaceId: "ws_1",
      connectorKey: "sandbox-read",
      installedBy: "user_admin",
    });

    const auth = await connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      companyId: "company_1",
      workspaceId: "ws_1",
      principalId: "user_alice",
      secretRef: "secret://cosa-connectors/valid-vault-ref",
      grantedScopes: ["read:data"],
      expiresAt: new Date(Date.now() + 3600000),
    });

    await connectorSvc.grantConnectorToSession({
      companyId: "company_1",
      workspaceId: "ws_1",
      conversationId: "conv_active",
      authorizationId: auth.id,
      grantedBy: "user_alice",
      allowedActions: ["fetch_records"],
    });

    const successAssert = await connectorSvc.assertConnectorInvocation({
      companyId: "company_1",
      workspaceId: "ws_1",
      conversationId: "conv_active",
      connectorKey: "sandbox-read",
      action: "fetch_records",
      requiredScope: "read:data",
    });

    expect(successAssert.ok).toBe(true);
    expect(successAssert.secretRef).toBe("secret://cosa-connectors/valid-vault-ref");
  });

  it("rejects registerConnectorAuthorization when installation belongs to a different company", async () => {
    const inst = await connectorSvc.installWorkspaceConnector({
      companyId: "company_a",
      workspaceId: "ws_a",
      connectorKey: "sandbox-read",
      installedBy: "user_a",
    });

    await expect(
      connectorSvc.registerConnectorAuthorization({
        installationId: inst.id,
        companyId: "company_b",
        workspaceId: "ws_b",
        principalId: "user_b",
        secretRef: "secret://cosa-connectors/sandbox-read/b",
        grantedScopes: ["read"],
        expiresAt: new Date(Date.now() + 3600_000),
      })
    ).rejects.toThrow(/not found/i);
  });
});
