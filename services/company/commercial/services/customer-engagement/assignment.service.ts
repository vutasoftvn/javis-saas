import { APIError } from "encore.dev/api";
import { and, eq, isNull, sql } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { TenantContext } from "../../../shared/types/tenant_context";
import {
  buildThreadAssignedEvent,
  buildThreadTakenOverEvent,
} from "../../../shared/events/customer-engagement-events";
import { loadThread } from "./thread.service";
import { ENGAGEMENT_PERMISSIONS, requireEngagementPermission } from "./rbac";

const { engagementAssignments, engagementThreads, engagementMessages, engagementOutboundDeliveries, engagementThreadTransitions } = schema;

export interface AssignmentDTO {
  id: string;
  threadId: string;
  assignedTeamId: string | null;
  assignedMemberId: string | null;
  assignedAgentSpecId: string | null;
  reason: string;
  assignedAt: string;
  endedAt: string | null;
}

function toAssignmentDTO(r: typeof engagementAssignments.$inferSelect): AssignmentDTO {
  return {
    id: String(r.id),
    threadId: String(r.threadId),
    assignedTeamId: r.assignedTeamId ? String(r.assignedTeamId) : null,
    assignedMemberId: r.assignedMemberId ? String(r.assignedMemberId) : null,
    assignedAgentSpecId: r.assignedAgentSpecId ?? null,
    reason: r.reason,
    assignedAt: r.assignedAt.toISOString(),
    endedAt: r.endedAt ? r.endedAt.toISOString() : null,
  };
}

function actorOf(ctx: TenantContext) {
  return { kind: "user" as const, id: ctx.workforceMemberId ?? ctx.userId };
}

export async function assignThread(
  params: { threadId: string; teamId?: string; memberId?: string; agentSpecId?: string; reason: string },
  ctx: TenantContext,
): Promise<AssignmentDTO> {
  // Load thread scoped
  const thread = await loadThread(params.threadId, ctx);

  const newAssignment = await db.transaction(async (tx) => {
    // End current active assignment
    await tx.update(engagementAssignments).set({ endedAt: new Date() }).where(and(
      eq(engagementAssignments.threadId, BigInt(params.threadId)),
      eq(engagementAssignments.workspaceId, BigInt(ctx.workspaceId)),
      isNull(engagementAssignments.endedAt),
    ));

    // Insert new assignment
    const newId = BigInt(generateSnowflake());
    const [assignment] = await tx.insert(engagementAssignments).values({
      id: newId,
      workspaceId: BigInt(ctx.workspaceId),
      threadId: BigInt(params.threadId),
      assignedTeamId: params.teamId ? BigInt(params.teamId) : null,
      assignedMemberId: params.memberId ? BigInt(params.memberId) : null,
      assignedAgentSpecId: params.agentSpecId ?? null,
      reason: params.reason,
    }).returning();
    if (!assignment) throw APIError.internal("failed to create assignment");

    // Update thread
    const [updatedThread] = await tx.update(engagementThreads).set({
      ownerMemberId: params.memberId ? BigInt(params.memberId) : null,
      activeMode: params.memberId ? "human_assigned" : "team_queue",
      updatedAt: new Date(),
    }).where(and(
      eq(engagementThreads.id, BigInt(params.threadId)),
      eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
    )).returning();
    if (!updatedThread) throw APIError.internal("failed to update thread");

    // Emit event
    await appendOutboxEvent(
      tx as any,
      buildThreadAssignedEvent(
        {
          threadId: params.threadId,
          workspaceId: String(ctx.workspaceId),
          assignmentId: String(newId),
          correlationId: thread.correlationId,
        },
        actorOf(ctx),
      ),
    );

    return assignment;
  });

  return toAssignmentDTO(newAssignment);
}

export async function takeOverThread(
  params: { threadId: string; reason: string },
  ctx: TenantContext,
): Promise<AssignmentDTO> {
  // Enforce permission
  requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.threadTakeover);

  // Validate workforce member
  if (!ctx.workforceMemberId) {
    throw APIError.permissionDenied("takeover requires a workforce member");
  }

  const workforceMemberId = ctx.workforceMemberId;

  // Load thread scoped
  const thread = await loadThread(params.threadId, ctx);

  const newAssignment = await db.transaction(async (tx) => {
    try {
      // End current active assignment
      await tx.update(engagementAssignments).set({ endedAt: new Date() }).where(and(
        eq(engagementAssignments.threadId, BigInt(params.threadId)),
        eq(engagementAssignments.workspaceId, BigInt(ctx.workspaceId)),
        isNull(engagementAssignments.endedAt),
      ));

      // Insert new assignment for human takeover
      const newId = BigInt(generateSnowflake());
      const [assignment] = await tx.insert(engagementAssignments).values({
        id: newId,
        workspaceId: BigInt(ctx.workspaceId),
        threadId: BigInt(params.threadId),
        assignedMemberId: BigInt(workforceMemberId),
        reason: params.reason,
      }).returning();
      if (!assignment) throw APIError.internal("failed to create assignment");

      // Update thread
      const [updatedThread] = await tx.update(engagementThreads).set({
        activeMode: "human_assigned",
        ownerMemberId: BigInt(workforceMemberId),
        updatedAt: new Date(),
      }).where(and(
        eq(engagementThreads.id, BigInt(params.threadId)),
        eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
      )).returning();
      if (!updatedThread) throw APIError.internal("failed to update thread");

      // Cancel in-flight outbound messages
      await tx.update(engagementMessages).set({ deliveryState: "cancelled" }).where(and(
        eq(engagementMessages.threadId, BigInt(params.threadId)),
        eq(engagementMessages.workspaceId, BigInt(ctx.workspaceId)),
        eq(engagementMessages.direction, "outbound"),
        eq(engagementMessages.visibility, "customer"),
        eq(engagementMessages.deliveryState, "queued"),
      ));

      // Cancel in-flight outbound deliveries
      await tx.update(engagementOutboundDeliveries).set({
        status: "failed",
        deadLetterReason: "superseded_by_takeover",
      }).where(and(
        eq(engagementOutboundDeliveries.threadId, BigInt(params.threadId)),
        eq(engagementOutboundDeliveries.workspaceId, BigInt(ctx.workspaceId)),
        eq(engagementOutboundDeliveries.status, "queued"),
      ));

      // Insert transition
      await tx.insert(engagementThreadTransitions).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ctx.workspaceId),
        threadId: BigInt(params.threadId),
        actor: actorOf(ctx),
        reasonCode: "taken_over",
        previousState: thread.status,
        currentState: thread.status,
        previousMode: thread.activeMode,
        currentMode: "human_assigned",
        correlationId: thread.correlationId,
      });

      // Emit event
      await appendOutboxEvent(
        tx as any,
        buildThreadTakenOverEvent(
          {
            threadId: params.threadId,
            workspaceId: String(ctx.workspaceId),
            newOwnerMemberId: workforceMemberId,
            correlationId: thread.correlationId,
          },
          actorOf(ctx),
        ),
      );

      return assignment;
    } catch (err) {
      // Catch unique constraint violation on concurrent takeover
      if ((err as any)?.code === "23505" || (err as any)?.cause?.code === "23505") {
        throw APIError.alreadyExists("thread already taken over");
      }
      throw err;
    }
  });

  return toAssignmentDTO(newAssignment);
}

export async function handBackToAgent(
  params: { threadId: string; agentSpecId: string; scope?: string; expiresAt: string },
  ctx: TenantContext,
): Promise<AssignmentDTO> {
  // Validate required field
  if (!params.expiresAt) {
    throw APIError.invalidArgument("handBackToAgent requires expiresAt");
  }

  // Load thread scoped
  const thread = await loadThread(params.threadId, ctx);

  const newAssignment = await db.transaction(async (tx) => {
    // End current active assignment
    await tx.update(engagementAssignments).set({ endedAt: new Date() }).where(and(
      eq(engagementAssignments.threadId, BigInt(params.threadId)),
      eq(engagementAssignments.workspaceId, BigInt(ctx.workspaceId)),
      isNull(engagementAssignments.endedAt),
    ));

    // Insert new assignment with agent hand-back
    const newId = BigInt(generateSnowflake());
    const reason = JSON.stringify({ scope: params.scope, expiresAt: params.expiresAt });
    const [assignment] = await tx.insert(engagementAssignments).values({
      id: newId,
      workspaceId: BigInt(ctx.workspaceId),
      threadId: BigInt(params.threadId),
      assignedAgentSpecId: params.agentSpecId,
      reason,
    }).returning();
    if (!assignment) throw APIError.internal("failed to create assignment");

    // Update thread
    const [updatedThread] = await tx.update(engagementThreads).set({
      activeMode: "agent_copilot",
      ownerMemberId: null,
      updatedAt: new Date(),
    }).where(and(
      eq(engagementThreads.id, BigInt(params.threadId)),
      eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
    )).returning();
    if (!updatedThread) throw APIError.internal("failed to update thread");

    // Insert transition
    await tx.insert(engagementThreadTransitions).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      threadId: BigInt(params.threadId),
      actor: actorOf(ctx),
      reasonCode: "handed_back",
      previousState: thread.status,
      currentState: thread.status,
      previousMode: thread.activeMode,
      currentMode: "agent_copilot",
      correlationId: thread.correlationId,
    });

    return assignment;
  });

  return toAssignmentDTO(newAssignment);
}
