import { APIError } from "encore.dev/api";
import { and, eq, desc, isNull, inArray } from "drizzle-orm";
import { db } from "../../../db";
import {
  engagementThreads,
  engagementInboxes,
  engagementMessages,
  engagementThreadLabels,
  engagementThreadOutcomes,
  engagementDecisionRequests,
} from "../../../../shared/db/schema/customer-engagement";
import { contacts, accounts, customers } from "../../../../shared/db/schema/commercial";
import type { TenantContext } from "../../../../shared/types/tenant_context";

export interface AutomationFacts {
  thread: {
    status: string;
    priority: string;
    tier: string;
    activeMode: string;
    ownerMemberId: string | null;
    escalationLevel: number;
    ageMinutes: number;
    minutesSinceLastCustomerMsg: number | null;
    firstResponded: boolean;
    hasOpenDecisionRequest: boolean;
  };
  inbox: {
    channelType: string;
    locale: string | null;
    businessHoursOpen: boolean;
  };
  sla: {
    firstResponseDueInMinutes: number | null;
    resolutionDueInMinutes: number | null;
    firstResponseBreached: boolean;
    resolutionBreached: boolean;
    pctToFirstResponseBreach: number | null;
  };
  contact: {
    present: boolean;
    doNotContact: boolean;
  };
  account: {
    present: boolean;
  };
  customer: {
    present: boolean;
    healthStatus: string | null;
    tier: string | null;
  };
  lastMessage: {
    direction: string | null;
    visibility: string | null;
  };
  csat: {
    latestScore: number | null;
    latestRecordedMinutesAgo: number | null;
  };
  labels: string[];
}

export const FACT_KEYS: ReadonlySet<string> = new Set([
  "thread.status",
  "thread.priority",
  "thread.tier",
  "thread.activeMode",
  "thread.ownerMemberId",
  "thread.escalationLevel",
  "thread.ageMinutes",
  "thread.minutesSinceLastCustomerMsg",
  "thread.firstResponded",
  "thread.hasOpenDecisionRequest",
  "inbox.channelType",
  "inbox.locale",
  "inbox.businessHoursOpen",
  "sla.firstResponseDueInMinutes",
  "sla.resolutionDueInMinutes",
  "sla.firstResponseBreached",
  "sla.resolutionBreached",
  "sla.pctToFirstResponseBreach",
  "contact.present",
  "contact.doNotContact",
  "account.present",
  "customer.present",
  "customer.healthStatus",
  "customer.tier",
  "lastMessage.direction",
  "lastMessage.visibility",
  "csat.latestScore",
  "csat.latestRecordedMinutesAgo",
  "labels",
]);

export async function buildAutomationFacts(
  threadId: string,
  ctx: TenantContext
): Promise<AutomationFacts> {
  const wsId = BigInt(ctx.workspaceId);
  const tId = BigInt(threadId);

  // 1. Thread
  const threadRows = await db
    .select()
    .from(engagementThreads)
    .where(and(eq(engagementThreads.id, tId), eq(engagementThreads.workspaceId, wsId)));

  if (threadRows.length === 0) {
    throw APIError.notFound("Engagement thread not found");
  }
  const thread = threadRows[0];

  // 2. Inbox
  const inboxRows = await db
    .select()
    .from(engagementInboxes)
    .where(and(eq(engagementInboxes.id, thread.inboxId), eq(engagementInboxes.workspaceId, wsId)));

  const inbox = inboxRows[0];

  // 3. Contact (if linked)
  let contactRow: any = null;
  if (thread.contactId) {
    const rows = await db
      .select()
      .from(contacts)
      .where(and(eq(contacts.id, thread.contactId), eq(contacts.workspaceId, wsId)));
    contactRow = rows[0] || null;
  }

  // 4. Customer (if linked)
  let customerRow: any = null;
  if (thread.customerId) {
    const rows = await db
      .select()
      .from(customers)
      .where(and(eq(customers.id, thread.customerId), eq(customers.workspaceId, wsId)));
    customerRow = rows[0] || null;
  }

  // 5. Last message
  const msgRows = await db
    .select()
    .from(engagementMessages)
    .where(and(eq(engagementMessages.threadId, tId), eq(engagementMessages.workspaceId, wsId)))
    .orderBy(desc(engagementMessages.createdAt))
    .limit(1);
  const lastMsg = msgRows[0] || null;

  // 6. Labels
  const labelRows = await db
    .select()
    .from(engagementThreadLabels)
    .where(and(eq(engagementThreadLabels.threadId, tId), eq(engagementThreadLabels.workspaceId, wsId)));
  const labels = labelRows.map((l: any) => l.labelKey);

  // 7. CSAT Outcomes
  const outcomeRows = await db
    .select()
    .from(engagementThreadOutcomes)
    .where(and(eq(engagementThreadOutcomes.threadId, tId), eq(engagementThreadOutcomes.workspaceId, wsId)))
    .orderBy(desc(engagementThreadOutcomes.createdAt))
    .limit(1);
  const latestOutcome = outcomeRows[0] || null;

  // 8. Open Decision Requests
  const openDrRows = await db
    .select()
    .from(engagementDecisionRequests)
    .where(
      and(
        eq(engagementDecisionRequests.threadId, tId),
        eq(engagementDecisionRequests.workspaceId, wsId),
        inArray(engagementDecisionRequests.status, ["draft", "pending_approval"])
      )
    )
    .limit(1);
  const hasOpenDecisionRequest = openDrRows.length > 0;

  // Derived metrics
  const now = Date.now();
  const createdAtMs = thread.createdAt.getTime();
  const ageMinutes = Math.floor((now - createdAtMs) / 60000);

  const minutesSinceLastCustomerMsg = thread.lastCustomerMsgAt
    ? Math.floor((now - thread.lastCustomerMsgAt.getTime()) / 60000)
    : null;

  const firstResponded = thread.firstResponseAt !== null;

  const firstResponseDueInMinutes = thread.firstResponseDueAt
    ? Math.floor((thread.firstResponseDueAt.getTime() - now) / 60000)
    : null;

  const resolutionDueInMinutes = thread.resolutionDueAt
    ? Math.floor((thread.resolutionDueAt.getTime() - now) / 60000)
    : null;

  const firstResponseBreached = Boolean(
    thread.firstResponseDueAt && !firstResponded && thread.firstResponseDueAt.getTime() < now
  );

  const resolutionBreached = Boolean(
    thread.resolutionDueAt && thread.status !== "resolved" && thread.resolutionDueAt.getTime() < now
  );

  let pctToFirstResponseBreach: number | null = null;
  if (thread.firstResponseDueAt) {
    const totalWindow = thread.firstResponseDueAt.getTime() - createdAtMs;
    const elapsed = now - createdAtMs;
    pctToFirstResponseBreach = totalWindow > 0 ? Math.min(100, Math.max(0, Math.round((elapsed / totalWindow) * 100))) : 100;
  }

  // Business hours computation (default 8:00 - 18:00 local time Mon-Fri)
  const currentHour = new Date().getHours();
  const currentDay = new Date().getDay();
  const isWeekday = currentDay >= 1 && currentDay <= 5;
  const businessHoursOpen = isWeekday && currentHour >= 8 && currentHour < 18;

  let csatLatestRecordedMinutesAgo: number | null = null;
  if (latestOutcome?.csatRecordedAt) {
    csatLatestRecordedMinutesAgo = Math.floor((now - latestOutcome.csatRecordedAt.getTime()) / 60000);
  }

  return {
    thread: {
      status: thread.status,
      priority: thread.priority,
      tier: thread.tier,
      activeMode: thread.activeMode,
      ownerMemberId: thread.ownerMemberId ? thread.ownerMemberId.toString() : null,
      escalationLevel: thread.escalationLevel,
      ageMinutes,
      minutesSinceLastCustomerMsg,
      firstResponded,
      hasOpenDecisionRequest,
    },
    inbox: {
      channelType: inbox?.channelType || "unknown",
      locale: "vi",
      businessHoursOpen,
    },
    sla: {
      firstResponseDueInMinutes,
      resolutionDueInMinutes,
      firstResponseBreached,
      resolutionBreached,
      pctToFirstResponseBreach,
    },
    contact: {
      present: Boolean(contactRow),
      doNotContact: Boolean(contactRow?.doNotContact),
    },
    account: {
      present: Boolean(thread.accountId),
    },
    customer: {
      present: Boolean(customerRow),
      healthStatus: customerRow?.healthStatus || null,
      tier: customerRow?.lifecycleStatus || null,
    },
    lastMessage: {
      direction: lastMsg?.direction || null,
      visibility: lastMsg?.visibility || null,
    },
    csat: {
      latestScore: latestOutcome?.csatScore ?? null,
      latestRecordedMinutesAgo: csatLatestRecordedMinutesAgo,
    },
    labels,
  };
}
