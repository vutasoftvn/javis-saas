import { ChannelAdapter, DeliveryResult, OutboundCommand, VerifiedInbound } from "./contract";

export class ApiChannelAdapter implements ChannelAdapter {
  readonly channelType = "api";

  async verifyInbound(
    rawReq: { rawBody: Buffer; headers: Record<string, string | undefined> },
    _config?: any
  ): Promise<VerifiedInbound> {
    let parsed: any = {};
    try {
      parsed = JSON.parse(rawReq.rawBody.toString("utf-8"));
    } catch {
      parsed = {};
    }

    return {
      externalMessageId: parsed.externalMessageId || `api_msg_${Date.now()}`,
      senderRef: parsed.senderRef || "api_user",
      externalConversationRef: parsed.externalConversationRef || "api_thread",
      body: parsed.body || "",
      receivedAt: parsed.receivedAt ? new Date(parsed.receivedAt) : new Date(),
      rawPayload: parsed,
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

  async sendOutbound(cmd: OutboundCommand, _secret: string | null): Promise<DeliveryResult> {
    return {
      status: "sent",
      externalMessageId: `api_${cmd.deliveryId}`,
    };
  }

  async getDeliveryStatus(_externalMessageId: string, _secret?: string | null): Promise<"delivered" | "failed" | "unknown"> {
    return "delivered";
  }

  async resolveExternalIdentity(_senderRef: string, _secret?: string | null): Promise<{ name?: string; phone?: string; email?: string }> {
    return {};
  }

  peekRoutingKey(_rawBody: Buffer, _headers: Record<string, string | undefined>): string | null {
    return "api_default";
  }
}
