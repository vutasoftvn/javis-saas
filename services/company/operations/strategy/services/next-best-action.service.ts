import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { NEXT_BEST_ACTION_ACCEPTED } from "../../../shared/events";
import { randomUUID } from "node:crypto";
import { JsonObject, JsonValue, toJsonObject, toJsonArray } from "./strategy-json";

const {
  nextBestActions,
  ventureProfiles,
  financialSnapshots,
  legalObligationInstances,
  initiatives,
} = schema;

export type NextBestActionSource = "evidence" | "finance" | "legal" | "stage";
export type NextBestActionStatus = "PROPOSED" | "ACCEPTED" | "REJECTED" | "DONE";

export interface NextBestActionView {
  id: string;
  workspaceId: string;
  source: NextBestActionSource;
  recommendation: string;
  priority: number;
  dueBy: string | null;
  status: NextBestActionStatus;
  capabilityRequired: string | null;
  decisionReason: string;
  contextSnapshot: JsonObject;
  evidenceRefs: JsonValue[];
  regulationRefs: JsonValue[];
  createdAt: string;
  updatedAt: string;
}

export interface ActionContext {
  workspaceId: string;
  ventureProfile: {
    problemStatement: string | null;
    targetCustomer: string | null;
    industry: string | null;
    founderGoal: string | null;
    initialRunwayMonths: number | null;
  } | null;
  latestFinancialSnapshot: {
    snapshotDate: string;
    cashIn: string;
    cashOut: string;
    netBurn: string;
    runwayMonths: string | null;
  } | null;
  pendingObligationsCount: number;
  pendingObligations: Array<{
    id: string;
    title: string;
    dueDate: string | null;
  }>;
  activeInitiatives: Array<{
    id: string;
    title: string;
  }>;
  timestamp: string;
}

export async function assembleActionContextService(workspaceId: bigint): Promise<ActionContext> {
  // Deterministic context gathering without LLM
  const [profile] = await db
    .select()
    .from(ventureProfiles)
    .where(eq(ventureProfiles.workspaceId, workspaceId));

  const snapshots = await db
    .select()
    .from(financialSnapshots)
    .where(eq(financialSnapshots.workspaceId, workspaceId))
    .orderBy(desc(financialSnapshots.snapshotDate))
    .limit(1);

  const pendingObligations = await db
    .select()
    .from(legalObligationInstances)
    .where(
      and(
        eq(legalObligationInstances.workspaceId, workspaceId),
        eq(legalObligationInstances.status, "PENDING")
      )
    )
    .limit(5);

  const activeInitiatives = await db
    .select()
    .from(initiatives)
    .where(
      and(
        eq(initiatives.workspaceId, workspaceId),
        eq(initiatives.status, "active")
      )
    )
    .limit(5);

  return {
    workspaceId: String(workspaceId),
    ventureProfile: profile
      ? {
          problemStatement: profile.problemStatement,
          targetCustomer: profile.targetCustomer,
          industry: profile.industry,
          founderGoal: profile.founderGoal,
          initialRunwayMonths: profile.initialRunwayMonths,
        }
      : null,
    latestFinancialSnapshot: snapshots[0]
      ? {
          snapshotDate: snapshots[0].snapshotDate,
          cashIn: snapshots[0].cashIn,
          cashOut: snapshots[0].cashOut,
          netBurn: snapshots[0].netBurn,
          runwayMonths: snapshots[0].runwayMonths,
        }
      : null,
    pendingObligationsCount: pendingObligations.length,
    pendingObligations: pendingObligations.map((o) => ({
      id: String(o.id),
      title: o.title,
      dueDate: typeof o.dueDate === "string" ? o.dueDate : (o.dueDate ? new Date(o.dueDate).toISOString().split("T")[0] : null),
    })),
    activeInitiatives: activeInitiatives.map((i) => ({
      id: String(i.id),
      title: i.title,
    })),
    timestamp: new Date().toISOString(),
  };
}

export interface NextActionCandidateInput {
  projectId: number;
  untestedAssumptions?: Array<{ id: number; statement: string; importance: number; uncertainty: number }>;
  blockedTasks?: Array<{ id: number; title: string; priority: string; status: string }>;
  okrGaps?: Array<{ id: number; title: string; currentValue: number; targetValue: number; gapPercentage: number }>;
}

export interface RankedNextAction {
  rank: number;
  candidate: {
    source: "assumption" | "task" | "okr_gap";
    refId: number;
    score: number;
    title?: string;
  };
  llmRerankNote?: string | null;
}

export function generateAndRankNextActions(input: NextActionCandidateInput): RankedNextAction[] {
  const candidates: Array<{ source: "assumption" | "task" | "okr_gap"; refId: number; score: number; title?: string }> = [];

  if (input.untestedAssumptions) {
    for (const a of input.untestedAssumptions) {
      const score = 50 + Math.round((a.importance * a.uncertainty) * 0.45);
      candidates.push({ source: "assumption", refId: a.id, score, title: a.statement });
    }
  }

  if (input.blockedTasks) {
    for (const t of input.blockedTasks) {
      let score = 50;
      if (t.priority === "urgent") score = 90;
      else if (t.priority === "high") score = 70;
      candidates.push({ source: "task", refId: t.id, score, title: t.title });
    }
  }

  if (input.okrGaps) {
    for (const g of input.okrGaps) {
      const score = 55 + Math.round(g.gapPercentage * 0.3);
      candidates.push({ source: "okr_gap", refId: g.id, score, title: g.title });
    }
  }

  // Sort descending by score
  candidates.sort((a, b) => b.score - a.score);

  return candidates.map((candidate, idx) => ({
    rank: idx + 1,
    candidate,
    llmRerankNote: null,
  }));
}

export interface CreateActionProposalServiceInput {
  workspaceId: bigint;
  source: NextBestActionSource;
  recommendation: string;
  priority?: number;
  dueBy?: string;
  capabilityRequired?: string;
  decisionReason: string;
  contextSnapshot?: JsonObject;
  evidenceRefs?: JsonValue[];
  regulationRefs?: JsonValue[];
}

export async function createActionProposalService(p: CreateActionProposalServiceInput): Promise<NextBestActionView> {
  if (!p.decisionReason) {
    throw APIError.invalidArgument("decisionReason is strictly required for all action proposals");
  }

  // Check forbidden payout capability
  if (p.capabilityRequired && (p.capabilityRequired === "finance.payout.execute" || p.capabilityRequired.includes("payout"))) {
    throw APIError.invalidArgument(`Capability '${p.capabilityRequired}' does not exist or is forbidden`);
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(nextBestActions)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      source: p.source,
      recommendation: p.recommendation,
      priority: p.priority ?? 1,
      dueBy: p.dueBy ?? null,
      capabilityRequired: p.capabilityRequired ?? null,
      decisionReason: p.decisionReason,
      contextSnapshot: p.contextSnapshot ?? {},
      evidenceRefs: p.evidenceRefs ?? [],
      regulationRefs: p.regulationRefs ?? [],
      status: "PROPOSED",
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    source: created.source as NextBestActionSource,
    recommendation: created.recommendation,
    priority: created.priority,
    dueBy: created.dueBy ? (typeof created.dueBy === "string" ? created.dueBy : new Date(created.dueBy).toISOString().split("T")[0]) : null,
    status: created.status as NextBestActionStatus,
    capabilityRequired: created.capabilityRequired,
    decisionReason: created.decisionReason,
    contextSnapshot: toJsonObject(created.contextSnapshot),
    evidenceRefs: toJsonArray(created.evidenceRefs),
    regulationRefs: toJsonArray(created.regulationRefs),
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}

export async function listActionProposalsService(
  workspaceId: bigint,
  status?: string
): Promise<NextBestActionView[]> {
  const rows = await db
    .select()
    .from(nextBestActions)
    .where(eq(nextBestActions.workspaceId, workspaceId))
    .orderBy(desc(nextBestActions.priority), desc(nextBestActions.createdAt));

  let filtered = rows;
  if (status) {
    filtered = rows.filter((r) => r.status.toUpperCase() === status.toUpperCase());
  }

  return filtered.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    source: r.source as NextBestActionSource,
    recommendation: r.recommendation,
    priority: r.priority,
    dueBy: r.dueBy ? (typeof r.dueBy === "string" ? r.dueBy : new Date(r.dueBy).toISOString().split("T")[0]) : null,
    status: r.status as NextBestActionStatus,
    capabilityRequired: r.capabilityRequired,
    decisionReason: r.decisionReason,
    contextSnapshot: toJsonObject(r.contextSnapshot),
    evidenceRefs: toJsonArray(r.evidenceRefs),
    regulationRefs: toJsonArray(r.regulationRefs),
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

export async function acceptActionProposalService(p: {
  proposalId: bigint;
  acceptedBy: bigint;
}): Promise<NextBestActionView> {
  return await db.transaction(async (tx) => {
    const [action] = await tx
      .select()
      .from(nextBestActions)
      .where(eq(nextBestActions.id, p.proposalId));

    if (!action) {
      throw APIError.notFound(`Next best action proposal '${p.proposalId}' not found`);
    }

    const now = new Date();
    const [updated] = await tx
      .update(nextBestActions)
      .set({
        status: "ACCEPTED",
        updatedAt: now,
      })
      .where(eq(nextBestActions.id, p.proposalId))
      .returning();

    const event = makeBusinessEvent({
      eventType: NEXT_BEST_ACTION_ACCEPTED,
      workspaceId: String(updated.workspaceId),
      aggregateType: "next_best_action",
      aggregateId: String(updated.id),
      correlationId: randomUUID(),
      actor: {
        kind: "user",
        id: String(p.acceptedBy),
      },
      classification: "internal",
      payload: {
        workspaceId: String(updated.workspaceId),
        actionId: String(updated.id),
        source: updated.source,
        recommendation: updated.recommendation,
        capabilityRequired: updated.capabilityRequired,
        acceptedAt: now.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      source: updated.source as NextBestActionSource,
      recommendation: updated.recommendation,
      priority: updated.priority,
      dueBy: updated.dueBy ? (typeof updated.dueBy === "string" ? updated.dueBy : new Date(updated.dueBy).toISOString().split("T")[0]) : null,
      status: "ACCEPTED",
      capabilityRequired: updated.capabilityRequired,
      decisionReason: updated.decisionReason,
      contextSnapshot: toJsonObject(updated.contextSnapshot),
      evidenceRefs: toJsonArray(updated.evidenceRefs),
      regulationRefs: toJsonArray(updated.regulationRefs),
      createdAt: updated.createdAt.toISOString(),
      updatedAt: updated.updatedAt.toISOString(),
    };
  });
}
