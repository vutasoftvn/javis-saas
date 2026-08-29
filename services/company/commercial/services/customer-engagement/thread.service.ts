import { APIError } from "encore.dev/api";
import { and, eq, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { TenantContext } from "../../../shared/types/tenant_context";
import {
  buildThreadOpenedEvent, buildThreadStatusChangedEvent, buildThreadResolvedEvent,
} from "../../../shared/events/customer-engagement-events";
import { assertStatusTransition, type ThreadStatus } from "./thread-state";
import { resolveTier, snapshotThreadSla, SLA_POLICY_SEED } from "./sla.service";
import { assertRouteBound } from "./escalation.service";

const { engagementThreads, engagementThreadTransitions, engagementInboxes } = schema;

export interface ThreadDTO {
  id: string;
  workspaceId: string;
  inboxId: string;
  contactId: string | null;
  status: string;
  priority: string;
  tier: string;
  activeMode: string;
  ownerMemberId: string | null;
  correlationId: string;
  firstResponseDueAt: string | null;
  resolutionDueAt: string | null;
  escalationLevel: number;
  createdAt: string;
  updatedAt: string;
}

function toThreadDTO(r: typeof engagementThreads.$inferSelect): ThreadDTO {
  return {
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    inboxId: String(r.inboxId),
    contactId: r.contactId ? String(r.contactId) : null,
    status: r.status,
    priority: r.priority,
    tier: r.tier,
    activeMode: r.activeMode,
    ownerMemberId: r.ownerMemberId ? String(r.ownerMemberId) : null,
    correlationId: r.correlationId,
    firstResponseDueAt: r.firstResponseDueAt ? r.firstResponseDueAt.toISOString() : null,
    resolutionDueAt: r.resolutionDueAt ? r.resolutionDueAt.toISOString() : null,
    escalationLevel: r.escalationLevel,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  };
}

function actorOf(ctx: TenantContext) {
  return { kind: "user" as const, id: ctx.workforceMemberId ?? ctx.userId };
}

export async function openThread(
  params: { workspaceId: string; inboxId: string; contactId?: string; priority?: string; tier?: string; correlationId?: string },
  ctx: TenantContext,
): Promise<ThreadDTO> {
  if (String(params.workspaceId) !== String(ctx.workspaceId)) {
    throw APIError.permissionDenied("workspace mismatch");
  }

  // Load inbox scoped by workspace
  const [inbox] = await db.select().from(engagementInboxes).where(and(
    eq(engagementInboxes.id, BigInt(params.inboxId)),
    eq(engagementInboxes.workspaceId, BigInt(params.workspaceId)),
  )).limit(1);
  if (!inbox) throw APIError.notFound("inbox not found");

  // Resolve tier
  const tier = resolveTier({ defaultTier: inbox.defaultTier }, { tier: params.tier });

  // Snapshot SLA
  const sla = snapshotThreadSla(
    { workspaceId: BigInt(params.workspaceId) },
    inbox.slaPolicy as typeof SLA_POLICY_SEED,
    tier,
    new Date(),
  );

  // Fail-closed: if on_call mode and route key set, assert route is bound
  if (sla.slaSnapshot.outOfHoursMode === "on_call" && sla.escalationRouteKey) {
    await assertRouteBound(sla.escalationRouteKey, ctx);
  }

  const id = BigInt(generateSnowflake());
  const correlationId = params.correlationId ?? ctx.correlationId ?? `thr_${id}`;

  const row = await db.transaction(async (tx) => {
    const [t] = await tx.insert(engagementThreads).values({
      id,
      workspaceId: BigInt(params.workspaceId),
      inboxId: BigInt(params.inboxId),
      contactId: params.contactId ? BigInt(params.contactId) : null,
      status: "open",
      priority: params.priority ?? "normal",
      activeMode: "team_queue",
      correlationId,
      tier: sla.tier,
      slaPolicyVersion: sla.slaPolicyVersion,
      slaSnapshot: sla.slaSnapshot as any,
      firstResponseDueAt: sla.firstResponseDueAt,
      resolutionDueAt: sla.resolutionDueAt,
      escalationRouteKey: sla.escalationRouteKey,
    }).returning();
    if (!t) throw APIError.internal("failed to open thread");

    await tx.insert(engagementThreadTransitions).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(params.workspaceId),
      threadId: id,
      actor: actorOf(ctx),
      reasonCode: "opened",
      previousState: null,
      currentState: "open",
      correlationId,
    });

    await appendOutboxEvent(
      tx as any,
      buildThreadOpenedEvent(
        { id: String(id), workspaceId: String(params.workspaceId), inboxId: String(params.inboxId), correlationId },
        actorOf(ctx),
      ),
    );

    return t;
  });

  return toThreadDTO(row);
}

export async function loadThread(id: string, ctx: TenantContext) {
  const [row] = await db.select().from(engagementThreads).where(and(
    eq(engagementThreads.id, BigInt(id)),
    eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
  )).limit(1);
  if (!row) throw APIError.notFound("thread not found");
  return row;
}

export async function getThread(id: string, ctx: TenantContext): Promise<ThreadDTO> {
  return toThreadDTO(await loadThread(id, ctx));
}

export async function listThreads(
  filter: { status?: string; priority?: string; ownerMemberId?: string; activeMode?: string; limit?: number },
  ctx: TenantContext,
): Promise<ThreadDTO[]> {
  const conds = [eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId))];
  if (filter.status) conds.push(eq(engagementThreads.status, filter.status));
  if (filter.priority) conds.push(eq(engagementThreads.priority, filter.priority));
  if (filter.activeMode) conds.push(eq(engagementThreads.activeMode, filter.activeMode));
  if (filter.ownerMemberId) conds.push(eq(engagementThreads.ownerMemberId, BigInt(filter.ownerMemberId)));
  const rows = await db.select().from(engagementThreads).where(and(...conds))
    .orderBy(desc(engagementThreads.createdAt)).limit(filter.limit ?? 50);
  return rows.map(toThreadDTO);
}

export async function changeThreadStatus(
  id: string,
  params: { to: ThreadStatus; reasonCode: string; snoozedUntil?: string; resolutionCode?: string },
  ctx: TenantContext,
): Promise<ThreadDTO> {
  const current = await loadThread(id, ctx);
  assertStatusTransition(current.status as ThreadStatus, params.to);

  const updated = await db.transaction(async (tx) => {
    const patch: Record<string, unknown> = { status: params.to, updatedAt: new Date() };
    if (params.to === "snoozed") patch.snoozedUntil = params.snoozedUntil ? new Date(params.snoozedUntil) : null;
    if (params.to === "resolved") patch.resolvedAt = new Date();

    const [row] = await tx.update(engagementThreads).set(patch).where(and(
      eq(engagementThreads.id, BigInt(id)),
      eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
    )).returning();
    if (!row) throw APIError.internal("failed to update thread");

    await tx.insert(engagementThreadTransitions).values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(ctx.workspaceId),
      threadId: BigInt(id),
      actor: actorOf(ctx),
      reasonCode: params.reasonCode,
      previousState: current.status,
      currentState: params.to,
      correlationId: current.correlationId,
    });

    await appendOutboxEvent(
      tx as any,
      buildThreadStatusChangedEvent(
        {
          threadId: id,
          workspaceId: String(ctx.workspaceId),
          previousState: current.status,
          currentState: params.to,
          correlationId: current.correlationId,
        },
        actorOf(ctx),
      ),
    );

    if (params.to === "resolved") {
      await appendOutboxEvent(
        tx as any,
        buildThreadResolvedEvent(
          {
            threadId: id,
            workspaceId: String(ctx.workspaceId),
            resolutionCode: params.resolutionCode ?? "resolved",
            correlationId: current.correlationId,
          },
          actorOf(ctx),
        ),
      );
    }

    return row;
  });

  return toThreadDTO(updated);
}
