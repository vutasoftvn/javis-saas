// Task 3 (B2) / ADR-FOUNDER-CHANNEL-001 Decision 4-7 — capability
// `founder.notify.send`. Endpoint `POST /identity/founder-notifications/send`
// (api.raw, expose:true) nhận delegation của agent mang capability
// `founder.notify.send`; founder sở hữu run = danh tính trong delegation.
// KHÔNG gọi mạng thật: adapter Telegram và secret resolver bị tiêm test double
// qua setter của Task 2, reset ở `afterEach`.
import { Readable } from "node:stream";
import type { IncomingMessage, ServerResponse } from "node:http";
import { afterEach, describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db, schema } from "../models/db";
import { identityWorkforceMembers, identityUserProjections, identityWorkspaceMemberships } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import type { TenantContext } from "../../shared/types/tenant_context";
import { sendFounderNotificationApi } from "../handlers/founder-notification-send.handler";
import { sendFounderNotification } from "../services/founder-notification-send.service";
import {
  setCustomFounderChannelAdapter,
  TelegramBotApiAdapter,
  type FounderChannelAdapter,
  type FounderChannelSendResult,
} from "../services/telegram-channel-adapter";
import {
  FOUNDER_CHANNEL_SECRET_NAMESPACE,
  setCustomFounderChannelSecretResolver,
} from "../services/founder-channel-secret";

const { founderNotificationChannels } = schema;

interface SentMessage {
  chatId: string;
  token: string;
  content: string;
}

function recordingAdapter(result: FounderChannelSendResult | Error = { ok: true }) {
  const sent: SentMessage[] = [];
  const adapter: FounderChannelAdapter = {
    sendVerificationProbe: async () => ({ ok: true }),
    sendMessage: async (chatId, token, content) => {
      sent.push({ chatId, token, content });
      if (result instanceof Error) throw result;
      return result;
    },
  };
  return { adapter, sent };
}

/** Bot token giả theo secretRef, để khẳng định adapter nhận đúng token của kênh. */
function tokenFor(secretRef: string): string {
  return `bot-token-for:${secretRef}`;
}

interface SeededFounder {
  workspaceId: string;
  userId: string;
  memberId: string;
}

async function addHumanMember(
  workspaceId: string,
  userId: bigint,
  roleTitle: string,
  status = "active"
): Promise<string> {
  const memberId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: memberId,
    workspaceId: BigInt(workspaceId),
    memberType: "HUMAN",
    humanUserId: userId,
    roleTitle,
    status,
  });
  return memberId.toString();
}

async function seedFounder(role = "founder"): Promise<SeededFounder> {
  const ws = await createTestWorkspaceWithMember({ role });
  const memberId = await addHumanMember(ws.workspaceId, BigInt(ws.userId), role);
  return { workspaceId: ws.workspaceId, userId: ws.userId, memberId };
}

/** Thêm co-founder thứ hai (user + membership + workforce member) vào cùng workspace. */
async function addCoFounder(workspaceId: string): Promise<SeededFounder> {
  const userId = generateSnowflake();
  await db.insert(identityUserProjections).values({
    id: userId,
    email: `cofounder-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Co-Founder B",
  });
  await db.insert(identityWorkspaceMemberships).values({
    id: generateSnowflake(),
    workspaceId: BigInt(workspaceId),
    userId,
    role: "co-founder",
  });
  const memberId = await addHumanMember(workspaceId, userId, "Co-Founder");
  return { workspaceId, userId: userId.toString(), memberId };
}

async function insertChannel(
  founder: SeededFounder,
  opts: { chatId: string; verified?: boolean; revoked?: boolean; label?: string | null }
): Promise<typeof founderNotificationChannels.$inferSelect> {
  const id = generateSnowflake();
  const [row] = await db
    .insert(founderNotificationChannels)
    .values({
      id,
      workspaceId: BigInt(founder.workspaceId),
      founderMemberId: BigInt(founder.memberId),
      kind: "telegram",
      secretRef: `${FOUNDER_CHANNEL_SECRET_NAMESPACE}telegram/${id.toString()}`,
      chatId: opts.chatId,
      label: opts.label === undefined ? "Nhóm của tôi" : opts.label,
      verifiedAt: opts.verified === false ? null : new Date("2026-09-27T01:00:00Z"),
      revokedAt: opts.revoked ? new Date("2026-09-27T02:00:00Z") : null,
    })
    .returning();
  return row;
}

function delegationFor(founder: SeededFounder, capabilityIds: string[], workspaceId?: string): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${founder.userId}`,
    workspace_id: workspaceId ?? founder.workspaceId,
    run_id: "run-founder-notify-1",
    capability_ids: capabilityIds,
  })}`;
}

interface RawCallResult {
  status: number;
  body: Record<string, unknown>;
  text: string;
}

/** Gọi đúng raw handler đã đăng ký với Encore bằng req/resp giả (vitest trần không chạy runtime). */
async function callSend(opts: {
  authorization?: string;
  workspaceId?: string;
  body: unknown;
}): Promise<RawCallResult> {
  const rawBody = typeof opts.body === "string" ? opts.body : JSON.stringify(opts.body);
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (opts.authorization) headers.authorization = opts.authorization;
  if (opts.workspaceId) headers["x-workspace-id"] = opts.workspaceId;
  const req = Object.assign(Readable.from([Buffer.from(rawBody)]), { headers, method: "POST" });

  let text = "";
  const resp = {
    statusCode: 200,
    headers: {} as Record<string, string>,
    setHeader(name: string, value: string) {
      this.headers[name.toLowerCase()] = value;
    },
    end(chunk?: string) {
      text = chunk ?? "";
    },
  };
  await sendFounderNotificationApi(req as unknown as IncomingMessage, resp as unknown as ServerResponse);
  return { status: resp.statusCode, body: text ? JSON.parse(text) : {}, text };
}

function sendAs(founder: SeededFounder, body: unknown, caps: string[] = [AGENT_CAP.FOUNDER_NOTIFY_SEND]) {
  return callSend({
    authorization: delegationFor(founder, caps),
    workspaceId: founder.workspaceId,
    body,
  });
}

describe("founder.notify.send (B2)", () => {
  afterEach(() => {
    setCustomFounderChannelAdapter(null);
    setCustomFounderChannelSecretResolver(null);
  });

  it("gửi thành công: adapter nhận đúng chatId/token kênh của founder, response không lộ chatId/secret", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    const channel = await insertChannel(founder, { chatId: "-100987654321" });

    const res = await sendAs(founder, { content: "  Tóm tắt email hôm nay  ", channelKind: "telegram" });

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ delivered: true, channelKind: "telegram", channelLabel: "Nhóm của tôi" });
    expect(sent).toEqual([
      { chatId: "-100987654321", token: tokenFor(channel.secretRef), content: "Tóm tắt email hôm nay" },
    ]);
    expect(res.text).not.toContain("987654321");
    expect(res.text).not.toContain(channel.secretRef);
    expect(res.text).not.toContain("bot-token-for");
  });

  it("bỏ channelKind: founder có đúng một kênh dùng được -> gửi vào kênh đó; nhãn rỗng -> tên loại kênh", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "555", label: null });

    const res = await sendAs(founder, { content: "Xin chào" });

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ delivered: true, channelKind: "telegram", channelLabel: "Telegram" });
    expect(sent.map((m) => m.chatId)).toEqual(["555"]);
  });

  it.each(["chat_id", "chatId", "recipient", "channelId", "channel_id", "founderMemberId", "workspaceId"])(
    "payload có field lạ `%s` -> invalid_argument, không gửi gì",
    async (field) => {
      setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
      const { adapter, sent } = recordingAdapter();
      setCustomFounderChannelAdapter(adapter);
      const founder = await seedFounder();
      await insertChannel(founder, { chatId: "111" });

      const res = await sendAs(founder, { content: "Xin chào", [field]: "999" });

      expect(res.status).toBe(400);
      expect(res.body.code).toBe("invalid_argument");
      expect(String(res.body.message)).toContain(field);
      expect(sent).toEqual([]);
    }
  );

  it.each([
    ["content rỗng sau trim", { content: "   " }],
    ["thiếu content", { channelKind: "telegram" }],
    ["content không phải string", { content: 42 }],
    ["content quá 4000 ký tự", { content: "a".repeat(4001) }],
    ["channelKind không hỗ trợ", { content: "x", channelKind: "sms" }],
    ["channelKind null", { content: "x", channelKind: null }],
    ["body là mảng", [{ content: "x" }]],
    ["body không phải JSON", "{content: x"],
  ])("%s -> invalid_argument", async (_name, body) => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "111" });

    const res = await sendAs(founder, body);

    expect(res.status).toBe(400);
    expect(res.body.code).toBe("invalid_argument");
    expect(sent).toEqual([]);
  });

  it("content đúng 4000 ký tự (kể cả emoji) vẫn gửi được", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "111" });

    const res = await sendAs(founder, { content: "😀".repeat(4000) });

    expect(res.status).toBe(200);
    expect(sent).toHaveLength(1);
  });

  it("kênh chưa xác minh -> founder_channel_unavailable", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "111", verified: false });

    const res = await sendAs(founder, { content: "Xin chào" });

    expect(res.status).toBe(400);
    expect(res.body.code).toBe("failed_precondition");
    expect(String(res.body.message)).toMatch(/^founder_channel_unavailable:/);
    expect(sent).toEqual([]);
  });

  it("kênh đã thu hồi -> founder_channel_unavailable", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "111", revoked: true });

    const res = await sendAs(founder, { content: "Xin chào", channelKind: "telegram" });

    expect(res.status).toBe(400);
    expect(String(res.body.message)).toMatch(/^founder_channel_unavailable:/);
    expect(sent).toEqual([]);
  });

  it("role không phải founder/co-founder -> founder_owner_not_authorized", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const member = await seedFounder("member");
    await insertChannel(member, { chatId: "111" });

    const res = await sendAs(member, { content: "Xin chào" });

    expect(res.status).toBe(403);
    expect(res.body.code).toBe("permission_denied");
    expect(String(res.body.message)).toMatch(/^founder_owner_not_authorized:/);
    expect(sent).toEqual([]);
  });

  it("workforce member của founder không còn active -> founder_owner_not_authorized", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "111" });
    await db
      .update(identityWorkforceMembers)
      .set({ status: "inactive" })
      .where(eq(identityWorkforceMembers.id, BigInt(founder.memberId)));

    const res = await sendAs(founder, { content: "Xin chào" });

    expect(res.status).toBe(403);
    expect(String(res.body.message)).toMatch(/^founder_owner_not_authorized:/);
    expect(sent).toEqual([]);
  });

  it("delegation thiếu workforceMemberId (user không có workforce member) -> founder_owner_not_authorized", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const res = await callSend({
      authorization: delegationFor(
        { workspaceId: ws.workspaceId, userId: ws.userId, memberId: "0" },
        [AGENT_CAP.FOUNDER_NOTIFY_SEND]
      ),
      workspaceId: ws.workspaceId,
      body: { content: "Xin chào" },
    });

    expect(res.status).toBe(403);
    expect(String(res.body.message)).toMatch(/^founder_owner_not_authorized:/);
  });

  it("service trực tiếp: ctx không có workforceMemberId hoặc role sai -> founder_owner_not_authorized", async () => {
    const founder = await seedFounder();
    const base: TenantContext = {
      workspaceId: founder.workspaceId,
      userId: founder.userId,
      workforceMemberId: founder.memberId,
      membershipRole: "founder",
      permissions: ["*"],
      correlationId: "b2-direct",
    };
    await expect(
      sendFounderNotification({ ...base, workforceMemberId: undefined }, { content: "x" })
    ).rejects.toMatchObject({ code: "permission_denied", message: expect.stringMatching(/^founder_owner_not_authorized:/) });
    await expect(
      sendFounderNotification({ ...base, membershipRole: "auditor" }, { content: "x" })
    ).rejects.toMatchObject({ code: "permission_denied", message: expect.stringMatching(/^founder_owner_not_authorized:/) });
    // Gọi thẳng service cũng không lách được allowlist bằng cách ép kiểu.
    await expect(
      sendFounderNotification(base, { content: "x", chat_id: "999" } as unknown as { content: string })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("founder A không gửi được vào kênh của founder B", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founderA = await seedFounder();
    const founderB = await addCoFounder(founderA.workspaceId);
    await insertChannel(founderB, { chatId: "chat-of-B" });

    // A chưa có kênh: không được "mượn" kênh đã xác minh của B.
    const denied = await sendAs(founderA, { content: "Xin chào" });
    expect(denied.status).toBe(400);
    expect(String(denied.body.message)).toMatch(/^founder_channel_unavailable:/);
    expect(sent).toEqual([]);

    // A có kênh riêng: tin đi đúng kênh của A, không bao giờ tới B.
    await insertChannel(founderA, { chatId: "chat-of-A" });
    const ok = await sendAs(founderA, { content: "Xin chào" });
    expect(ok.status).toBe(200);
    expect(sent.map((m) => m.chatId)).toEqual(["chat-of-A"]);

    // B (co-founder) gửi qua delegation của chính B thì vào kênh của B.
    const okB = await sendAs(founderB, { content: "Chào B" });
    expect(okB.status).toBe(200);
    expect(sent.map((m) => m.chatId)).toEqual(["chat-of-A", "chat-of-B"]);
  });

  it("adapter trả lỗi -> unavailable (thử lại được), verifiedAt không đổi", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter } = recordingAdapter({ ok: false, reason: "Bad Request: chat not found" });
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    const channel = await insertChannel(founder, { chatId: "111" });

    const res = await sendAs(founder, { content: "Xin chào" });

    expect(res.status).toBe(503);
    expect(res.body.code).toBe("unavailable");
    expect(String(res.body.message)).toMatch(/^founder_channel_delivery_failed:/);
    const [after] = await db
      .select()
      .from(founderNotificationChannels)
      .where(eq(founderNotificationChannels.id, channel.id));
    expect(after.verifiedAt?.toISOString()).toBe(channel.verifiedAt?.toISOString());
    expect(after.revokedAt).toBeNull();
  });

  it("adapter ném lỗi (timeout/mạng) -> unavailable, verifiedAt không đổi", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter } = recordingAdapter(new Error("The operation was aborted due to timeout"));
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    const channel = await insertChannel(founder, { chatId: "111" });

    const res = await sendAs(founder, { content: "Xin chào" });

    expect(res.status).toBe(503);
    expect(res.body.code).toBe("unavailable");
    const [after] = await db
      .select()
      .from(founderNotificationChannels)
      .where(eq(founderNotificationChannels.id, channel.id));
    expect(after.verifiedAt?.toISOString()).toBe(channel.verifiedAt?.toISOString());
  });

  it("delegation thiếu capability founder.notify.send -> permission_denied", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "111" });

    const res = await sendAs(founder, { content: "Xin chào" }, [AGENT_CAP.OKR_OBJECTIVE_LIST]);

    expect(res.status).toBe(403);
    expect(res.body.code).toBe("permission_denied");
    expect(sent).toEqual([]);
  });

  it("delegation của workspace khác / thiếu Authorization -> bị từ chối", async () => {
    setCustomFounderChannelSecretResolver(async (ref) => tokenFor(ref));
    const { adapter, sent } = recordingAdapter();
    setCustomFounderChannelAdapter(adapter);
    const founder = await seedFounder();
    const other = await seedFounder();
    await insertChannel(founder, { chatId: "111" });

    const crossWs = await callSend({
      authorization: delegationFor(founder, [AGENT_CAP.FOUNDER_NOTIFY_SEND], other.workspaceId),
      workspaceId: founder.workspaceId,
      body: { content: "Xin chào" },
    });
    expect(crossWs.status).toBe(403);

    const noAuth = await callSend({ workspaceId: founder.workspaceId, body: { content: "Xin chào" } });
    expect(noAuth.status).toBe(401);
    expect(noAuth.body.code).toBe("unauthenticated");
    expect(sent).toEqual([]);
  });
});

describe("TelegramBotApiAdapter timeout", () => {
  it("fetch treo quá timeout -> {ok:false}, không treo request", async () => {
    const realFetch = globalThis.fetch;
    globalThis.fetch = ((_url: string, init?: RequestInit) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(init.signal?.reason ?? new Error("aborted")));
      })) as typeof fetch;
    try {
      const result = await new TelegramBotApiAdapter({ timeoutMs: 20 }).sendMessage("1", "t", "x");
      expect(result.ok).toBe(false);
    } finally {
      globalThis.fetch = realFetch;
    }
  });
});
