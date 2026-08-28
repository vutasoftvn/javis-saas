import { ChannelAdapter, DeliveryResult, OutboundCommand, VerifiedInbound } from "./contract";
import { VerificationConfig, verifyHmac } from "./verification";
import { APIError } from "encore.dev/api";

export interface ZaloChannelAdapterOptions {
  secretResolver?: (secretRef: string) => Promise<string>;
  fetchRunner?: (url: string, options: any) => Promise<{ status: number; json: () => Promise<any> }>;
}

export class ZaloChannelAdapter implements ChannelAdapter {
  readonly channelType = "zalo";
  private secretResolver?: (secretRef: string) => Promise<string>;
  private fetchRunner: (url: string, options: any) => Promise<{ status: number; json: () => Promise<any> }>;

  constructor(opts?: ZaloChannelAdapterOptions) {
    this.secretResolver = opts?.secretResolver;
    this.fetchRunner =
      opts?.fetchRunner ||
      (async (url, options) => {
        const resp = await fetch(url, options);
        return {
          status: resp.status,
          json: () => resp.json(),
        };
      });
  }

  peekRoutingKey(rawBody: Buffer, headers: Record<string, string | undefined>): string | null {
    // 1. Header lookup
    for (const [k, v] of Object.entries(headers)) {
      if (k.toLowerCase() === "x-zalo-oa-id" && v) return v;
    }

    // 2. Body inspection
    try {
      const json = JSON.parse(rawBody.toString("utf-8"));
      return json.oa_id || json.recipient?.id || json.app_id || null;
    } catch {
      return null;
    }
  }

  async verifyInbound(
    rawReq: { rawBody: Buffer; headers: Record<string, string | undefined> },
    config?: VerificationConfig
  ): Promise<VerifiedInbound> {
    if (!config) {
      throw APIError.failedPrecondition("missing verification config for zalo inbound");
    }

    let secretKey = "test_zalo_app_secret";
    if (this.secretResolver && config.secretRef) {
      secretKey = await this.secretResolver(config.secretRef);
    } else if (process.env[`CHANNEL_SECRET_${config.secretRef?.toUpperCase()}`]) {
      secretKey = process.env[`CHANNEL_SECRET_${config.secretRef?.toUpperCase()}`]!;
    }

    verifyHmac(rawReq.rawBody, rawReq.headers, config, secretKey);

    let json: any;
    try {
      json = JSON.parse(rawReq.rawBody.toString("utf-8"));
    } catch {
      throw APIError.invalidArgument("invalid json in zalo webhook body");
    }

    const externalMessageId =
      json.message?.msg_id || json.event_id || `zalo_msg_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const senderRef = json.sender?.id || json.user_id_by_app || "";
    const externalConversationRef = senderRef;
    const body = json.message?.text || json.text || "";
    const receivedAt = json.timestamp ? new Date(Number(json.timestamp)) : new Date();

    return {
      externalMessageId,
      senderRef,
      externalConversationRef,
      body,
      receivedAt,
      rawPayload: json,
    };
  }

  async normalizeInbound(v: VerifiedInbound): Promise<{
    body: string;
    senderRef: string;
    externalMessageId: string;
    externalConversationRef: string;
  }> {
    return {
      body: v.body,
      senderRef: v.senderRef,
      externalMessageId: v.externalMessageId,
      externalConversationRef: v.externalConversationRef,
    };
  }

  async sendOutbound(cmd: OutboundCommand, secret: string | null): Promise<DeliveryResult> {
    if (!secret) {
      return {
        status: "failed",
        error: "missing access token for zalo outbound",
        permanent: true,
      };
    }

    const recipientId = cmd.externalConversationRef || cmd.recipientRef;
    if (!recipientId) {
      return {
        status: "failed",
        error: "missing recipient externalConversationRef",
        permanent: true,
      };
    }

    const url = "https://openapi.zalo.me/v2.0/oa/message";
    const payload = {
      recipient: { user_id: recipientId },
      message: { text: cmd.body },
    };

    try {
      const resp = await this.fetchRunner(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          access_token: secret,
        },
        body: JSON.stringify(payload),
      });

      const resData = await resp.json().catch(() => ({}));

      if (resp.status === 200 && (resData.error === 0 || !resData.error)) {
        return {
          status: "sent",
          externalMessageId: resData.data?.message_id || `zmsg_${Date.now()}`,
        };
      }

      // Check if error is permanent (e.g. 401, 403, invalid token error codes in Zalo OA)
      const errCode = resData.error || resp.status;
      const isPermanent =
        resp.status === 401 ||
        resp.status === 403 ||
        errCode === -216 || // Invalid access token
        errCode === -204 || // Access token expired
        errCode === -213; // App is not authorized

      return {
        status: "failed",
        error: resData.message || `Zalo send failed with status ${resp.status} (code ${errCode})`,
        permanent: isPermanent,
      };
    } catch (err: any) {
      return {
        status: "failed",
        error: err.message || "Network exception while calling Zalo API",
        permanent: false,
      };
    }
  }

  async getDeliveryStatus(_externalMessageId: string, _secret?: string | null): Promise<"delivered" | "failed" | "unknown"> {
    return "unknown";
  }

  async resolveExternalIdentity(
    senderRef: string,
    secret?: string | null
  ): Promise<{ name?: string; phone?: string; email?: string }> {
    if (!secret || !senderRef) return {};
    try {
      const url = `https://openapi.zalo.me/v2.0/oa/getprofile?data={"user_id":"${senderRef}"}`;
      const resp = await this.fetchRunner(url, {
        method: "GET",
        headers: { access_token: secret },
      });
      const data = await resp.json().catch(() => ({}));
      if (data.error === 0 && data.data) {
        return {
          name: data.data.display_name,
          phone: data.data.phone,
        };
      }
    } catch {
      // Ignore network errors in identity resolution
    }
    return {};
  }
}
