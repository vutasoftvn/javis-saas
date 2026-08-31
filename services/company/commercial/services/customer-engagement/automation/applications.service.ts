import { eq, and, desc } from "drizzle-orm";
import { db } from "../../../db";
import { engagementAutomationApplications } from "../../../../shared/db/schema/customer-engagement";

export async function listThreadAutomationApplications(input: {
  workspaceId: string;
  threadId: string;
}) {
  const wsId = BigInt(input.workspaceId);
  const threadId = BigInt(input.threadId);

  const rows = await db
    .select()
    .from(engagementAutomationApplications)
    .where(
      and(
        eq(engagementAutomationApplications.workspaceId, wsId),
        eq(engagementAutomationApplications.threadId, threadId)
      )
    )
    .orderBy(desc(engagementAutomationApplications.createdAt));

  return {
    applications: rows.map((r) => ({
      id: r.id.toString(),
      workspaceId: r.workspaceId.toString(),
      ruleKey: r.ruleKey,
      ruleVersion: r.ruleVersion,
      threadId: r.threadId.toString(),
      trigger: r.trigger,
      actionIndex: r.actionIndex,
      actionType: r.actionType,
      dedupeKey: r.dedupeKey,
      outcome: r.outcome,
      detail: r.detail,
      createdAt: r.createdAt,
    })),
  };
}
