import { beforeAll, describe, expect, it } from "vitest";
import { registerPlatformUser } from "../services/auth.service";
import { provisionVentureWorkspace } from "../services/venture-workspace.service";
import { signPlatformToken, signWorkerServiceToken } from "../services/token.service";
import {
  installWorkspaceConnector,
  listWorkspaceAuditEvents,
  listWorkspaceConnectors,
  listWorkspaceMembers,
  listWorkspaceRuntimeNodes,
  revokeWorkspaceConnector,
} from "../handlers/workspace-settings.handler";

describe("Workspace Settings Endpoints", () => {
  let userId: string;
  let workspaceId: string;
  let validToken: string;

  beforeAll(async () => {
    const email = `settings-user-${Date.now()}@test.io`;
    const reg = await registerPlatformUser({
      email,
      password: "SecurePassword123",
      workspace_name: "Settings Test Venture",
    });
    userId = reg.user.id;
    workspaceId = reg.platform_workspace_id!;
    validToken = reg.access_token;
  });

  it("lists workspace members truthfully", async () => {
    const res = await listWorkspaceMembers({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(res.meta.dataState).toBe("populated");
    expect(res.data.length).toBeGreaterThanOrEqual(1);
    expect(res.data[0].roleId).toBe("founder");
  });

  it("handles connector installation, list and revocation without exposing secrets", async () => {
    // 1. Initially connectors list is empty
    const initList = await listWorkspaceConnectors({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(initList.data).toEqual([]);
    expect(initList.meta.dataState).toBe("empty");

    // 2. Install connector
    const installRes = await installWorkspaceConnector({
      workspaceId,
      connectorKey: "google-drive",
      authorization: `Bearer ${validToken}`,
    });
    expect(installRes.data.connectorKey).toBe("google-drive");
    expect(installRes.data.state).toBe("enabled");
    expect(JSON.stringify(installRes)).not.toContain("secret");

    // 3. List connectors shows installed
    const listAfter = await listWorkspaceConnectors({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(listAfter.data.length).toBe(1);
    expect(listAfter.data[0].connectorKey).toBe("google-drive");

    // 4. Revoke connector
    const revokeRes = await revokeWorkspaceConnector({
      workspaceId,
      connectorKey: "google-drive",
      authorization: `Bearer ${validToken}`,
    });
    expect(revokeRes.data.state).toBe("revoked");

    // 5. Audit events recorded installation and revocation
    const auditRes = await listWorkspaceAuditEvents({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(auditRes.data.length).toBeGreaterThanOrEqual(2);
    expect(auditRes.data[0].targetKind).toBe("connector");
  });

  it("lists runtime nodes truthfully", async () => {
    const res = await listWorkspaceRuntimeNodes({
      workspaceId,
      authorization: `Bearer ${validToken}`,
    });
    expect(res.data).toBeDefined();
    expect(res.meta.sources[0].kind).toBe("control_plane");
  });

  it("rejects worker token on human settings route", async () => {
    const workerToken = signWorkerServiceToken("worker_1", workspaceId);
    await expect(
      listWorkspaceMembers({
        workspaceId,
        authorization: `Bearer ${workerToken}`,
      })
    ).rejects.toThrow(/invalid or expired platform token|unauthenticated/i);
  });
});
