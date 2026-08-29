import { describe, expect, it } from "vitest";
import { eq, and } from "drizzle-orm";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveContact } from "../../services/customer-engagement/identity-resolution.service";

async function ws(name: string) {
  const u = await createTestSession({
    email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`,
    displayName: name,
  });
  const ctx = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);
  return { ctx, workspaceId: u.workspaceId };
}

describe("identity-resolution.service", () => {
  it("branch 1: verified email, single clean match → returns contactId, no review item", async () => {
    const a = await ws("res-verified-single");
    const workspaceId = BigInt(a.workspaceId);
    const threadId = String(generateSnowflake());

    // Seed contact with email
    const contactId = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values({
      id: contactId,
      workspaceId,
      name: "Test Contact",
      email: "unique@example.com",
      doNotContact: false,
    });

    const result = await resolveContact(
      { email: "unique@example.com", emailVerified: true },
      threadId,
      a.ctx
    );

    expect(result.contactId).toBe(String(contactId));
    expect(result.reviewItemId).toBeNull();

    // Verify no review item was created for this thread
    const reviews = await db
      .select()
      .from(schema.engagementIdentityReviewItems)
      .where(eq(schema.engagementIdentityReviewItems.threadId, BigInt(threadId)));
    expect(reviews).toHaveLength(0);
  });

  it("branch 1: verified email, multiple matching contacts (different case) → creates multiple_candidates review item", async () => {
    const a = await ws("res-verified-multiple-case");
    const workspaceId = BigInt(a.workspaceId);
    const threadId = String(generateSnowflake());

    // Seed two contacts with same email but different case.
    // The unique constraint is on the raw email string, but our query uses lower() for comparison.
    // So "Dana@Acme.com" and "dana@acme.com" are two distinct rows.
    const contact1Id = BigInt(generateSnowflake());
    const contact2Id = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values([
      {
        id: contact1Id,
        workspaceId,
        name: "Dana First",
        email: "Dana@Acme.com",
        doNotContact: false,
      },
      {
        id: contact2Id,
        workspaceId,
        name: "Dana Second",
        email: "dana@acme.com",
        doNotContact: false,
      },
    ]);

    // Query with different case, should match both
    const result = await resolveContact(
      { email: "DANA@acme.com", emailVerified: true },
      threadId,
      a.ctx
    );

    expect(result.contactId).toBeNull();
    expect(result.reviewItemId).toBeTruthy();

    // Verify review item was created with correct reason and both candidates
    const reviews = await db
      .select()
      .from(schema.engagementIdentityReviewItems)
      .where(eq(schema.engagementIdentityReviewItems.threadId, BigInt(threadId)));
    expect(reviews).toHaveLength(1);
    expect(reviews[0].reason).toBe("multiple_candidates");
    expect((reviews[0].candidateRefs as any[]).length).toBe(2);
    const candidateIds = (reviews[0].candidateRefs as any[]).map((c: any) => c.contactId).sort();
    expect(candidateIds).toContain(String(contact1Id));
    expect(candidateIds).toContain(String(contact2Id));
  });

  it("branch 1: verified email, matched contact has doNotContact=true → creates do_not_contact review item", async () => {
    const a = await ws("res-do-not-contact");
    const workspaceId = BigInt(a.workspaceId);
    const threadId = String(generateSnowflake());

    // Seed contact with doNotContact flag
    const contactId = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values({
      id: contactId,
      workspaceId,
      name: "Do Not Contact",
      email: "dnc@example.com",
      doNotContact: true,
    });

    const result = await resolveContact(
      { email: "dnc@example.com", emailVerified: true },
      threadId,
      a.ctx
    );

    expect(result.contactId).toBeNull();
    expect(result.reviewItemId).toBeTruthy();

    const reviews = await db
      .select()
      .from(schema.engagementIdentityReviewItems)
      .where(eq(schema.engagementIdentityReviewItems.threadId, BigInt(threadId)));
    expect(reviews).toHaveLength(1);
    expect(reviews[0].reason).toBe("do_not_contact");
  });

  it("branch 4: unverified email → creates unverified review item", async () => {
    const a = await ws("res-unverified");
    const workspaceId = BigInt(a.workspaceId);
    const threadId = String(generateSnowflake());

    const result = await resolveContact(
      { email: "unverified@example.com", emailVerified: false },
      threadId,
      a.ctx
    );

    expect(result.contactId).toBeNull();
    expect(result.reviewItemId).toBeTruthy();

    const reviews = await db
      .select()
      .from(schema.engagementIdentityReviewItems)
      .where(eq(schema.engagementIdentityReviewItems.threadId, BigInt(threadId)));
    expect(reviews).toHaveLength(1);
    expect(reviews[0].reason).toBe("unverified");
  });

  it("branch 3: phone matches contacts under multiple accounts → creates account_conflict review item", async () => {
    const a = await ws("res-account-conflict");
    const workspaceId = BigInt(a.workspaceId);
    const threadId = String(generateSnowflake());

    // Seed two accounts
    const account1Id = BigInt(generateSnowflake());
    const account2Id = BigInt(generateSnowflake());
    await db.insert(schema.accounts).values([
      { id: account1Id, workspaceId, name: "Account 1" },
      { id: account2Id, workspaceId, name: "Account 2" },
    ]);

    // Seed contacts with same phone but different accounts
    const contact1Id = BigInt(generateSnowflake());
    const contact2Id = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values([
      {
        id: contact1Id,
        workspaceId,
        accountId: account1Id,
        name: "Contact 1",
        phone: "+1234567890",
        doNotContact: false,
      },
      {
        id: contact2Id,
        workspaceId,
        accountId: account2Id,
        name: "Contact 2",
        phone: "+1234567890",
        doNotContact: false,
      },
    ]);

    const result = await resolveContact(
      { phone: "+1234567890" },
      threadId,
      a.ctx
    );

    expect(result.contactId).toBeNull();
    expect(result.reviewItemId).toBeTruthy();

    const reviews = await db
      .select()
      .from(schema.engagementIdentityReviewItems)
      .where(eq(schema.engagementIdentityReviewItems.threadId, BigInt(threadId)));
    expect(reviews).toHaveLength(1);
    expect(reviews[0].reason).toBe("account_conflict");
  });

  it("branch 5: no email and no phone match → returns null contactId and null reviewItemId", async () => {
    const a = await ws("res-no-match");
    const threadId = String(generateSnowflake());

    const result = await resolveContact(
      { email: "nonexistent@example.com", emailVerified: true },
      threadId,
      a.ctx
    );

    // Should not create a review since no matches were found during branch processing
    // Branch 1 finds zero matches, so it skips to branch 3 (no phone) -> branch 5 (nothing matched)
    expect(result.contactId).toBeNull();
    expect(result.reviewItemId).toBeNull();
  });
});
