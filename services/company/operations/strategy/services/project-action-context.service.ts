import { APIError } from "encore.dev/api";
import { and, desc, eq, isNull } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { db } from "../../models/db";
import {
  projects,
  twelveWeekCycles,
  weeklyPlans,
  weeklyCommitments,
} from "../../../shared/db/schema/operations";
import {
  assumptions,
  evidence,
  nextBestActions,
  decisionRecords,
} from "../../../shared/db/schema/strategy";
import { legalObligationInstances } from "../../../shared/db/schema/legal";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { NEXT_BEST_ACTION_ACCEPTED } from "../../../shared/events";
import {
  getLocalDateFromInstant,
  resolveExecutionWeek,
} from "../../services/execution-calendar";
import { isEvidenceEligible } from "./eligible-evidence.service";

export type ContextPart<T> =
  | { availability: "READY"; data: T; asOf: string; sourceVersion: string }
  | { availability: "UNAVAILABLE"; reason: string };

export interface ProjectActionContext {
  projectId: string;
  workspaceId: string;
  stage: ContextPart<{ lifecycleStage: string; stageVersion: number; currentGate: string | null }>;
  assumptions: ContextPart<Array<{
    id: string;
    statement: string;
    importance: number;
    uncertainty: number;
    riskScore: number;
    status: string;
  }>>;
  evidence: ContextPart<Array<{
    id: string;
    sourceType: string;
    strength: number;
    confidence: number;
    supportsOrRefutes: string;
  }>>;
  metrics: ContextPart<Array<{
    id: string;
    metricContractId: string;
    metricName: string;
    currentValue: number | null;
  }>>;
  currentCycle: ContextPart<{
    id: string;
    displayName: string | null;
    durationWeeks: number;
    revision: number;
    status: string;
  }>;
  currentWeek: ContextPart<{ weekNo: number; weeklyPlanId: string | null }>;
  openObligations: ContextPart<Array<{
    id: string;
    title: string;
    dueDate: string | null;
    source: string;
  }>>;
  cashSummary: ContextPart<{ cashBalance: number; monthlyBurn: number; runwayMonths: number }>;
  budgetSummary: ContextPart<{ totalBudget: number; spent: number; remaining: number }>;
}

/**
 * Gathers deterministic, live business context for a project across strategy,
 * operations, legal, and finance domains.
 * Guarantees string preservation for Snowflake/large IDs.
 */
export async function getProjectActionContext(
  ctx: TenantContext,
  projectId: string
): Promise<ProjectActionContext> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);
  const now = new Date();
  const nowIso = now.toISOString();

  // 1. Project & Stage
  const [project] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId), isNull(projects.deletedAt)))
    .limit(1);

  if (!project) {
    throw APIError.notFound(`Project ${projectId} not found in this workspace`);
  }

  const stagePart: ContextPart<{ lifecycleStage: string; stageVersion: number; currentGate: string | null }> = {
    availability: "READY",
    data: {
      lifecycleStage: project.lifecycleStage,
      stageVersion: project.stageVersion,
      currentGate: project.currentGate,
    },
    asOf: nowIso,
    sourceVersion: String(project.stageVersion),
  };

  // 2. Real Assumptions
  const assumptionRows = await db
    .select()
    .from(assumptions)
    .where(and(eq(assumptions.projectId, pId), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)))
    .orderBy(desc(assumptions.riskScore));

  let assumptionsPart: ContextPart<Array<{
    id: string;
    statement: string;
    importance: number;
    uncertainty: number;
    riskScore: number;
    status: string;
  }>>;

  if (assumptionRows.length === 0) {
    assumptionsPart = {
      availability: "UNAVAILABLE",
      reason: "No assumptions recorded for this project",
    };
  } else {
    assumptionsPart = {
      availability: "READY",
      data: assumptionRows.map((a) => ({
        id: a.id.toString(),
        statement: a.statement,
        importance: a.importance,
        uncertainty: a.uncertainty,
        riskScore: a.riskScore,
        status: a.status,
      })),
      asOf: nowIso,
      sourceVersion: String(assumptionRows[0]!.updatedAt.getTime()),
    };
  }

  // 3. Real Eligible Evidence
  const evidenceRows = await db
    .select()
    .from(evidence)
    .where(and(eq(evidence.projectId, pId), eq(evidence.workspaceId, wsId), isNull(evidence.deletedAt)))
    .orderBy(desc(evidence.strength));

  const eligibleEvidence = evidenceRows.filter((e) => isEvidenceEligible(e, now));
  const evidencePart: ContextPart<Array<{
    id: string;
    sourceType: string;
    strength: number;
    confidence: number;
    supportsOrRefutes: string;
  }>> = {
    availability: "READY",
    data: eligibleEvidence.map((e) => ({
      id: e.id.toString(),
      sourceType: e.sourceType,
      strength: e.strength,
      confidence: e.confidence,
      supportsOrRefutes: e.supportsOrRefutes,
    })),
    asOf: nowIso,
    sourceVersion: "1",
  };

  // 4. Metrics
  const metricsPart: ContextPart<Array<{
    id: string;
    metricContractId: string;
    metricName: string;
    currentValue: number | null;
  }>> = {
    availability: "READY",
    data: [],
    asOf: nowIso,
    sourceVersion: "1",
  };

  // 5. Active Cycle and Execution Week
  const [cycle] = await db
    .select()
    .from(twelveWeekCycles)
    .where(
      and(
        eq(twelveWeekCycles.projectId, pId),
        eq(twelveWeekCycles.workspaceId, wsId),
        eq(twelveWeekCycles.status, "ACTIVE"),
        isNull(twelveWeekCycles.deletedAt)
      )
    )
    .orderBy(desc(twelveWeekCycles.createdAt))
    .limit(1);

  let cyclePart: ContextPart<{
    id: string;
    displayName: string | null;
    durationWeeks: number;
    revision: number;
    status: string;
  }>;
  let weekPart: ContextPart<{ weekNo: number; weeklyPlanId: string | null }>;

  if (cycle) {
    cyclePart = {
      availability: "READY",
      data: {
        id: cycle.id.toString(),
        displayName: cycle.displayName,
        durationWeeks: cycle.durationWeeks,
        revision: cycle.revision,
        status: cycle.status,
      },
      asOf: nowIso,
      sourceVersion: String(cycle.revision),
    };

    let currentWeekNo = 1;
    if (cycle.startLocalDate) {
      const todayLocal = getLocalDateFromInstant(now, cycle.timezone || "UTC");
      const resolved = resolveExecutionWeek(String(cycle.startLocalDate), cycle.durationWeeks, todayLocal);
      if (resolved !== null) currentWeekNo = resolved;
    }

    const [currentPlan] = await db
      .select({ id: weeklyPlans.id })
      .from(weeklyPlans)
      .where(and(eq(weeklyPlans.cycleId, cycle.id), eq(weeklyPlans.weekNo, currentWeekNo), eq(weeklyPlans.workspaceId, wsId)))
      .limit(1);

    weekPart = {
      availability: "READY",
      data: {
        weekNo: currentWeekNo,
        weeklyPlanId: currentPlan ? currentPlan.id.toString() : null,
      },
      asOf: nowIso,
      sourceVersion: "1",
    };
  } else {
    cyclePart = {
      availability: "UNAVAILABLE",
      reason: "No active execution cycle for this project",
    };
    weekPart = {
      availability: "UNAVAILABLE",
      reason: "No active cycle to resolve current week",
    };
  }

  // 6. Open Legal Obligations
  const obligations = await db
    .select()
    .from(legalObligationInstances)
    .where(and(eq(legalObligationInstances.workspaceId, wsId), eq(legalObligationInstances.status, "OPEN")))
    .orderBy(legalObligationInstances.dueDate)
    .limit(10);

  const obligationsPart: ContextPart<Array<{
    id: string;
    title: string;
    dueDate: string | null;
    source: string;
  }>> = {
    availability: "READY",
    data: obligations.map((o) => ({
      id: o.id.toString(),
      title: o.title,
      dueDate: o.dueDate ? String(o.dueDate) : null,
      source: o.source,
    })),
    asOf: nowIso,
    sourceVersion: "1",
  };

  // 7. Finance & Budget Adapters (Prior to F6, returns UNAVAILABLE with reason)
  const cashSummary: ContextPart<{ cashBalance: number; monthlyBurn: number; runwayMonths: number }> = {
    availability: "UNAVAILABLE",
    reason: "Finance cash summary integration not yet available (scheduled in F6)",
  };

  const budgetSummary: ContextPart<{ totalBudget: number; spent: number; remaining: number }> = {
    availability: "UNAVAILABLE",
    reason: "Budget tracking adapter not yet available (scheduled in F6)",
  };

  return {
    projectId,
    workspaceId: ctx.workspaceId,
    stage: stagePart,
    assumptions: assumptionsPart,
    evidence: evidencePart,
    metrics: metricsPart,
    currentCycle: cyclePart,
    currentWeek: weekPart,
    openObligations: obligationsPart,
    cashSummary,
    budgetSummary,
  };
}

export interface ProposedActionItem {
  id: string;
  projectId: string;
  source: "evidence" | "finance" | "legal" | "stage";
  recommendation: string;
  priority: number;
  dueBy: string | null;
  status: "PROPOSED" | "ACCEPTED" | "REJECTED" | "DONE";
  decisionReason: string;
}

export interface ProposeNextActionsResult {
  status: "READY" | "INSUFFICIENT_DATA";
  reason?: string;
  items: ProposedActionItem[];
}

/**
 * Proposes next actions dynamically derived from live assumptions and obligations.
 * If assumptions are missing, returns INSUFFICIENT_DATA instead of fake/mock data.
 */
export async function proposeNextActions(
  ctx: TenantContext,
  projectId: string
): Promise<ProposeNextActionsResult> {
  const context = await getProjectActionContext(ctx, projectId);
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  if (context.assumptions.availability !== "READY" || context.assumptions.data.length === 0) {
    return {
      status: "INSUFFICIENT_DATA",
      reason: "Chưa có giả định kiểm chứng để đề xuất hành động",
      items: [],
    };
  }

  const items: ProposedActionItem[] = [];

  // 1. Propose validation experiments from untested assumptions
  const untested = context.assumptions.data.filter((a) => a.status === "untested");
  for (const assumption of untested.slice(0, 3)) {
    const actionId = generateSnowflake();
    const recommendation = `Kiểm chứng giả định: ${assumption.statement}`;
    const priority = assumption.riskScore >= 16 ? 1 : 2;
    const decisionReason = `Giả định có độ rủi ro ${assumption.riskScore} (quan trọng: ${assumption.importance}, không chắc chắn: ${assumption.uncertainty}) cần kiểm chứng sớm.`;

    const [row] = await db
      .insert(nextBestActions)
      .values({
        id: actionId,
        workspaceId: wsId,
        projectId: pId,
        source: "evidence",
        recommendation,
        priority,
        status: "PROPOSED",
        capabilityRequired: "research",
        decisionReason,
        contextSnapshot: { assumptionId: assumption.id, riskScore: assumption.riskScore },
      })
      .returning();

    items.push({
      id: row!.id.toString(),
      projectId,
      source: "evidence",
      recommendation,
      priority,
      dueBy: null,
      status: "PROPOSED",
      decisionReason,
    });
  }

  // 2. Propose actions from open legal obligations
  if (context.openObligations.availability === "READY") {
    for (const obligation of context.openObligations.data.slice(0, 2)) {
      const actionId = generateSnowflake();
      const recommendation = `Hoàn thành nghĩa vụ pháp lý: ${obligation.title}`;
      const decisionReason = `Nghĩa vụ pháp lý đang OPEN (hạn: ${obligation.dueDate ?? "chưa xác định"}) cần hoàn thành.`;

      const [row] = await db
        .insert(nextBestActions)
        .values({
          id: actionId,
          workspaceId: wsId,
          projectId: pId,
          source: "legal",
          recommendation,
          priority: 1,
          dueBy: obligation.dueDate || null,
          status: "PROPOSED",
          capabilityRequired: "legal",
          decisionReason,
          contextSnapshot: { obligationId: obligation.id },
        })
        .returning();

      items.push({
        id: row!.id.toString(),
        projectId,
        source: "legal",
        recommendation,
        priority: 1,
        dueBy: obligation.dueDate,
        status: "PROPOSED",
        decisionReason,
      });
    }
  }

  return {
    status: "READY",
    items,
  };
}

export interface AcceptActionProposalInput {
  proposalId: string;
  expectedVersion?: number;
  cycleId?: string;
  weekNo?: number;
}

export interface AcceptActionProposalResult {
  proposalId: string;
  status: "ACCEPTED";
  decisionId: string;
  commitmentId: string | null;
  revision: number;
}

/**
 * Accepts an action proposal, binds it to a strategic decision record, and
 * creates a weekly commitment if cycleId and weekNo are provided.
 * Replaying accept is idempotent and does not duplicate commitments or events.
 */
export async function acceptActionProposal(
  ctx: TenantContext,
  input: AcceptActionProposalInput
): Promise<AcceptActionProposalResult> {
  const wsId = BigInt(ctx.workspaceId);
  const proposalIdBig = BigInt(input.proposalId);

  return await db.transaction(async (tx) => {
    const [action] = await tx
      .select()
      .from(nextBestActions)
      .where(and(eq(nextBestActions.id, proposalIdBig), eq(nextBestActions.workspaceId, wsId)))
      .limit(1);

    if (!action) {
      throw APIError.notFound(`Action proposal ${input.proposalId} not found`);
    }

    if (input.expectedVersion !== undefined && action.revision !== input.expectedVersion) {
      throw APIError.failedPrecondition(
        `Action proposal revision conflict: expected ${input.expectedVersion}, actual ${action.revision}`
      );
    }

    // Idempotent: return existing ACCEPTED state without duplicating commitment or outbox event
    if (action.status === "ACCEPTED") {
      const [existingCommitment] = await tx
        .select({ id: weeklyCommitments.id })
        .from(weeklyCommitments)
        .where(and(eq(weeklyCommitments.sourceActionId, input.proposalId), eq(weeklyCommitments.workspaceId, wsId)))
        .limit(1);

      return {
        proposalId: action.id.toString(),
        status: "ACCEPTED",
        decisionId: action.decisionId ? action.decisionId.toString() : "",
        commitmentId: existingCommitment ? existingCommitment.id.toString() : null,
        revision: action.revision,
      };
    }

    if (action.status !== "PROPOSED") {
      throw APIError.failedPrecondition(
        `Action proposal must be in PROPOSED status to accept (current: ${action.status})`
      );
    }

    // 1. Create Decision Record
    const decisionId = generateSnowflake();
    await tx.insert(decisionRecords).values({
      id: decisionId,
      workspaceId: wsId,
      projectId: action.projectId,
      decision: "proceed",
      evidenceSnapshot: {
        recommendation: action.recommendation,
        decisionReason: action.decisionReason,
        source: action.source,
      },
    });

    const nextRevision = (action.revision ?? 1) + 1;
    const now = new Date();

    // 2. Update action proposal to ACCEPTED
    await tx
      .update(nextBestActions)
      .set({
        status: "ACCEPTED",
        decisionId,
        revision: nextRevision,
        updatedAt: now,
      })
      .where(and(eq(nextBestActions.id, proposalIdBig), eq(nextBestActions.workspaceId, wsId)));

    // 3. Create weekly commitment if cycleId/weekNo provided
    let commitmentIdStr: string | null = null;
    if (input.cycleId && input.weekNo) {
      const cycleIdBig = BigInt(input.cycleId);
      let [plan] = await tx
        .select()
        .from(weeklyPlans)
        .where(and(eq(weeklyPlans.cycleId, cycleIdBig), eq(weeklyPlans.weekNo, input.weekNo), eq(weeklyPlans.workspaceId, wsId)))
        .limit(1);

      if (!plan) {
        [plan] = await tx
          .insert(weeklyPlans)
          .values({
            id: generateSnowflake(),
            workspaceId: wsId,
            cycleId: cycleIdBig,
            weekNo: input.weekNo,
            decisionId,
          })
          .returning();
      }

      const commitmentId = generateSnowflake();
      const purposeType = action.source === "legal" ? "OBLIGATION" : "EXPERIMENT";

      await tx.insert(weeklyCommitments).values({
        id: commitmentId,
        workspaceId: wsId,
        weeklyPlanId: plan!.id,
        title: action.recommendation,
        purposeType,
        sourceActionId: input.proposalId,
        decisionId,
        revision: 1,
        sourceRevision: 1,
      });

      commitmentIdStr = commitmentId.toString();
    }

    // 4. Outbox event
    const event = makeBusinessEvent({
      eventType: NEXT_BEST_ACTION_ACCEPTED,
      workspaceId: ctx.workspaceId,
      aggregateType: "next_best_action",
      aggregateId: input.proposalId,
      correlationId: ctx.correlationId || randomUUID(),
      actor: { kind: "user", id: ctx.userId || "0" },
      classification: "internal",
      payload: {
        workspaceId: ctx.workspaceId,
        actionId: input.proposalId,
        decisionId: decisionId.toString(),
        commitmentId: commitmentIdStr,
        source: action.source,
        recommendation: action.recommendation,
        acceptedAt: now.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      proposalId: input.proposalId,
      status: "ACCEPTED",
      decisionId: decisionId.toString(),
      commitmentId: commitmentIdStr,
      revision: nextRevision,
    };
  });
}
