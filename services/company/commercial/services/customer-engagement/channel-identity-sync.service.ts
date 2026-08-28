import { and, eq, or, isNull } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementThreads,
  engagementIdentityReviewItems,
} from "../../../shared/db/schema/customer-engagement";
import { contacts, accounts } from "../../../shared/db/schema/commercial";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

export interface IdentitySignals {
  email?: string;
  emailVerified?: boolean;
  phone?: string;
  externalUserRef?: string;
  externalUserName?: string;
}

export interface LinkIdentityOptions {
  autoCreateContact: boolean;
  channelType?: string;
}

export interface LinkIdentityResult {
  contactId: string | null;
  accountId: string | null;
  reviewItemId: string | null;
  created: boolean;
}

export async function linkThreadIdentity(
  threadIdStr: string,
  signals: IdentitySignals,
  ctx: TenantContext,
  opts: LinkIdentityOptions
): Promise<LinkIdentityResult> {
  const wsId = BigInt(ctx.workspaceId);
  const threadId = BigInt(threadIdStr);

  // 1. Search candidates by email (if verified) or phone
  const searchConditions = [];
  if (signals.email && signals.emailVerified) {
    searchConditions.push(eq(contacts.email, signals.email));
  }
  if (signals.phone) {
    searchConditions.push(eq(contacts.phone, signals.phone));
  }

  let candidates: any[] = [];
  if (searchConditions.length > 0) {
    candidates = await db
      .select()
      .from(contacts)
      .where(
        and(
          eq(contacts.workspaceId, wsId),
          isNull(contacts.deletedAt),
          or(...searchConditions)
        )
      );
  }

  // 2. Exact single match
  if (candidates.length === 1) {
    const matched = candidates[0];

    // If contact is flagged doNotContact, require human review
    if (matched.doNotContact) {
      const reviewItemId = generateSnowflake();
      await db.insert(engagementIdentityReviewItems).values({
        id: reviewItemId,
        workspaceId: wsId,
        threadId,
        candidateRefs: [matched.id.toString()],
        reason: "contact_do_not_contact",
        status: "open",
      });

      return {
        contactId: null,
        accountId: null,
        reviewItemId: reviewItemId.toString(),
        created: false,
      };
    }

    // Link thread to matched contact and backfill accountId if present
    await db
      .update(engagementThreads)
      .set({
        contactId: matched.id,
        accountId: matched.accountId,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(engagementThreads.id, threadId),
          eq(engagementThreads.workspaceId, wsId)
        )
      );

    return {
      contactId: matched.id.toString(),
      accountId: matched.accountId ? matched.accountId.toString() : null,
      reviewItemId: null,
      created: false,
    };
  }

  // 3. Ambiguous multiple candidates
  if (candidates.length > 1) {
    const reviewItemId = generateSnowflake();
    await db.insert(engagementIdentityReviewItems).values({
      id: reviewItemId,
      workspaceId: wsId,
      threadId,
      candidateRefs: candidates.map((c) => c.id.toString()),
      reason: "ambiguous_matches",
      status: "open",
    });

    return {
      contactId: null,
      accountId: null,
      reviewItemId: reviewItemId.toString(),
      created: false,
    };
  }

  // 4. No match found
  if (opts.autoCreateContact) {
    const newContactId = generateSnowflake();
    const contactName =
      signals.externalUserName || signals.phone || signals.externalUserRef || "Customer Contact";
    const channelSource = `engagement:${opts.channelType || "zalo"}`;

    await db.insert(contacts).values({
      id: newContactId,
      workspaceId: wsId,
      name: contactName,
      phone: signals.phone || null,
      email: signals.emailVerified ? signals.email : null,
      source: channelSource,
    });

    await db
      .update(engagementThreads)
      .set({
        contactId: newContactId,
        accountId: null,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(engagementThreads.id, threadId),
          eq(engagementThreads.workspaceId, wsId)
        )
      );

    return {
      contactId: newContactId.toString(),
      accountId: null,
      reviewItemId: null,
      created: true,
    };
  }

  // 5. No match and autoCreateContact is false -> create review item
  const reviewItemId = generateSnowflake();
  await db.insert(engagementIdentityReviewItems).values({
    id: reviewItemId,
    workspaceId: wsId,
    threadId,
    candidateRefs: [],
    reason: "no_match",
    status: "open",
  });

  return {
    contactId: null,
    accountId: null,
    reviewItemId: reviewItemId.toString(),
    created: false,
  };
}
