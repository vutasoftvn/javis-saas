import { APIError } from "encore.dev/api";
import { and, eq, desc, isNull } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementThreads,
  engagementMessages,
  engagementAssignments,
  engagementThreadLabels,
} from "../../../shared/db/schema/customer-engagement";
import { contacts } from "../../../shared/db/schema/commercial";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { ENGAGEMENT_PERMISSIONS, requireEngagementPermission } from "./rbac";

export interface ThreadContextDTO {
  thread: {
    id: string;
    status: string;
    priority: string;
    tier: string;
    activeMode: string;
    ownerMemberId: string | null;
    firstResponseDueAt: string | null;
    resolutionDueAt: string | null;
    correlationId: string;
  };
  contactId: string | null;
  identityVerified: boolean;
  messages: Array<{
    id: string;
    direction: string;
    visibility: string;
    senderKind: string;
    body: string;
    createdAt: string;
  }>;
  assignment: {
    assignedTeamId: string | null;
    assignedMemberId: string | null;
    assignedAgentSpecId: string | null;
  } | null;
  labels: Array<{
    labelKey: string;
    taxonomyVersion: number;
  }>;
}

export async function getThreadContextForAgent(
  threadId: string,
  ctx: TenantContext
): Promise<ThreadContextDTO> {
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);

  const wsId = BigInt(ctx.workspaceId);
  const tId = BigInt(threadId);

  // 1. Load thread
  const threadRows = await db
    .select()
    .from(engagementThreads)
    .where(and(eq(engagementThreads.id, tId), eq(engagementThreads.workspaceId, wsId)))
    .limit(1);

  if (threadRows.length === 0) {
    throw APIError.notFound(`Thread ${threadId} not found`);
  }

  const thread = threadRows[0];

  // 2. Identity verification check (P1: heuristic qua contact có email + !doNotContact)
  // TODO (P2 identity): nâng cấp khi có email_verified thật trên sales.contacts
  let identityVerified = false;
  let contactIdStr: string | null = null;

  if (thread.contactId) {
    contactIdStr = thread.contactId.toString();
    const contactRows = await db
      .select()
      .from(contacts)
      .where(and(eq(contacts.id, thread.contactId), eq(contacts.workspaceId, wsId)))
      .limit(1);

    if (contactRows.length > 0) {
      const contact = contactRows[0];
      identityVerified = Boolean(contact.email && contact.email.trim().length > 0 && !contact.doNotContact);
    }
  }

  // 3. Load messages (tối đa 30 gần nhất, giữ thứ tự thời gian tăng dần)
  const messageRows = await db
    .select()
    .from(engagementMessages)
    .where(and(eq(engagementMessages.threadId, tId), eq(engagementMessages.workspaceId, wsId)))
    .orderBy(desc(engagementMessages.createdAt))
    .limit(30);

  // Sắp xếp lại tăng dần theo createdAt
  const sortedMessages = messageRows.reverse().map((m) => ({
    id: m.id.toString(),
    direction: m.direction,
    visibility: m.visibility,
    senderKind: m.senderKind,
    body: m.body,
    createdAt: m.createdAt.toISOString(),
  }));

  // 4. Load active assignment
  const assignmentRows = await db
    .select()
    .from(engagementAssignments)
    .where(
      and(
        eq(engagementAssignments.threadId, tId),
        eq(engagementAssignments.workspaceId, wsId),
        isNull(engagementAssignments.endedAt)
      )
    )
    .limit(1);

  let assignment: ThreadContextDTO["assignment"] = null;
  if (assignmentRows.length > 0) {
    const a = assignmentRows[0];
    assignment = {
      assignedTeamId: a.assignedTeamId ? a.assignedTeamId.toString() : null,
      assignedMemberId: a.assignedMemberId ? a.assignedMemberId.toString() : null,
      assignedAgentSpecId: a.assignedAgentSpecId,
    };
  }

  // 5. Load thread labels
  const labelRows = await db
    .select()
    .from(engagementThreadLabels)
    .where(and(eq(engagementThreadLabels.threadId, tId), eq(engagementThreadLabels.workspaceId, wsId)));

  const labels = labelRows.map((l) => ({
    labelKey: l.labelKey,
    taxonomyVersion: typeof l.taxonomyVersion === "string" ? parseInt(l.taxonomyVersion, 10) || 1 : Number(l.taxonomyVersion) || 1,
  }));

  return {
    thread: {
      id: thread.id.toString(),
      status: thread.status,
      priority: thread.priority,
      tier: thread.tier,
      activeMode: thread.activeMode,
      ownerMemberId: thread.ownerMemberId ? thread.ownerMemberId.toString() : null,
      firstResponseDueAt: thread.firstResponseDueAt ? thread.firstResponseDueAt.toISOString() : null,
      resolutionDueAt: thread.resolutionDueAt ? thread.resolutionDueAt.toISOString() : null,
      correlationId: thread.correlationId,
    },
    contactId: contactIdStr,
    identityVerified,
    messages: sortedMessages,
    assignment,
    labels,
  };
}
