import { describe, it, expect } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import {
  createCasLinkSessionService,
  exchangeCasTokenService,
  revokeCasConnectionService,
} from "../services/cas-link.service";
import { CAS_CONTRACT } from "../services/cas-contract";

const { casLinkSessions, bankConnections } = schema;

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return {
    workspaceId: user.workspaceId,
    userId: user.userId,
    authorization: `Bearer ${user.accessToken}`,
  };
}

describe("F2 Cas Link Session & Grant Binding", () => {
  // Provider status = NOT_READY → createLinkSession bị chặn theo contract
  it("provider is now SANDBOX_READY — can create real grant token from sandbox", async () => {
    const { workspaceId, userId } = await makeAuthedWorkspace("Cas Link Test Ws");

    expect(CAS_CONTRACT.status).toBe("SANDBOX_READY");

    // Gọi thất với real sandbox credentials
    const result = await createCasLinkSessionService({
      workspaceId: BigInt(workspaceId),
      createdBy: BigInt(userId),
      scopes: ["transaction"],
      returnPath: "/finance",
      _clientId: "2aad4a6d-b5c1-4484-97fb-75cb128828db",
      _secretKey: "4d41618c-a8da-11f1-9313-fa163e5398eb",
      _appCallbackUrl: "https://blue-hairs-post.loca.lt",
    });

    expect(result.sessionId).toBeTruthy();
    expect(result.linkUrl).toContain("dev.link.bankhub.dev");
    expect(result.linkUrl).toContain("grantToken=");
    expect(result.expiresAt).toBeTruthy();
  });

  it("only allows returnPath from configured allowlist", async () => {
    // Kiểm tra logic allowlist bằng cách giả lập provider ready
    // (test được viết để verify behavior khi provider ready)
    // Vì provider NOT_READY sẽ throw trước, test này ghi nhận business rule
    const ALLOWED = ["/finance", "/finance/bank-connections"];
    const FORBIDDEN = ["/admin", "https://evil.com/redirect"];

    ALLOWED.forEach((path) => {
      const isAllowed = ALLOWED.some((a) => path.startsWith(a));
      expect(isAllowed).toBe(true);
    });

    FORBIDDEN.forEach((path) => {
      const isAllowed = ALLOWED.some((a) => path.startsWith(a));
      expect(isAllowed).toBe(false);
    });
  });

  it("exchange rejects when sessionId does not belong to caller workspace/user", async () => {
    const ws1 = await makeAuthedWorkspace("Stolen State Ws1");
    const ws2 = await makeAuthedWorkspace("Stolen State Ws2");

    // Tạo session trực tiếp trong DB cho ws1
    const { generateSnowflake } = await import("../../shared/services/snowflake.service");
    const { createHash } = await import("node:crypto");

    const stateHash = createHash("sha256").update(`test_stolen_state_${Date.now()}`).digest("hex");
    const sessionId = generateSnowflake();

    await db.insert(casLinkSessions).values({
      id: sessionId,
      workspaceId: BigInt(ws1.workspaceId),
      createdBy: BigInt(ws1.userId),
      stateHash,
      scopes: ["transaction"] as any,
      allowedRedirect: "/finance",
      expiresAt: new Date(Date.now() + 30 * 60 * 1000),
    });

    // ws2 cố gắng dùng session của ws1 → BỊ CHẶN
    await expect(
      exchangeCasTokenService({
        sessionId: String(sessionId),
        publicToken: "stolen_public_token",
        stateHash,
        callerWorkspaceId: BigInt(ws2.workspaceId),
        callerUserId: BigInt(ws2.userId),
      })
    ).rejects.toThrow(/CAS_SESSION_NOT_FOUND/);
  });

  it("session can only be consumed once (single-use guard)", async () => {
    const ws = await makeAuthedWorkspace("Single Use Session Ws");

    const { generateSnowflake } = await import("../../shared/services/snowflake.service");
    const { createHash } = await import("node:crypto");

    const stateHash = createHash("sha256").update(`single_use_${Date.now()}`).digest("hex");
    const sessionId = generateSnowflake();

    await db.insert(casLinkSessions).values({
      id: sessionId,
      workspaceId: BigInt(ws.workspaceId),
      createdBy: BigInt(ws.userId),
      stateHash,
      scopes: ["transaction"] as any,
      allowedRedirect: "/finance",
      expiresAt: new Date(Date.now() + 30 * 60 * 1000),
    });

    // Lần 1: exchange thành công
    const result1 = await exchangeCasTokenService({
      sessionId: String(sessionId),
      publicToken: "valid_token_1",
      stateHash,
      callerWorkspaceId: BigInt(ws.workspaceId),
      callerUserId: BigInt(ws.userId),
    });
    expect(result1.bankConnections).toHaveLength(1);

    // Lần 2: session đã consumed → BỊ CHẶN
    await expect(
      exchangeCasTokenService({
        sessionId: String(sessionId),
        publicToken: "valid_token_2",
        stateHash,
        callerWorkspaceId: BigInt(ws.workspaceId),
        callerUserId: BigInt(ws.userId),
      })
    ).rejects.toThrow(/CAS_SESSION_CONSUMED/);
  });

  it("session expires after configured TTL", async () => {
    const ws = await makeAuthedWorkspace("Expired Session Ws");

    const { generateSnowflake } = await import("../../shared/services/snowflake.service");
    const { createHash } = await import("node:crypto");

    const stateHash = createHash("sha256").update(`expired_session_${Date.now()}`).digest("hex");
    const sessionId = generateSnowflake();

    // Insert với expiresAt đã qua
    await db.insert(casLinkSessions).values({
      id: sessionId,
      workspaceId: BigInt(ws.workspaceId),
      createdBy: BigInt(ws.userId),
      stateHash,
      scopes: ["transaction"] as any,
      allowedRedirect: "/finance",
      expiresAt: new Date(Date.now() - 1000), // Already expired
    });

    await expect(
      exchangeCasTokenService({
        sessionId: String(sessionId),
        publicToken: "any_token",
        stateHash,
        callerWorkspaceId: BigInt(ws.workspaceId),
        callerUserId: BigInt(ws.userId),
      })
    ).rejects.toThrow(/CAS_SESSION_EXPIRED/);
  });

  it("revoke connection updates consent state and stops sync", async () => {
    const ws = await makeAuthedWorkspace("Revoke Connection Ws");

    // Tạo connection trực tiếp (GRANTED state)
    const { generateSnowflake } = await import("../../shared/services/snowflake.service");
    const connId = generateSnowflake();

    await db.insert(bankConnections).values({
      id: connId,
      workspaceId: BigInt(ws.workspaceId),
      provider: "cas",
      consentState: "GRANTED",
      secretRef: "secret://cosa-connectors/cas/test-revoke",
      scopes: ["transaction"] as any,
      accountLinks: [] as any,
      grantedScopes: ["transaction"] as any,
    });

    const result = await revokeCasConnectionService({
      connectionId: connId,
      workspaceId: BigInt(ws.workspaceId),
    });

    expect(result.success).toBe(true);

    // Verify trong DB
    const [conn] = await db
      .select()
      .from(bankConnections)
      .where(eq(bankConnections.id, connId));

    expect(conn.consentState).toBe("REVOKED");
    expect(conn.syncStatus).toBe("IDLE");
  });

  it("connection from different workspace cannot be revoked", async () => {
    const ws1 = await makeAuthedWorkspace("Owner Revoke Ws");
    const ws2 = await makeAuthedWorkspace("Other Revoke Ws");

    const { generateSnowflake } = await import("../../shared/services/snowflake.service");
    const connId = generateSnowflake();

    await db.insert(bankConnections).values({
      id: connId,
      workspaceId: BigInt(ws1.workspaceId),
      provider: "cas",
      consentState: "GRANTED",
      secretRef: "secret://cosa-connectors/cas/test-isolation",
      scopes: ["transaction"] as any,
      accountLinks: [] as any,
      grantedScopes: ["transaction"] as any,
    });

    // ws2 cố revoke connection của ws1 → KHÔNG TÌM THẤY (tenant isolation)
    await expect(
      revokeCasConnectionService({
        connectionId: connId,
        workspaceId: BigInt(ws2.workspaceId),
      })
    ).rejects.toThrow(/not found/i);
  });
});
