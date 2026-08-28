import { describe, expect, it, beforeEach } from "vitest";
import crypto from "node:crypto";
import { ZaloChannelAdapter } from "../../services/customer-engagement/channel-adapters/zalo-channel.adapter";
import {
  verifyHmac,
  VerificationConfig,
} from "../../services/customer-engagement/channel-adapters/verification";

describe("ZaloChannelAdapter & Verification Tests", () => {
  const secretKey = "test_zalo_app_secret";
  const verificationConfig: VerificationConfig = {
    scheme: "hmac_sha256",
    secretRef: "sec_zalo_1",
    header: "X-Zalo-Signature",
    encoding: "hex",
    signedPayload: "raw",
    skewSeconds: 300,
  };

  const samplePayload = JSON.stringify({
    app_id: "oa_12345",
    sender: { id: "user_999" },
    recipient: { id: "oa_12345" },
    event_name: "user_send_text",
    message: {
      msg_id: "zmsg_1001",
      text: "Xin chào shop!",
    },
    timestamp: Date.now().toString(),
  });
  const rawBody = Buffer.from(samplePayload, "utf-8");

  function computeSignature(payload: Buffer, key: string, encoding: "hex" | "base64" = "hex"): string {
    return crypto.createHmac("sha256", key).update(payload).digest(encoding);
  }

  it("should verify valid inbound HMAC signature and extract normalized inbound message", async () => {
    const signature = computeSignature(rawBody, secretKey);
    const headers = { "x-zalo-signature": `mac=${signature}` };

    const adapter = new ZaloChannelAdapter({
      secretResolver: async () => secretKey,
    });

    const verified = await adapter.verifyInbound({ rawBody, headers }, verificationConfig);
    expect(verified.externalMessageId).toBe("zmsg_1001");
    expect(verified.senderRef).toBe("user_999");
    expect(verified.externalConversationRef).toBe("user_999");
    expect(verified.body).toBe("Xin chào shop!");

    const normalized = await adapter.normalizeInbound(verified);
    expect(normalized.body).toBe("Xin chào shop!");
  });

  it("should throw unauthenticated error on tampered body or invalid signature", async () => {
    const signature = computeSignature(rawBody, secretKey);
    const tamperedBody = Buffer.from(samplePayload.replace("Xin chào", "Tampered"), "utf-8");
    const headers = { "x-zalo-signature": `mac=${signature}` };

    const adapter = new ZaloChannelAdapter({
      secretResolver: async () => secretKey,
    });

    await expect(
      adapter.verifyInbound({ rawBody: tamperedBody, headers }, verificationConfig)
    ).rejects.toThrow(/invalid channel signature/i);
  });

  it("should classify outbound response errors into permanent vs retryable", async () => {
    const adapter = new ZaloChannelAdapter({
      // Mock fetch runner for outbound
      fetchRunner: async (url, options) => {
        const body = JSON.parse(options.body as string);
        if (options.headers["access_token"] === "invalid_token") {
          return { status: 401, json: async () => ({ error: -216, message: "Invalid Access Token" }) };
        }
        if (body.message?.text === "RATE_LIMIT") {
          return { status: 429, json: async () => ({ error: -32, message: "Quota exceeded / rate limited" }) };
        }
        return { status: 200, json: async () => ({ error: 0, message: "Success", data: { message_id: "zmsg_out_777" } }) };
      },
    });

    // 1. Happy path: sent
    const resHappy = await adapter.sendOutbound(
      { deliveryId: "del_1", threadId: "t_1", body: "Hello", externalConversationRef: "user_999" },
      "valid_token"
    );
    expect(resHappy.status).toBe("sent");
    if (resHappy.status === "sent") {
      expect(resHappy.externalMessageId).toBe("zmsg_out_777");
    }

    // 2. Permanent error (401 invalid token)
    const resPerm = await adapter.sendOutbound(
      { deliveryId: "del_2", threadId: "t_1", body: "Hello", externalConversationRef: "user_999" },
      "invalid_token"
    );
    expect(resPerm.status).toBe("failed");
    if (resPerm.status === "failed") {
      expect(resPerm.permanent).toBe(true);
    }

    // 3. Transient error (429 rate limit)
    const resRetry = await adapter.sendOutbound(
      { deliveryId: "del_3", threadId: "t_1", body: "RATE_LIMIT", externalConversationRef: "user_999" },
      "valid_token"
    );
    expect(resRetry.status).toBe("failed");
    if (resRetry.status === "failed") {
      expect(resRetry.permanent).toBe(false);
    }
  });
});
