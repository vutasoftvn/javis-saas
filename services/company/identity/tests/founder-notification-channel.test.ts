// Task 2 (B1) / ADR-FOUNDER-CHANNEL-001 — test cho kênh nhận thông báo của
// founder. KHÔNG gọi mạng thật: adapter Telegram và secret resolver đều bị
// tiêm test double qua `setCustomFounderChannelAdapter` /
// `setCustomFounderChannelSecretResolver`, reset lại ở `afterEach`.
import { afterEach, describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db, schema } from "../models/db";
import { identityWorkforceMembers, identityUserProjections } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  createFounderNotificationChannel,
  verifyFounderNotificationChannel,
  revokeFounderNotificationChannel,
  listFounderNotificationChannels,
  resolveUsableChannelForFounder,
} from "../services/founder-notification-channel.service";
import {
  setCustomFounderChannelAdapter,
  type FounderChannelAdapter,
  type FounderChannelSendResult,
} from "../services/telegram-channel-adapter";
import {
  FOUNDER_CHANNEL_SECRET_NAMESPACE,
  setCustomFounderChannelSecretResolver,
} from "../services/founder-channel-secret";

const { founderNotificationChannels } = schema;

function makeMockAdapter(result: FounderChannelSendResult): FounderChannelAdapter {
  return {
    sendVerificationProbe: async () => result,
    sendMessage: async () => result,
  };
}

async function seedWorkspaceWithTwoFounders() {
  const ws = await createTestWorkspaceWithMember({ role: "founder" });
  const wsId = BigInt(ws.workspaceId);

  const founderAMemberId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: founderAMemberId,
    workspaceId: wsId,
    memberType: "HUMAN",
    humanUserId: BigInt(ws.userId),
    roleTitle: "Founder",
    status: "active",
  });

  const founderBUserId = generateSnowflake();
  await db.insert(identityUserProjections).values({
    id: founderBUserId,
    email: `founder-b-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Founder B",
  });
  const founderBMemberId = generateSnowflake();
  await db.insert(identityWorkforceMembers).values({
    id: founderBMemberId,
    workspaceId: wsId,
    memberType: "HUMAN",
    humanUserId: founderBUserId,
    roleTitle: "Co-Founder",
    status: "active",
  });

  const founderACtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: ws.userId,
    workforceMemberId: founderAMemberId.toString(),
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "founder-a-notif-test",
  };

  const founderBCtx: TenantContext = {
    workspaceId: ws.workspaceId,
    userId: founderBUserId.toString(),
    workforceMemberId: founderBMemberId.toString(),
    membershipRole: "co-founder",
    permissions: ["*"],
    correlationId: "founder-b-notif-test",
  };

  return {
    workspaceId: ws.workspaceId,
    founderACtx,
    founderBCtx,
    founderAMemberId: founderAMemberId.toString(),
    founderBMemberId: founderBMemberId.toString(),
  };
}

async function getErrorCode(promise: Promise<unknown>): Promise<string | undefined> {
  try {
    await promise;
    return undefined;
  } catch (err) {
    return (err as { code?: string }).code;
  }
}

describe("founder notification channels (B1)", () => {
  afterEach(() => {
    setCustomFounderChannelAdapter(null);
    setCustomFounderChannelSecretResolver(null);
  });

  it("kênh mới tạo chưa xác minh -> resolveUsableChannelForFounder coi như không có kênh dùng được", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    const { founderACtx, workspaceId, founderAMemberId } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
      label: "My phone",
    });

    expect(created.data.verified).toBe(false);
    expect(created.data.verifiedAt).toBeNull();

    await expect(
      resolveUsableChannelForFounder(workspaceId, founderAMemberId, "telegram")
    ).rejects.toThrow(/founder_channel_unavailable/);
  });

  it("xác minh thành công -> verifiedAt được set, kênh dùng được", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    setCustomFounderChannelAdapter(makeMockAdapter({ ok: true }));
    const { founderACtx, workspaceId, founderAMemberId } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });

    const verified = await verifyFounderNotificationChannel(founderACtx, created.data.id);
    expect(verified.data.verified).toBe(true);
    expect(verified.data.verifiedAt).not.toBeNull();

    const usable = await resolveUsableChannelForFounder(workspaceId, founderAMemberId, "telegram");
    expect(usable.id.toString()).toBe(created.data.id);
  });

  it("xác minh thất bại -> vẫn chưa xác minh, lỗi failedPrecondition nêu rõ reason", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    setCustomFounderChannelAdapter(makeMockAdapter({ ok: false, reason: "chat not found" }));
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "bad-chat-id",
    });

    await expect(verifyFounderNotificationChannel(founderACtx, created.data.id)).rejects.toThrow(
      /chat not found/
    );

    const list = await listFounderNotificationChannels(founderACtx);
    const row = list.data.find((c) => c.id === created.data.id);
    expect(row?.verified).toBe(false);
  });

  it("revoke kênh đã xác minh -> resolveUsableChannelForFounder sau đó trả founder_channel_unavailable", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    setCustomFounderChannelAdapter(makeMockAdapter({ ok: true }));
    const { founderACtx, workspaceId, founderAMemberId } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });
    await verifyFounderNotificationChannel(founderACtx, created.data.id);

    // Vẫn dùng được trước khi revoke.
    await resolveUsableChannelForFounder(workspaceId, founderAMemberId, "telegram");

    await revokeFounderNotificationChannel(founderACtx, created.data.id);

    await expect(
      resolveUsableChannelForFounder(workspaceId, founderAMemberId, "telegram")
    ).rejects.toThrow(/founder_channel_unavailable/);
  });

  it("founder khác không revoke/verify được kênh không phải của mình (mã lỗi not_found)", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    setCustomFounderChannelAdapter(makeMockAdapter({ ok: true }));
    const { founderACtx, founderBCtx } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });

    // Fix review #6 — khẳng định đúng mã lỗi machine-readable (`not_found`),
    // không chỉ `rejects.toThrow()` trống (test đó có thể pass ngay cả khi
    // lỗi là một 500 không liên quan).
    expect(await getErrorCode(verifyFounderNotificationChannel(founderBCtx, created.data.id))).toBe(
      "not_found"
    );
    expect(await getErrorCode(revokeFounderNotificationChannel(founderBCtx, created.data.id))).toBe(
      "not_found"
    );

    // Founder A vẫn thao tác được bình thường trên kênh của chính mình.
    const verified = await verifyFounderNotificationChannel(founderACtx, created.data.id);
    expect(verified.data.verified).toBe(true);
  });

  it("GET không trả secretRef trong response JSON", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
      label: "My phone",
    });

    const [row] = await db
      .select()
      .from(founderNotificationChannels)
      .where(eq(founderNotificationChannels.id, BigInt(created.data.id)));
    const secretRef = row.secretRef;

    const list = await listFounderNotificationChannels(founderACtx);
    expect(list.data).toHaveLength(1);

    const serialized = JSON.stringify(list);
    expect(serialized).not.toContain(secretRef);
    expect(serialized).not.toContain("secretRef");
    expect(serialized).not.toContain("123456789");
    expect((list.data[0] as any).secretRef).toBeUndefined();
    expect((list.data[0] as any).chatId).toBeUndefined();
    expect(list.data[0].chatIdMasked).toBe("***6789");
  });

  it("từ chối kind chưa hỗ trợ", async () => {
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    await expect(
      createFounderNotificationChannel(founderACtx, {
        // @ts-expect-error kind không hợp lệ dùng để test validate
        kind: "zalo",
        chatId: "123456789",
      })
    ).rejects.toThrow();
  });

  it("Fix review #1 — secretRef luôn do server sinh, không nhận qua input, không trỏ được tới kênh khác", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });

    // Input không còn field secretRef (lỗi biên dịch nếu ai đó thêm lại field
    // này mà không cập nhật test). Kiểm tra thật trong DB: secretRef được
    // server sinh đúng namespace + kind + đúng id vừa tạo, founder không thể
    // truyền secretRef tuỳ ý để trỏ sang kênh của người khác.
    const [row] = await db
      .select()
      .from(founderNotificationChannels)
      .where(eq(founderNotificationChannels.id, BigInt(created.data.id)));

    expect(row.secretRef).toBe(`${FOUNDER_CHANNEL_SECRET_NAMESPACE}telegram/${created.data.id}`);
  });

  it("Fix review #2 — tạo kênh khi đã có kênh cùng kind chưa thu hồi -> alreadyExists, không phải lỗi 500 thô", async () => {
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });

    const code = await getErrorCode(
      createFounderNotificationChannel(founderACtx, {
        kind: "telegram",
        chatId: "987654321",
      })
    );
    expect(code).toBe("already_exists");
  });

  it("Fix review #3 — verify/revoke kênh đã thu hồi trả failedPrecondition, không âm thầm thành công", async () => {
    setCustomFounderChannelSecretResolver(async () => "fake-bot-token");
    setCustomFounderChannelAdapter(makeMockAdapter({ ok: true }));
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });
    await revokeFounderNotificationChannel(founderACtx, created.data.id);

    await expect(verifyFounderNotificationChannel(founderACtx, created.data.id)).rejects.toThrow(
      /founder_channel_revoked/
    );
    await expect(revokeFounderNotificationChannel(founderACtx, created.data.id)).rejects.toThrow(
      /founder_channel_revoked/
    );
  });

  it("Fix review #4 — channelId không phải số nguyên hợp lệ -> invalidArgument", async () => {
    const { founderACtx } = await seedWorkspaceWithTwoFounders();

    expect(await getErrorCode(verifyFounderNotificationChannel(founderACtx, "not-a-number"))).toBe(
      "invalid_argument"
    );
    expect(await getErrorCode(revokeFounderNotificationChannel(founderACtx, "abc123"))).toBe(
      "invalid_argument"
    );
  });

  it("Fix review #5 — lỗi secret không resolve được không lộ secretRef trong message", async () => {
    // Không set resolver custom -> rơi về nhánh env lookup, luôn miss trong test -> throw.
    const { founderACtx } = await seedWorkspaceWithTwoFounders();
    setCustomFounderChannelAdapter(makeMockAdapter({ ok: true }));

    const created = await createFounderNotificationChannel(founderACtx, {
      kind: "telegram",
      chatId: "123456789",
    });

    const [row] = await db
      .select()
      .from(founderNotificationChannels)
      .where(eq(founderNotificationChannels.id, BigInt(created.data.id)));

    let message = "";
    try {
      await verifyFounderNotificationChannel(founderACtx, created.data.id);
    } catch (err) {
      message = (err as Error).message;
    }
    expect(message).not.toContain(row.secretRef);
    expect(message).not.toContain(FOUNDER_CHANNEL_SECRET_NAMESPACE);
  });
});
