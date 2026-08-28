import { describe, expect, it, beforeEach } from "vitest";
import {
  assertConnectorGrant,
  setCustomConnectorGrantRunner,
} from "../../services/customer-engagement/connector-grant.client";
import {
  resolveChannelSecret,
  setCustomChannelSecretResolver,
} from "../../services/customer-engagement/channel-secret";

describe("Connector Grant Client & Channel Secret Tests", () => {
  beforeEach(() => {
    setCustomConnectorGrantRunner(null);
    setCustomChannelSecretResolver(null);
  });

  it("should return ok:true and secretRef when control plane asserts grant successfully", async () => {
    setCustomConnectorGrantRunner(async (params) => {
      expect(params.connectorKey).toBe("zalo_oa_main");
      expect(params.action).toBe("send");
      return { ok: true, secretRef: "sec_zalo_oa_vault_ref_1" };
    });

    const res = await assertConnectorGrant({
      workspaceId: "ws_123",
      conversationId: "t_456",
      connectorKey: "zalo_oa_main",
      action: "send",
    });

    expect(res.ok).toBe(true);
    expect(res.secretRef).toBe("sec_zalo_oa_vault_ref_1");
  });

  it("should fail-closed (ok:false) on denied grant or network exception without throwing", async () => {
    // 1. Grant denied
    setCustomConnectorGrantRunner(async () => {
      return { ok: false, secretRef: null };
    });
    const resDenied = await assertConnectorGrant({
      workspaceId: "ws_123",
      conversationId: "t_456",
      connectorKey: "zalo_oa_main",
      action: "send",
    });
    expect(resDenied.ok).toBe(false);
    expect(resDenied.secretRef).toBeNull();

    // 2. Network exception
    setCustomConnectorGrantRunner(async () => {
      throw new Error("Connection refused");
    });
    const resNet = await assertConnectorGrant({
      workspaceId: "ws_123",
      conversationId: "t_456",
      connectorKey: "zalo_oa_main",
      action: "send",
    });
    expect(resNet.ok).toBe(false);
    expect(resNet.secretRef).toBeNull();
  });

  it("should resolve channel secret from secretRef or throw failedPrecondition if not resolvable", async () => {
    // 1. Resolvable via custom / env
    process.env["CHANNEL_SECRET_SEC_ZALO_KEY"] = "token_secret_123456";
    const token = await resolveChannelSecret("sec_zalo_key");
    expect(token).toBe("token_secret_123456");

    // 2. Unresolvable
    await expect(resolveChannelSecret("sec_non_existent_vault_key")).rejects.toThrow(
      /secret not resolvable/i
    );
  });
});
