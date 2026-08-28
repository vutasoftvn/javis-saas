import { describe, expect, it, beforeEach } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementInboxes,
  engagementThreads,
  engagementIdentityReviewItems,
} from "../../../shared/db/schema/customer-engagement";
import { contacts, accounts } from "../../../shared/db/schema/commercial";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { linkThreadIdentity } from "../../services/customer-engagement/channel-identity-sync.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

describe("Channel CRM Identity Sync Service Tests", () => {
  let wsId: bigint;
  let inboxId: bigint;
  let ctx: TenantContext;

  beforeEach(async () => {
    wsId = generateSnowflake();
    inboxId = generateSnowflake();

    ctx = {
      workspaceId: wsId.toString(),
      userId: "user_1",
      membershipRole: "admin",
      permissions: ["*"],
      correlationId: "corr_test_1",
    };

    await db.insert(engagementInboxes).values({
      id: inboxId,
      workspaceId: wsId,
      channelType: "zalo",
      name: "Identity Test Inbox",
      slaPolicy: { firstResponseMinutes: 60 },
    });
  });

  it("should link contact and backfill account when verified email matches exactly", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const accountId = generateSnowflake();
    await db.insert(accounts).values({
      id: accountId,
      workspaceId: wsId,
      name: "Acme Corp",
    });

    const contactId = generateSnowflake();
    await db.insert(contacts).values({
      id: contactId,
      workspaceId: wsId,
      accountId,
      name: "John Doe",
      email: "john.doe@example.com",
      phone: "+84901234567",
    });

    const res = await linkThreadIdentity(
      threadId.toString(),
      { email: "john.doe@example.com", emailVerified: true, phone: "+84901234567" },
      ctx,
      { autoCreateContact: false }
    );

    expect(res.contactId).toBe(contactId.toString());
    expect(res.accountId).toBe(accountId.toString());
    expect(res.created).toBe(false);
    expect(res.reviewItemId).toBeNull();

    // Verify thread in DB updated
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.contactId).toBe(contactId);
    expect(thread.accountId).toBe(accountId);
  });

  it("should create review item and leave thread contact null when matches are ambiguous / conflicting", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    // 2 contacts with same phone number
    const contactId1 = generateSnowflake();
    const contactId2 = generateSnowflake();
    await db.insert(contacts).values([
      { id: contactId1, workspaceId: wsId, name: "Alice 1", phone: "+84988888888" },
      { id: contactId2, workspaceId: wsId, name: "Alice 2", phone: "+84988888888" },
    ]);

    const res = await linkThreadIdentity(
      threadId.toString(),
      { phone: "+84988888888", emailVerified: false },
      ctx,
      { autoCreateContact: false }
    );

    expect(res.contactId).toBeNull();
    expect(res.reviewItemId).toBeDefined();
    expect(res.created).toBe(false);

    // Verify review item created
    const [reviewItem] = await db
      .select()
      .from(engagementIdentityReviewItems)
      .where(eq(engagementIdentityReviewItems.threadId, threadId));
    expect(reviewItem).toBeDefined();
    expect(reviewItem.status).toBe("open");

    // Thread contactId remains null
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.contactId).toBeNull();
  });

  it("should auto-create contact when no match found and autoCreateContact is true without touching other contacts", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const res = await linkThreadIdentity(
      threadId.toString(),
      { phone: "+84911223344", externalUserName: "Nguyen Van A", externalUserRef: "zalo_u_123" },
      ctx,
      { autoCreateContact: true, channelType: "zalo" }
    );

    expect(res.created).toBe(true);
    expect(res.contactId).toBeDefined();
    expect(res.reviewItemId).toBeNull();

    // Verify newly created contact
    const [newContact] = await db
      .select()
      .from(contacts)
      .where(eq(contacts.id, BigInt(res.contactId!)));
    expect(newContact.name).toBe("Nguyen Van A");
    expect(newContact.phone).toBe("+84911223344");
    expect(newContact.source).toBe("engagement:zalo");
    expect(newContact.accountId).toBeNull();

    // Thread linked
    const [thread] = await db
      .select()
      .from(engagementThreads)
      .where(eq(engagementThreads.id, threadId));
    expect(thread.contactId).toBe(BigInt(res.contactId!));
  });

  it("should create review item with no_match reason when no match and autoCreateContact is false", async () => {
    const threadId = generateSnowflake();
    await db.insert(engagementThreads).values({
      id: threadId,
      workspaceId: wsId,
      inboxId,
      status: "open",
      correlationId: `corr_${threadId}`,
    });

    const res = await linkThreadIdentity(
      threadId.toString(),
      { phone: "+84999000111", externalUserName: "Unknown User" },
      ctx,
      { autoCreateContact: false }
    );

    expect(res.created).toBe(false);
    expect(res.contactId).toBeNull();
    expect(res.reviewItemId).toBeDefined();

    const [reviewItem] = await db
      .select()
      .from(engagementIdentityReviewItems)
      .where(eq(engagementIdentityReviewItems.threadId, threadId));
    expect(reviewItem.reason).toBe("no_match");
  });
});
