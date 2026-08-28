export type DeliveryResult =
  | { status: "sent"; externalMessageId: string }
  | { status: "failed"; error: string; permanent: boolean }
  | { status: "unknown" };

export interface OutboundCommand {
  deliveryId: string;
  threadId: string;
  body: string;
  externalConversationRef?: string | null;
  endpointProviderRef?: string | null;
  recipientRef?: string | null;
  [key: string]: any;
}

export interface VerifiedInbound {
  externalMessageId: string;
  senderRef: string;
  externalConversationRef: string;
  body: string;
  receivedAt: Date;
  rawPayload?: any;
}

export interface ChannelAdapter {
  readonly channelType: string;
  verifyInbound(
    rawReq: { rawBody: Buffer; headers: Record<string, string | undefined> },
    config?: any
  ): Promise<VerifiedInbound>;
  normalizeInbound(v: VerifiedInbound): Promise<{
    body: string;
    senderRef: string;
    externalMessageId: string;
    externalConversationRef: string;
  }>;
  sendOutbound(cmd: OutboundCommand, secret: string | null): Promise<DeliveryResult>;
  getDeliveryStatus(externalMessageId: string, secret?: string | null): Promise<"delivered" | "failed" | "unknown">;
  resolveExternalIdentity(
    senderRef: string,
    secret?: string | null
  ): Promise<{ name?: string; phone?: string; email?: string }>;
  peekRoutingKey?(
    rawBody: Buffer,
    headers: Record<string, string | undefined>
  ): string | null;
}
