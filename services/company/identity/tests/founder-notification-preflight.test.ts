// B5 (Task 6b, plan hub vận hành đợt 2) / ADR-FOUNDER-CHANNEL-001 mục 8 —
// `GET /identity/founder-notifications/preflight`. Cùng guard/logic kiểm founder + tra
// kênh với `send` (Task 3), nhưng KHÔNG gửi gì — worker gọi TRƯỚC khi tạo conversation/gọi
// model. Typed `api()` handler nên vitest trần gọi thẳng hàm.
import { afterEach, describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db, schema } from "../models/db";
import { identityWorkforceMembers, identityUserProjections, identityWorkspaceMemberships } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import { founderNotificationPreflightApi } from "../handlers/founder-notification-preflight.handler";
import {
  setCustomFounderChannelAdapter,
  type FounderChannelAdapter,
} from "../services/telegram-channel-adapter";
import {
  FOUNDER_CHANNEL_SECRET_NAMESPACE,
  setCustomFounderChannelSecretResolver,
} from "../services/founder-channel-secret";

const { founderNotificationChannels } = schema;

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
    run_id: "run-founder-notify-preflight-1",
    capability_ids: capabilityIds,
  })}`;
}

function preflightAs(
  founder: SeededFounder,
  channelKind?: string,
  caps: string[] = [AGENT_CAP.FOUNDER_NOTIFY_SEND]
) {
  return founderNotificationPreflightApi({
    authorization: delegationFor(founder, caps),
    workspaceId: founder.workspaceId,
    channelKind,
  });
}

describe("GET /identity/founder-notifications/preflight (B5 Task 6b)", () => {
  afterEach(() => {
    setCustomFounderChannelAdapter(null);
    setCustomFounderChannelSecretResolver(null);
  });

  it("ok:true với đúng một kênh dùng được, không đọc secret/gọi adapter", async () => {
    let adapterCalled = false;
    const adapter: FounderChannelAdapter = {
      sendVerificationProbe: async () => ({ ok: true }),
      sendMessage: async () => {
        adapterCalled = true;
        return { ok: true };
      },
    };
    setCustomFounderChannelAdapter(adapter);
    let secretResolved = false;
    setCustomFounderChannelSecretResolver(async (ref) => {
      secretResolved = true;
      return `token:${ref}`;
    });

    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "-100999", label: "Ops" });

    const res = await preflightAs(founder);

    expect(res).toEqual({ ok: true, channelKind: "telegram", channelLabel: "Ops" });
    expect(adapterCalled).toBe(false);
    expect(secretResolved).toBe(false);
  });

  it("channelKind rỗng -> nhãn tên loại kênh mặc định", async () => {
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "555", label: null });

    const res = await preflightAs(founder);

    expect(res).toEqual({ ok: true, channelKind: "telegram", channelLabel: "Telegram" });
  });

  it("founder_channel_unavailable: chưa có kênh nào xác minh", async () => {
    const founder = await seedFounder();

    await expect(preflightAs(founder)).rejects.toMatchObject({
      message: expect.stringContaining("founder_channel_unavailable:"),
    });
  });

  it("founder_channel_unavailable: kênh duy nhất đã bị thu hồi", async () => {
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "1", revoked: true });

    await expect(preflightAs(founder)).rejects.toMatchObject({
      message: expect.stringContaining("founder_channel_unavailable:"),
    });
  });

  it("founder_owner_not_authorized: role không phải founder/co-founder", async () => {
    const founder = await seedFounder("member");
    await insertChannel(founder, { chatId: "1" });

    await expect(preflightAs(founder)).rejects.toMatchObject({
      message: expect.stringContaining("founder_owner_not_authorized:"),
    });
  });

  // `founder_channel_ambiguous` (`resolveUsableChannelForFounder`, B1: `!kind && usable.length
  // > 1`) không tái tạo được bằng DB thật ở thời điểm này — `SUPPORTED_KINDS` chỉ có
  // "telegram" và bảng có unique constraint `(workspace_id, founder_member_id, kind)` (chỉ 1
  // kênh active/kind/founder), nên KHÔNG thể chèn 2 kênh cùng kind cùng usable. Cùng tình
  // trạng với bộ test Task 3 (`founder-notification-send.test.ts`, không có case này) — nhánh
  // này chỉ sống lại khi thêm kind thứ 2. Worker (`scheduled_tasks.py`) vẫn map đúng tiền tố
  // message này sang `failed` — đã khoá bằng test Python (khớp chuỗi, không cần DB thật).

  it("founder A không thấy được kênh của co-founder B (mỗi founder chỉ preflight kênh của chính mình)", async () => {
    const founderA = await seedFounder();
    const founderB = await addCoFounder(founderA.workspaceId);
    await insertChannel(founderB, { chatId: "b-channel" });

    await expect(preflightAs(founderA)).rejects.toMatchObject({
      message: expect.stringContaining("founder_channel_unavailable:"),
    });

    const resB = await preflightAs(founderB);
    expect(resB.channelKind).toBe("telegram");
  });

  it("delegation thiếu capability founder.notify.send -> permission_denied", async () => {
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "1" });

    await expect(preflightAs(founder, undefined, ["some.other.capability"])).rejects.toMatchObject(
      { code: "permission_denied" }
    );
  });

  it("thiếu Authorization -> unauthenticated", async () => {
    await expect(
      founderNotificationPreflightApi({ workspaceId: "1" } as never)
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("channelKind không hỗ trợ -> invalid_argument", async () => {
    const founder = await seedFounder();
    await insertChannel(founder, { chatId: "1" });

    await expect(preflightAs(founder, "sms")).rejects.toMatchObject({
      message: expect.stringContaining("founder_notify_invalid_payload:"),
    });
  });
});
