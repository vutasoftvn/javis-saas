import { APIError } from "encore.dev/api";
import { eq, and, isNull, sql } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { TenantContext } from "../../../shared/types/tenant_context";

interface ResolveContactInput {
  email?: string;
  phone?: string;
  emailVerified?: boolean;
}

export async function resolveContact(
  input: ResolveContactInput,
  threadId: string,
  ctx: TenantContext
): Promise<{ contactId: string | null; reviewItemId: string | null }> {
  const wsId = BigInt(ctx.workspaceId);
  const threadIdBig = BigInt(threadId);

  // Branch 1: email && emailVerified
  if (input.email && input.emailVerified) {
    const matches = await db
      .select()
      .from(schema.contacts)
      .where(
        and(
          sql`lower(${schema.contacts.email}) = lower(${input.email})`,
          eq(schema.contacts.workspaceId, wsId),
          isNull(schema.contacts.deletedAt)
        )
      );

    if (matches.length === 1) {
      const contact = matches[0];
      if (!contact.doNotContact) {
        // Exactly 1 match, not do-not-contact
        return { contactId: String(contact.id), reviewItemId: null };
      } else {
        // Exactly 1 match, but do-not-contact
        const reviewId = BigInt(generateSnowflake());
        await db.insert(schema.engagementIdentityReviewItems).values({
          id: reviewId,
          workspaceId: wsId,
          threadId: threadIdBig,
          candidateRefs: [{ contactId: String(contact.id) }],
          reason: "do_not_contact",
          status: "open",
        });
        return { contactId: null, reviewItemId: String(reviewId) };
      }
    } else if (matches.length > 1) {
      // Multiple matches
      const reviewId = BigInt(generateSnowflake());
      await db.insert(schema.engagementIdentityReviewItems).values({
        id: reviewId,
        workspaceId: wsId,
        threadId: threadIdBig,
        candidateRefs: matches.map((m) => ({ contactId: String(m.id) })),
        reason: "multiple_candidates",
        status: "open",
      });
      return { contactId: null, reviewItemId: String(reviewId) };
    }
    // If no matches, fall through to branch 2
  }

  // Branch 2: email && !emailVerified (only if branch 1 didn't handle it)
  if (input.email && !input.emailVerified) {
    const reviewId = BigInt(generateSnowflake());
    await db.insert(schema.engagementIdentityReviewItems).values({
      id: reviewId,
      workspaceId: wsId,
      threadId: threadIdBig,
      candidateRefs: [],
      reason: "unverified",
      status: "open",
    });
    return { contactId: null, reviewItemId: String(reviewId) };
  }

  // Branch 3: phone (only if email didn't produce a result)
  if (input.phone) {
    const matches = await db
      .select()
      .from(schema.contacts)
      .where(and(eq(schema.contacts.phone, input.phone), eq(schema.contacts.workspaceId, wsId), isNull(schema.contacts.deletedAt)));

    if (matches.length > 0) {
      // Get distinct accountIds
      const accountIds = new Set(matches.map((m) => String(m.accountId || "")));
      const distinctAccounts = Array.from(accountIds).filter((id) => id !== "");

      if (distinctAccounts.length > 1) {
        // Spans multiple accounts
        const reviewId = BigInt(generateSnowflake());
        await db.insert(schema.engagementIdentityReviewItems).values({
          id: reviewId,
          workspaceId: wsId,
          threadId: threadIdBig,
          candidateRefs: matches.map((m) => ({ contactId: String(m.id) })),
          reason: "account_conflict",
          status: "open",
        });
        return { contactId: null, reviewItemId: String(reviewId) };
      } else if (matches.length === 1) {
        const contact = matches[0];
        if (!contact.doNotContact) {
          return { contactId: String(contact.id), reviewItemId: null };
        } else {
          const reviewId = BigInt(generateSnowflake());
          await db.insert(schema.engagementIdentityReviewItems).values({
            id: reviewId,
            workspaceId: wsId,
            threadId: threadIdBig,
            candidateRefs: [{ contactId: String(contact.id) }],
            reason: "do_not_contact",
            status: "open",
          });
          return { contactId: null, reviewItemId: String(reviewId) };
        }
      }
    }
  }

  // Branch 5: No match found
  return { contactId: null, reviewItemId: null };
}
