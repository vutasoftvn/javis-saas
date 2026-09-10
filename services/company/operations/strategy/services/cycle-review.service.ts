import { APIError } from "encore.dev/api";
import { eq, and, isNull, desc, inArray } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  validateDurationWeeks,
  addDaysToLocalDate,
  localDateToTimezoneInstant,
} from "../../services/execution-calendar";
import {
  getWorkspaceStrategySettings,
  WorkspaceStrategySettings,
  MidCycleReviewPolicy,
} from "./workspace-strategy-settings.service";
import { requireStrategyGovernanceAuthority } from "./strategy-governance-authorization.service";

const {
  cycleReviews,
  twelveWeekCycles,
  pestelSignals,
  initiatives,
  keyResults,
  decisionRecords,
} = schema;

export type CycleReviewKind = "WEEKLY" | "MID_CYCLE" | "END_CYCLE";
export type CycleReviewStatus =
  | "SCHEDULED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "SKIPPED"
  | "SUPERSEDED";

export interface CycleReviewSlot {
  kind: CycleReviewKind;
  scheduledWeekNo: number;
}

export interface CycleReviewView {
  id: string;
  workspaceId: string;
  projectId: string | null;
  cycleId: string;
  kind: CycleReviewKind;
  scheduledWeekNo: number;
  scheduledAt: string | null;
  status: CycleReviewStatus;
  krSnapshots: any[];
  initiativeSnapshots: any[];
  pestelSnapshots: any[];
  decisionId: string | null;
  conclusion: string | null;
  conductedByMemberId: string | null;
  conductedAt: string | null;
  settingsRevision: number | null;
  revision: number;
  createdAt: string;
  updatedAt: string;
}

export function toCycleReviewView(row: typeof cycleReviews.$inferSelect): CycleReviewView {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    projectId: row.projectId ? String(row.projectId) : null,
    cycleId: String(row.cycleId),
    kind: row.kind as CycleReviewKind,
    scheduledWeekNo: row.scheduledWeekNo,
    scheduledAt: row.scheduledAt ? row.scheduledAt.toISOString() : null,
    status: row.status as CycleReviewStatus,
    krSnapshots: (row.krSnapshots as any[]) || [],
    initiativeSnapshots: (row.initiativeSnapshots as any[]) || [],
    pestelSnapshots: (row.pestelSnapshots as any[]) || [],
    decisionId: row.decisionId ? String(row.decisionId) : null,
    conclusion: row.conclusion,
    conductedByMemberId: row.conductedByMemberId ? String(row.conductedByMemberId) : null,
    conductedAt: row.conductedAt ? row.conductedAt.toISOString() : null,
    settingsRevision: row.settingsRevision,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

/**
 * Deterministically constructs review slots for a cycle based on duration and policy.
 * - duration 1..3: WEEKLY + END_CYCLE only
 * - duration >= 4 and policy AUTO: add MID_CYCLE at Math.ceil(durationWeeks / 2)
 * - policy CUSTOM: mid-cycle is not scheduled automatically (created on-demand)
 * - policy OFF: mid-cycle is never scheduled automatically
 */
export function buildCycleReviewSchedule(
  durationWeeks: number,
  policy: MidCycleReviewPolicy = "AUTO",
  options?: { weeklyReviewEnabled?: boolean; endCycleReviewEnabled?: boolean }
): CycleReviewSlot[] {
  validateDurationWeeks(durationWeeks);

  const slots: CycleReviewSlot[] = [];

  // 1. Weekly reviews
  if (options?.weeklyReviewEnabled !== false) {
    for (let w = 1; w <= durationWeeks; w++) {
      slots.push({ kind: "WEEKLY", scheduledWeekNo: w });
    }
  }

  // 2. Mid-cycle review
  if (durationWeeks >= 4 && policy === "AUTO") {
    const midWeek = Math.ceil(durationWeeks / 2);
    slots.push({ kind: "MID_CYCLE", scheduledWeekNo: midWeek });
  }

  // 3. End-cycle review
  if (options?.endCycleReviewEnabled !== false) {
    slots.push({ kind: "END_CYCLE", scheduledWeekNo: durationWeeks });
  }

  const kindOrder: Record<CycleReviewKind, number> = {
    WEEKLY: 1,
    MID_CYCLE: 2,
    END_CYCLE: 3,
  };

  slots.sort((a, b) => {
    if (a.scheduledWeekNo !== b.scheduledWeekNo) {
      return a.scheduledWeekNo - b.scheduledWeekNo;
    }
    return kindOrder[a.kind] - kindOrder[b.kind];
  });

  return slots;
}

export function calculateReviewScheduledDate(
  startLocalDate: string | null | undefined,
  weekNo: number,
  timezone = "UTC"
): Date | null {
  if (!startLocalDate) return null;
  const civilDate = addDaysToLocalDate(startLocalDate, (weekNo - 1) * 7);
  return localDateToTimezoneInstant(civilDate, timezone);
}

/**
 * Schedule initial reviews when a cycle is created or activated.
 */
export async function scheduleInitialCycleReviews(
  tx: any,
  cycle: {
    id: bigint;
    workspaceId: bigint;
    projectId?: bigint | null;
    durationWeeks: number;
    startLocalDate?: string | null;
    timezone?: string | null;
  },
  settings?: WorkspaceStrategySettings
): Promise<void> {
  const currentSettings = settings ?? (await getWorkspaceStrategySettings(cycle.workspaceId));
  const slots = buildCycleReviewSchedule(
    cycle.durationWeeks,
    currentSettings.midCycleReviewPolicy,
    {
      weeklyReviewEnabled: currentSettings.weeklyReviewEnabled,
      endCycleReviewEnabled: currentSettings.endCycleReviewEnabled,
    }
  );

  const rowsToInsert = slots.map((slot) => {
    const scheduledAt = calculateReviewScheduledDate(
      cycle.startLocalDate,
      slot.scheduledWeekNo,
      cycle.timezone || "UTC"
    );
    return {
      id: generateSnowflake(),
      workspaceId: cycle.workspaceId,
      projectId: cycle.projectId || null,
      cycleId: cycle.id,
      kind: slot.kind,
      scheduledWeekNo: slot.scheduledWeekNo,
      scheduledAt,
      status: "SCHEDULED",
      settingsRevision: currentSettings.revision,
      revision: 1,
    };
  });

  if (rowsToInsert.length > 0) {
    await tx.insert(cycleReviews).values(rowsToInsert);
  }
}

/**
 * Reschedules cycle reviews upon cycle duration or schedule change.
 * - Preserves COMPLETED reviews unmodified.
 * - Supersedes incomplete reviews that are outside the new duration or obsolete.
 * - Inserts new slots without duplicating active/completed ones.
 */
export async function rescheduleCycleReviews(
  tx: any,
  cycleId: bigint,
  workspaceId: bigint,
  oldDuration: number,
  newDuration: number,
  settings: WorkspaceStrategySettings,
  startLocalDate?: string | null,
  timezone?: string | null
): Promise<void> {
  const existingRows = await tx
    .select()
    .from(cycleReviews)
    .where(
      and(
        eq(cycleReviews.cycleId, cycleId),
        eq(cycleReviews.workspaceId, workspaceId),
        isNull(cycleReviews.deletedAt)
      )
    );

  const targetSlots = buildCycleReviewSchedule(
    newDuration,
    settings.midCycleReviewPolicy,
    {
      weeklyReviewEnabled: settings.weeklyReviewEnabled,
      endCycleReviewEnabled: settings.endCycleReviewEnabled,
    }
  );

  const targetSlotKey = (kind: string, week: number) => `${kind}:${week}`;
  const validSlotKeys = new Set(targetSlots.map((s) => targetSlotKey(s.kind, s.scheduledWeekNo)));

  // Supersede obsolete incomplete slots
  for (const row of existingRows) {
    if (row.status === "COMPLETED" || row.status === "SUPERSEDED" || row.status === "SKIPPED") {
      continue;
    }
    const key = targetSlotKey(row.kind, row.scheduledWeekNo);
    if (!validSlotKeys.has(key)) {
      await tx
        .update(cycleReviews)
        .set({
          status: "SUPERSEDED",
          updatedAt: new Date(),
          revision: row.revision + 1,
        })
        .where(eq(cycleReviews.id, row.id));
    } else if (row.status === "SCHEDULED" && startLocalDate !== undefined) {
      // Update scheduledAt if civil date or timezone changed
      const updatedDate = calculateReviewScheduledDate(
        startLocalDate,
        row.scheduledWeekNo,
        timezone || "UTC"
      );
      await tx
        .update(cycleReviews)
        .set({
          scheduledAt: updatedDate,
          updatedAt: new Date(),
        })
        .where(eq(cycleReviews.id, row.id));
    }
  }

  // Check which target slots need insertion
  const activeExistingKeys = new Set(
    existingRows
      .filter((r: any) => r.status !== "SUPERSEDED" && r.status !== "SKIPPED")
      .map((r: any) => targetSlotKey(r.kind, r.scheduledWeekNo))
  );

  const newSlotsToInsert: typeof cycleReviews.$inferInsert[] = [];
  for (const slot of targetSlots) {
    const key = targetSlotKey(slot.kind, slot.scheduledWeekNo);
    if (!activeExistingKeys.has(key)) {
      const scheduledAt = calculateReviewScheduledDate(
        startLocalDate,
        slot.scheduledWeekNo,
        timezone || "UTC"
      );
      newSlotsToInsert.push({
        id: generateSnowflake(),
        workspaceId,
        cycleId,
        kind: slot.kind,
        scheduledWeekNo: slot.scheduledWeekNo,
        scheduledAt,
        status: "SCHEDULED",
        settingsRevision: settings.revision,
        revision: 1,
      });
    }
  }

  if (newSlotsToInsert.length > 0) {
    await tx.insert(cycleReviews).values(newSlotsToInsert);
  }
}

export async function listCycleReviewsService(
  workspaceId: bigint,
  cycleId: bigint
): Promise<CycleReviewView[]> {
  const rows = await db
    .select()
    .from(cycleReviews)
    .where(
      and(
        eq(cycleReviews.workspaceId, workspaceId),
        eq(cycleReviews.cycleId, cycleId),
        isNull(cycleReviews.deletedAt)
      )
    )
    .orderBy(cycleReviews.scheduledWeekNo, cycleReviews.kind);

  return rows.map(toCycleReviewView);
}

export async function getCycleReviewService(
  workspaceId: bigint,
  reviewId: bigint
): Promise<CycleReviewView> {
  const [row] = await db
    .select()
    .from(cycleReviews)
    .where(
      and(
        eq(cycleReviews.workspaceId, workspaceId),
        eq(cycleReviews.id, reviewId),
        isNull(cycleReviews.deletedAt)
      )
    )
    .limit(1);

  if (!row) {
    throw APIError.notFound(`Cycle review ${reviewId} not found`);
  }

  return toCycleReviewView(row);
}

export async function startCycleReviewService(
  ctx: TenantContext,
  reviewId: bigint
): Promise<CycleReviewView> {
  const wsId = BigInt(ctx.workspaceId);

  return await db.transaction(async (tx) => {
    const [review] = await tx
      .select()
      .from(cycleReviews)
      .where(
        and(
          eq(cycleReviews.id, reviewId),
          eq(cycleReviews.workspaceId, wsId),
          isNull(cycleReviews.deletedAt)
        )
      )
      .limit(1);

    if (!review) {
      throw APIError.notFound(`Cycle review ${reviewId} not found`);
    }

    // Idempotent: snapshots already captured
    if (review.status === "IN_PROGRESS" || review.status === "COMPLETED") {
      return toCycleReviewView(review);
    }

    if (review.status !== "SCHEDULED") {
      throw APIError.failedPrecondition(
        `Cannot start review in status '${review.status}'`
      );
    }

    // Capture visible PESTEL signals
    const pestelRows = await tx
      .select()
      .from(pestelSignals)
      .where(eq(pestelSignals.workspaceId, wsId));
    const pestelSnapshots = pestelRows.map((p) => ({
      id: String(p.id),
      strategicObjectiveId: String(p.strategicObjectiveId),
      dimension: p.dimension,
      statement: p.statement,
      impact: p.impact,
      certainty: p.certainty,
      evidenceRefs: p.evidenceRefs,
      bscPerspectives: p.bscPerspectives,
      status: p.status,
    }));

    // Capture active initiatives
    const initRows = await tx
      .select()
      .from(initiatives)
      .where(and(eq(initiatives.workspaceId, wsId), isNull(initiatives.deletedAt)));
    const initiativeSnapshots = initRows.map((i) => ({
      id: String(i.id),
      title: i.title,
      status: i.status,
      approvalStatus: i.approvalStatus,
      strategicObjectiveId: null,
      sourceTowsOptionId: null,
      targetDate: i.targetDate ? i.targetDate.toISOString() : null,
      milestones: i.milestones,
    }));

    // Capture Key Results
    const krRows = await tx
      .select()
      .from(keyResults)
      .where(and(eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)));
    const krSnapshots = krRows.map((k) => ({
      id: String(k.id),
      objectiveId: String(k.objectiveId),
      title: k.title,
      baselineValue: k.baselineValue,
      currentValue: k.currentValue,
      targetValue: k.targetValue,
      unit: k.unit,
      scoringType: k.scoringType,
      status: k.status,
    }));

    const [updated] = await tx
      .update(cycleReviews)
      .set({
        status: "IN_PROGRESS",
        pestelSnapshots,
        initiativeSnapshots,
        krSnapshots,
        revision: review.revision + 1,
        updatedAt: new Date(),
      })
      .where(eq(cycleReviews.id, review.id))
      .returning();

    return toCycleReviewView(updated!);
  });
}

export async function createCustomMidCycleReviewService(
  ctx: TenantContext,
  cycleId: bigint,
  scheduledWeekNo: number
): Promise<CycleReviewView> {
  const wsId = BigInt(ctx.workspaceId);

  if (
    (ctx as any).actorKind === "AI_AGENT" ||
    (ctx as any).isAgent === true ||
    ctx.membershipRole === "agent"
  ) {
    throw APIError.permissionDenied("Agents cannot create custom reviews; human approval required");
  }

  const [cycle] = await db
    .select()
    .from(twelveWeekCycles)
    .where(
      and(
        eq(twelveWeekCycles.id, cycleId),
        eq(twelveWeekCycles.workspaceId, wsId),
        isNull(twelveWeekCycles.deletedAt)
      )
    )
    .limit(1);

  if (!cycle) {
    throw APIError.notFound(`Cycle ${cycleId} not found`);
  }

  if (scheduledWeekNo < 1 || scheduledWeekNo > cycle.durationWeeks) {
    throw APIError.invalidArgument(
      `scheduledWeekNo ${scheduledWeekNo} is outside cycle duration of ${cycle.durationWeeks} weeks`
    );
  }

  const settings = await getWorkspaceStrategySettings(wsId);
  if (settings.midCycleReviewPolicy === "OFF") {
    throw APIError.failedPrecondition(
      "Mid-cycle reviews are disabled by workspace strategy settings policy 'OFF'"
    );
  }

  // Check if active MID_CYCLE review already exists for this week
  const [existing] = await db
    .select()
    .from(cycleReviews)
    .where(
      and(
        eq(cycleReviews.cycleId, cycleId),
        eq(cycleReviews.kind, "MID_CYCLE"),
        eq(cycleReviews.scheduledWeekNo, scheduledWeekNo),
        isNull(cycleReviews.deletedAt)
      )
    )
    .limit(1);

  if (existing && existing.status !== "SUPERSEDED" && existing.status !== "SKIPPED") {
    throw APIError.alreadyExists(
      `An active mid-cycle review already exists for week ${scheduledWeekNo}`
    );
  }

  const scheduledAt = calculateReviewScheduledDate(
    cycle.startLocalDate ? String(cycle.startLocalDate) : null,
    scheduledWeekNo,
    cycle.timezone || "UTC"
  );

  const [created] = await db
    .insert(cycleReviews)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: cycle.projectId || null,
      cycleId,
      kind: "MID_CYCLE",
      scheduledWeekNo,
      scheduledAt,
      status: "SCHEDULED",
      settingsRevision: settings.revision,
      revision: 1,
    })
    .returning();

  return toCycleReviewView(created!);
}

export async function updateCycleReviewService(
  ctx: TenantContext,
  reviewId: bigint,
  input: { conclusion?: string }
): Promise<CycleReviewView> {
  const wsId = BigInt(ctx.workspaceId);

  const [review] = await db
    .select()
    .from(cycleReviews)
    .where(
      and(
        eq(cycleReviews.id, reviewId),
        eq(cycleReviews.workspaceId, wsId),
        isNull(cycleReviews.deletedAt)
      )
    )
    .limit(1);

  if (!review) {
    throw APIError.notFound(`Cycle review ${reviewId} not found`);
  }

  if (review.status === "COMPLETED") {
    throw APIError.failedPrecondition("Cannot update a completed cycle review");
  }

  const [updated] = await db
    .update(cycleReviews)
    .set({
      conclusion: input.conclusion !== undefined ? input.conclusion : review.conclusion,
      revision: review.revision + 1,
      updatedAt: new Date(),
    })
    .where(eq(cycleReviews.id, review.id))
    .returning();

  return toCycleReviewView(updated!);
}

export async function closeCycleReviewService(
  ctx: TenantContext,
  reviewId: bigint,
  input: { conclusion?: string; decisionId?: string }
): Promise<CycleReviewView> {
  const wsId = BigInt(ctx.workspaceId);

  if (
    (ctx as any).actorKind === "AI_AGENT" ||
    (ctx as any).isAgent === true ||
    ctx.membershipRole === "agent"
  ) {
    throw APIError.permissionDenied("Agents cannot close cycle reviews; human approval required");
  }

  return await db.transaction(async (tx) => {
    const [review] = await tx
      .select()
      .from(cycleReviews)
      .where(
        and(
          eq(cycleReviews.id, reviewId),
          eq(cycleReviews.workspaceId, wsId),
          isNull(cycleReviews.deletedAt)
        )
      )
      .limit(1);

    if (!review) {
      throw APIError.notFound(`Cycle review ${reviewId} not found`);
    }

    if (review.status === "COMPLETED") {
      return toCycleReviewView(review);
    }

    if (review.status === "SUPERSEDED" || review.status === "SKIPPED") {
      throw APIError.failedPrecondition(
        `Cannot close review in status '${review.status}'`
      );
    }

    let linkedDecisionId: bigint | null = null;

    // END_CYCLE review requires strategy.review.close governance authority and creates decision record
    if (review.kind === "END_CYCLE") {
      await requireStrategyGovernanceAuthority(ctx, "strategy.review.close", {
        workspaceId: ctx.workspaceId,
      });

      const decisionId = generateSnowflake();
      const actorMemberId = ctx.userId ? BigInt(ctx.userId) : null;

      await tx.insert(decisionRecords).values({
        id: decisionId,
        workspaceId: wsId,
        projectId: review.projectId,
        decision: "END_CYCLE_REVIEW_CLOSED",
        decisionType: "CYCLE_REVIEW_CLOSURE",
        createdByKind: "FOUNDER",
        actorMemberId,
        decidedAt: new Date(),
        evidenceSnapshot: {
          reviewId: String(review.id),
          cycleId: String(review.cycleId),
          scheduledWeekNo: review.scheduledWeekNo,
          conclusion: input.conclusion ?? review.conclusion ?? "",
        },
      });

      linkedDecisionId = decisionId;
    } else if (input.decisionId) {
      linkedDecisionId = BigInt(input.decisionId);
    } else {
      linkedDecisionId = review.decisionId;
    }

    // Ensure snapshots are preserved even if closed directly from SCHEDULED
    let pestelSnapshots = review.pestelSnapshots as any[];
    let initiativeSnapshots = review.initiativeSnapshots as any[];
    let krSnapshots = review.krSnapshots as any[];

    if (!pestelSnapshots || pestelSnapshots.length === 0) {
      const pestelRows = await tx
        .select()
        .from(pestelSignals)
        .where(eq(pestelSignals.workspaceId, wsId));
      pestelSnapshots = pestelRows.map((p) => ({
        id: String(p.id),
        strategicObjectiveId: String(p.strategicObjectiveId),
        dimension: p.dimension,
        statement: p.statement,
        impact: p.impact,
        certainty: p.certainty,
        evidenceRefs: p.evidenceRefs,
        bscPerspectives: p.bscPerspectives,
        status: p.status,
      }));
    }

    if (!initiativeSnapshots || initiativeSnapshots.length === 0) {
      const initRows = await tx
        .select()
        .from(initiatives)
        .where(and(eq(initiatives.workspaceId, wsId), isNull(initiatives.deletedAt)));
      initiativeSnapshots = initRows.map((i) => ({
        id: String(i.id),
        title: i.title,
        status: i.status,
        approvalStatus: i.approvalStatus,
        strategicObjectiveId: null,
        sourceTowsOptionId: null,
        targetDate: i.targetDate ? i.targetDate.toISOString() : null,
        milestones: i.milestones,
      }));
    }

    if (!krSnapshots || krSnapshots.length === 0) {
      const krRows = await tx
        .select()
        .from(keyResults)
        .where(and(eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)));
      krSnapshots = krRows.map((k) => ({
        id: String(k.id),
        objectiveId: String(k.objectiveId),
        title: k.title,
        baselineValue: k.baselineValue,
        currentValue: k.currentValue,
        targetValue: k.targetValue,
        unit: k.unit,
        scoringType: k.scoringType,
        status: k.status,
      }));
    }

    const actorMemberId = ctx.userId ? BigInt(ctx.userId) : null;
    const now = new Date();

    const [updated] = await tx
      .update(cycleReviews)
      .set({
        status: "COMPLETED",
        conclusion: input.conclusion !== undefined ? input.conclusion : review.conclusion,
        decisionId: linkedDecisionId,
        conductedByMemberId: actorMemberId,
        conductedAt: now,
        pestelSnapshots,
        initiativeSnapshots,
        krSnapshots,
        revision: review.revision + 1,
        updatedAt: now,
      })
      .where(eq(cycleReviews.id, review.id))
      .returning();

    return toCycleReviewView(updated!);
  });
}
