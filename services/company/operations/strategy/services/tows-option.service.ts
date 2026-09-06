import { eq, and, desc, inArray } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import {
  strategicObjectives,
  swotItems,
  towsOptions,
  towsOptionEvaluations,
} from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { getWorkspaceStrategySettings } from "./workspace-strategy-settings.service";
import { requireStrategyGovernanceAuthority } from "./strategy-governance-authorization.service";
import { recordTowsDecision } from "./decision-recording.service";

export type TowsQuadrant = "SO" | "WO" | "ST" | "WT";
export const VALID_TOWS_QUADRANTS: readonly TowsQuadrant[] = [
  "SO",
  "WO",
  "ST",
  "WT",
] as const;

export type TowsOptionStatus =
  | "DRAFT"
  | "PROPOSED"
  | "SELECTED"
  | "REJECTED"
  | "SUPERSEDED";
export const VALID_TOWS_STATUSES: readonly TowsOptionStatus[] = [
  "DRAFT",
  "PROPOSED",
  "SELECTED",
  "REJECTED",
  "SUPERSEDED",
] as const;

export type TowsScorerKind = "HUMAN" | "AI_AGENT";

export interface TowsOptionEvaluation {
  id: string;
  workspaceId: string;
  towsOptionId: string;
  impactScore: number;
  difficultyScore: number;
  priorityScore: number;
  rationale: string | null;
  scoredByMemberId: string | null;
  scorerKind: TowsScorerKind;
  createdAt: string;
}

export interface TowsOption {
  id: string;
  workspaceId: string;
  strategicObjectiveId: string;
  quadrant: TowsQuadrant;
  title: string;
  rationale: string | null;
  swotItemIds: string[];
  status: TowsOptionStatus;
  aiProvenance: Record<string, any> | null;
  selectedByMemberId: string | null;
  selectedAt: string | null;
  decisionId: string | null;
  createdByMemberId: string | null;
  updatedByMemberId: string | null;
  revision: number;
  createdAt: string;
  updatedAt: string;
  evaluations?: TowsOptionEvaluation[];
  impactScore?: number | null;
  difficultyScore?: number | null;
  priorityScore?: number | null;
}

export interface CreateTowsOptionInput {
  workspaceId: string | number | bigint;
  strategicObjectiveId: string | number | bigint;
  quadrant: TowsQuadrant;
  title: string;
  rationale?: string;
  swotItemIds?: string[];
  status?: "DRAFT" | "PROPOSED";
  aiProvenance?: Record<string, any>;
  createdByMemberId?: string | number | bigint;
}

export interface UpdateTowsOptionInput {
  id: string | number | bigint;
  workspaceId: string | number | bigint;
  quadrant?: TowsQuadrant;
  title?: string;
  rationale?: string;
  swotItemIds?: string[];
  expectedRevision?: number;
  updatedByMemberId?: string | number | bigint;
}

export interface CreateTowsOptionEvaluationInput {
  workspaceId: string | number | bigint;
  towsOptionId: string | number | bigint;
  impactScore: number;
  difficultyScore: number;
  rationale?: string;
  scorerKind?: TowsScorerKind;
  scoredByMemberId?: string | number | bigint;
}

export interface ListTowsOptionsInput {
  workspaceId: string | number | bigint;
  strategicObjectiveId: string | number | bigint;
  quadrant?: TowsQuadrant;
  status?: TowsOptionStatus;
}

export interface SelectTowsOptionInput {
  id: string | number | bigint;
  strategicObjectiveId?: string | number | bigint;
  reason?: string;
  supersedeOptionId?: string | number | bigint;
}

export interface RejectTowsOptionInput {
  id: string | number | bigint;
  reason?: string;
}

/**
 * Priority Score calculation:
 * priorityScore = impactScore * 2 - difficultyScore
 * Range: (1..5) * 2 - (1..5) = 2 - 5 = -3 (lowest) to 10 - 1 = 9 (highest)
 */
export function calculatePriorityScore(impact: number, difficulty: number): number {
  return impact * 2 - difficulty;
}

function toTowsOptionEvaluation(
  row: typeof towsOptionEvaluations.$inferSelect
): TowsOptionEvaluation {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    towsOptionId: row.towsOptionId.toString(),
    impactScore: row.impactScore,
    difficultyScore: row.difficultyScore,
    priorityScore: calculatePriorityScore(row.impactScore, row.difficultyScore),
    rationale: row.rationale,
    scoredByMemberId: row.scoredByMemberId ? row.scoredByMemberId.toString() : null,
    scorerKind: row.scorerKind as TowsScorerKind,
    createdAt: row.createdAt.toISOString(),
  };
}

function toTowsOption(
  row: typeof towsOptions.$inferSelect,
  evaluations?: TowsOptionEvaluation[]
): TowsOption {
  let impactScore: number | null = null;
  let difficultyScore: number | null = null;
  let priorityScore: number | null = null;

  if (evaluations && evaluations.length > 0) {
    const latest = evaluations[0];
    impactScore = latest.impactScore;
    difficultyScore = latest.difficultyScore;
    priorityScore = latest.priorityScore;
  }

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    strategicObjectiveId: row.strategicObjectiveId.toString(),
    quadrant: row.quadrant as TowsQuadrant,
    title: row.title,
    rationale: row.rationale,
    swotItemIds: (row.swotItemIds as string[]) || [],
    status: row.status as TowsOptionStatus,
    aiProvenance: (row.aiProvenance as Record<string, any>) || null,
    selectedByMemberId: row.selectedByMemberId ? row.selectedByMemberId.toString() : null,
    selectedAt: row.selectedAt ? row.selectedAt.toISOString() : null,
    decisionId: row.decisionId ? row.decisionId.toString() : null,
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
    evaluations,
    impactScore,
    difficultyScore,
    priorityScore,
  };
}

export async function createTowsOption(
  input: CreateTowsOptionInput
): Promise<TowsOption> {
  const wsId = BigInt(input.workspaceId);
  const objId = BigInt(input.strategicObjectiveId);

  // Validate objective exists in workspace
  const [obj] = await db
    .select()
    .from(strategicObjectives)
    .where(and(eq(strategicObjectives.id, objId), eq(strategicObjectives.workspaceId, wsId)))
    .limit(1);

  if (!obj) {
    throw APIError.notFound("Strategic objective not found in workspace");
  }

  if (!input.title || input.title.trim().length === 0) {
    throw APIError.invalidArgument("title is required");
  }

  if (!VALID_TOWS_QUADRANTS.includes(input.quadrant)) {
    throw APIError.invalidArgument(`Invalid quadrant: ${input.quadrant}. Must be one of: ${VALID_TOWS_QUADRANTS.join(", ")}`);
  }

  const status = input.status || "DRAFT";
  if (!["DRAFT", "PROPOSED"].includes(status)) {
    throw APIError.invalidArgument("Initial TOWS option status must be DRAFT or PROPOSED");
  }

  const swotItemIds = input.swotItemIds || [];
  if (swotItemIds.length > 0) {
    const swotBigInts = swotItemIds.map((id) => BigInt(id));
    const swotRows = await db
      .select()
      .from(swotItems)
      .where(
        and(
          eq(swotItems.workspaceId, wsId),
          eq(swotItems.strategicObjectiveId, objId),
          inArray(swotItems.id, swotBigInts)
        )
      );

    if (swotRows.length !== swotItemIds.length) {
      throw APIError.invalidArgument("One or more swotItemIds do not belong to this objective or workspace");
    }
  }

  const id = generateSnowflake();
  const createdBy = input.createdByMemberId ? BigInt(input.createdByMemberId) : null;

  const [row] = await db
    .insert(towsOptions)
    .values({
      id,
      workspaceId: wsId,
      strategicObjectiveId: objId,
      quadrant: input.quadrant,
      title: input.title.trim(),
      rationale: input.rationale || null,
      swotItemIds,
      status,
      aiProvenance: input.aiProvenance || null,
      createdByMemberId: createdBy,
      updatedByMemberId: createdBy,
      revision: 1,
    })
    .returning();

  return toTowsOption(row, []);
}

export async function updateTowsOption(
  input: UpdateTowsOptionInput
): Promise<TowsOption> {
  const wsId = BigInt(input.workspaceId);
  const id = BigInt(input.id);

  const [existing] = await db
    .select()
    .from(towsOptions)
    .where(and(eq(towsOptions.id, id), eq(towsOptions.workspaceId, wsId)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound("TOWS option not found");
  }

  if (["SELECTED", "REJECTED", "SUPERSEDED"].includes(existing.status)) {
    throw APIError.failedPrecondition(`Cannot update TOWS option with status ${existing.status}`);
  }

  if (input.expectedRevision !== undefined && existing.revision !== input.expectedRevision) {
    throw APIError.aborted(`Revision conflict: current revision is ${existing.revision}, expected ${input.expectedRevision}`);
  }

  if (input.quadrant && !VALID_TOWS_QUADRANTS.includes(input.quadrant)) {
    throw APIError.invalidArgument(`Invalid quadrant: ${input.quadrant}`);
  }

  if (input.title !== undefined && input.title.trim().length === 0) {
    throw APIError.invalidArgument("title cannot be empty");
  }

  const swotItemIds = input.swotItemIds ?? (existing.swotItemIds as string[]);
  if (input.swotItemIds && input.swotItemIds.length > 0) {
    const swotBigInts = input.swotItemIds.map((sid) => BigInt(sid));
    const swotRows = await db
      .select()
      .from(swotItems)
      .where(
        and(
          eq(swotItems.workspaceId, wsId),
          eq(swotItems.strategicObjectiveId, existing.strategicObjectiveId),
          inArray(swotItems.id, swotBigInts)
        )
      );

    if (swotRows.length !== input.swotItemIds.length) {
      throw APIError.invalidArgument("One or more swotItemIds do not belong to this objective or workspace");
    }
  }

  const updatedBy = input.updatedByMemberId ? BigInt(input.updatedByMemberId) : null;

  const [updated] = await db
    .update(towsOptions)
    .set({
      quadrant: input.quadrant || existing.quadrant,
      title: input.title ? input.title.trim() : existing.title,
      rationale: input.rationale !== undefined ? input.rationale : existing.rationale,
      swotItemIds,
      updatedByMemberId: updatedBy,
      revision: existing.revision + 1,
      updatedAt: new Date(),
    })
    .where(eq(towsOptions.id, id))
    .returning();

  return getTowsOption(id, wsId);
}

export async function createTowsOptionEvaluation(
  input: CreateTowsOptionEvaluationInput
): Promise<TowsOptionEvaluation> {
  const wsId = BigInt(input.workspaceId);
  const optionId = BigInt(input.towsOptionId);

  const [option] = await db
    .select()
    .from(towsOptions)
    .where(and(eq(towsOptions.id, optionId), eq(towsOptions.workspaceId, wsId)))
    .limit(1);

  if (!option) {
    throw APIError.notFound("TOWS option not found in workspace");
  }

  if (
    !Number.isInteger(input.impactScore) ||
    input.impactScore < 1 ||
    input.impactScore > 5
  ) {
    throw APIError.invalidArgument("impactScore must be an integer between 1 and 5");
  }

  if (
    !Number.isInteger(input.difficultyScore) ||
    input.difficultyScore < 1 ||
    input.difficultyScore > 5
  ) {
    throw APIError.invalidArgument("difficultyScore must be an integer between 1 and 5");
  }

  const scorerKind = input.scorerKind || "HUMAN";
  if (!["HUMAN", "AI_AGENT"].includes(scorerKind)) {
    throw APIError.invalidArgument("scorerKind must be HUMAN or AI_AGENT");
  }

  const id = generateSnowflake();
  const scoredBy = input.scoredByMemberId ? BigInt(input.scoredByMemberId) : null;

  const [row] = await db
    .insert(towsOptionEvaluations)
    .values({
      id,
      workspaceId: wsId,
      towsOptionId: optionId,
      impactScore: input.impactScore,
      difficultyScore: input.difficultyScore,
      rationale: input.rationale || null,
      scoredByMemberId: scoredBy,
      scorerKind,
    })
    .returning();

  return toTowsOptionEvaluation(row);
}

export async function getTowsOption(
  id: string | number | bigint,
  workspaceId: string | number | bigint
): Promise<TowsOption> {
  const wsId = BigInt(workspaceId);
  const optionId = BigInt(id);

  const [row] = await db
    .select()
    .from(towsOptions)
    .where(and(eq(towsOptions.id, optionId), eq(towsOptions.workspaceId, wsId)))
    .limit(1);

  if (!row) {
    throw APIError.notFound("TOWS option not found");
  }

  const evalRows = await db
    .select()
    .from(towsOptionEvaluations)
    .where(and(eq(towsOptionEvaluations.towsOptionId, optionId), eq(towsOptionEvaluations.workspaceId, wsId)))
    .orderBy(desc(towsOptionEvaluations.createdAt));

  const evaluations = evalRows.map(toTowsOptionEvaluation);
  return toTowsOption(row, evaluations);
}

export async function listTowsOptions(
  input: ListTowsOptionsInput
): Promise<{ items: TowsOption[] }> {
  const wsId = BigInt(input.workspaceId);
  const objId = BigInt(input.strategicObjectiveId);

  const conditions = [
    eq(towsOptions.workspaceId, wsId),
    eq(towsOptions.strategicObjectiveId, objId),
  ];

  if (input.quadrant) {
    conditions.push(eq(towsOptions.quadrant, input.quadrant));
  }

  if (input.status) {
    conditions.push(eq(towsOptions.status, input.status));
  }

  const rows = await db
    .select()
    .from(towsOptions)
    .where(and(...conditions));

  if (rows.length === 0) {
    return { items: [] };
  }

  const optionIds = rows.map((r) => r.id);
  const evalRows = await db
    .select()
    .from(towsOptionEvaluations)
    .where(
      and(
        eq(towsOptionEvaluations.workspaceId, wsId),
        inArray(towsOptionEvaluations.towsOptionId, optionIds)
      )
    )
    .orderBy(desc(towsOptionEvaluations.createdAt));

  const evalsByOptionId = new Map<string, TowsOptionEvaluation[]>();
  for (const evalRow of evalRows) {
    const optIdStr = evalRow.towsOptionId.toString();
    const existing = evalsByOptionId.get(optIdStr) || [];
    existing.push(toTowsOptionEvaluation(evalRow));
    evalsByOptionId.set(optIdStr, existing);
  }

  const items = rows.map((row) => {
    const optEvals = evalsByOptionId.get(row.id.toString()) || [];
    return toTowsOption(row, optEvals);
  });

  // Sort by priorityScore descending (nulls last), then title ascending
  items.sort((a, b) => {
    const aScore = a.priorityScore ?? -999;
    const bScore = b.priorityScore ?? -999;
    if (bScore !== aScore) {
      return bScore - aScore;
    }
    return a.title.localeCompare(b.title);
  });

  return { items };
}

export async function selectTowsOption(
  input: SelectTowsOptionInput,
  ctx: TenantContext
): Promise<TowsOption> {
  // Disallow AI agents from executing governance command
  if (
    (ctx as any).actorKind === "AI_AGENT" ||
    (ctx as any).isAgent === true ||
    ctx.membershipRole === "agent"
  ) {
    throw APIError.permissionDenied("Agent cannot perform governance decisions");
  }

  const wsId = BigInt(ctx.workspaceId);
  const targetOptionId = BigInt(input.id);

  // Require governance authority for strategy.option.select
  await requireStrategyGovernanceAuthority(ctx, "strategy.option.select", {
    workspaceId: ctx.workspaceId,
  });

  return await db.transaction(async (tx) => {
    // 1. Lock target option row
    const [targetOption] = await tx
      .select()
      .from(towsOptions)
      .where(and(eq(towsOptions.id, targetOptionId), eq(towsOptions.workspaceId, wsId)))
      .for("update");

    if (!targetOption) {
      throw APIError.notFound("TOWS option not found in workspace");
    }

    if (
      input.strategicObjectiveId &&
      targetOption.strategicObjectiveId !== BigInt(input.strategicObjectiveId)
    ) {
      throw APIError.invalidArgument("TOWS option does not belong to specified strategic objective");
    }

    const objId = targetOption.strategicObjectiveId;

    // 2. Lock strategic objective row to serialise selection limit check
    const [obj] = await tx
      .select()
      .from(strategicObjectives)
      .where(and(eq(strategicObjectives.id, objId), eq(strategicObjectives.workspaceId, wsId)))
      .for("update");

    if (!obj) {
      throw APIError.notFound("Strategic objective not found");
    }

    // 3. Ensure option is evaluated (impactScore and difficultyScore required)
    const evalRows = await tx
      .select()
      .from(towsOptionEvaluations)
      .where(
        and(
          eq(towsOptionEvaluations.towsOptionId, targetOptionId),
          eq(towsOptionEvaluations.workspaceId, wsId)
        )
      )
      .orderBy(desc(towsOptionEvaluations.createdAt));

    if (evalRows.length === 0) {
      throw APIError.failedPrecondition(
        "TOWS option must have at least one evaluation with impact_score and difficulty_score before selection"
      );
    }

    // 4. Validate all linked SWOT items are ACTIVE
    const swotIds = (targetOption.swotItemIds as string[]) || [];
    if (swotIds.length > 0) {
      const swotBigInts = swotIds.map((sid) => BigInt(sid));
      const swotRows = await tx
        .select()
        .from(swotItems)
        .where(
          and(
            eq(swotItems.workspaceId, wsId),
            eq(swotItems.strategicObjectiveId, objId),
            inArray(swotItems.id, swotBigInts)
          )
        );

      if (swotRows.length !== swotIds.length) {
        throw APIError.failedPrecondition("One or more linked SWOT items not found for this strategic objective");
      }

      for (const swot of swotRows) {
        if (swot.status !== "ACTIVE") {
          throw APIError.failedPrecondition(
            `Source SWOT item '${swot.statement}' is not ACTIVE (current status: ${swot.status}). All linked SWOT items must be ACTIVE.`
          );
        }
      }
    }

    // 5. Check workspace selection limit
    const settings = await getWorkspaceStrategySettings(String(wsId));
    const limit = settings.towsSelectionLimit;

    // 6. Fetch currently SELECTED options for this objective (locked)
    const currentlySelected = await tx
      .select()
      .from(towsOptions)
      .where(
        and(
          eq(towsOptions.workspaceId, wsId),
          eq(towsOptions.strategicObjectiveId, objId),
          eq(towsOptions.status, "SELECTED")
        )
      )
      .for("update");

    let effectiveSelected = [...currentlySelected];

    // 7. If supersedeOptionId is provided, mark it as SUPERSEDED in same transaction
    if (input.supersedeOptionId) {
      const supersedeId = BigInt(input.supersedeOptionId);
      const toSupersede = effectiveSelected.find((o) => o.id === supersedeId);
      if (!toSupersede) {
        throw APIError.notFound(
          `Option ${input.supersedeOptionId} specified to supersede is not currently SELECTED for this objective`
        );
      }

      await tx
        .update(towsOptions)
        .set({
          status: "SUPERSEDED",
          revision: toSupersede.revision + 1,
          updatedAt: new Date(),
        })
        .where(eq(towsOptions.id, supersedeId));

      effectiveSelected = effectiveSelected.filter((o) => o.id !== supersedeId);
    }

    // Check if target is already selected
    if (targetOption.status === "SELECTED") {
      const evaluations = evalRows.map(toTowsOptionEvaluation);
      return toTowsOption(targetOption, evaluations);
    }

    // Enforce selection limit
    if (effectiveSelected.length >= limit) {
      throw APIError.failedPrecondition(
        `TOWS selection limit of ${limit} reached for this strategic objective. Specify an option to supersede.`
      );
    }

    // 8. Build candidate ranking for audit record
    const allOptions = await tx
      .select()
      .from(towsOptions)
      .where(
        and(
          eq(towsOptions.workspaceId, wsId),
          eq(towsOptions.strategicObjectiveId, objId)
        )
      );

    const allOptionIds = allOptions.map((o) => o.id);
    const allEvals = await tx
      .select()
      .from(towsOptionEvaluations)
      .where(
        and(
          eq(towsOptionEvaluations.workspaceId, wsId),
          inArray(towsOptionEvaluations.towsOptionId, allOptionIds)
        )
      )
      .orderBy(desc(towsOptionEvaluations.createdAt));

    const candidateRanking = allOptions.map((opt) => {
      const optEval = allEvals.find((e) => e.towsOptionId === opt.id);
      return {
        optionId: opt.id.toString(),
        title: opt.title,
        quadrant: opt.quadrant,
        impactScore: optEval ? optEval.impactScore : undefined,
        difficultyScore: optEval ? optEval.difficultyScore : undefined,
        priorityScore: optEval
          ? calculatePriorityScore(optEval.impactScore, optEval.difficultyScore)
          : undefined,
        status: opt.id === targetOptionId ? "SELECTED" : opt.status,
      };
    });

    candidateRanking.sort((a, b) => {
      const aScore = a.priorityScore ?? -999;
      const bScore = b.priorityScore ?? -999;
      return bScore - aScore;
    });

    const selectedOptionIds = [
      ...effectiveSelected.map((o) => o.id.toString()),
      targetOptionId.toString(),
    ];

    const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

    // 9. Write audit record into strategy.decision_records
    const decisionId = await recordTowsDecision(
      {
        workspaceId: wsId,
        strategicObjectiveId: objId,
        towsOptionId: targetOptionId,
        action: "SELECTED",
        actorMemberId,
        actorRole: ctx.membershipRole,
        reason: input.reason,
        candidateRanking,
        selectedOptionIds,
        supersededOptionId: input.supersedeOptionId ? String(input.supersedeOptionId) : null,
        settingsRevision: settings.revision,
      },
      tx
    );

    // 10. Update target option to SELECTED
    const [updatedRow] = await tx
      .update(towsOptions)
      .set({
        status: "SELECTED",
        selectedByMemberId: actorMemberId,
        selectedAt: new Date(),
        decisionId: BigInt(decisionId),
        updatedByMemberId: actorMemberId,
        revision: targetOption.revision + 1,
        updatedAt: new Date(),
      })
      .where(eq(towsOptions.id, targetOptionId))
      .returning();

    const evaluations = evalRows.map(toTowsOptionEvaluation);
    return toTowsOption(updatedRow, evaluations);
  });
}

export async function rejectTowsOption(
  input: RejectTowsOptionInput,
  ctx: TenantContext
): Promise<TowsOption> {
  // Disallow AI agents from executing governance command
  if (
    (ctx as any).actorKind === "AI_AGENT" ||
    (ctx as any).isAgent === true ||
    ctx.membershipRole === "agent"
  ) {
    throw APIError.permissionDenied("Agent cannot perform governance decisions");
  }

  const wsId = BigInt(ctx.workspaceId);
  const targetOptionId = BigInt(input.id);

  // Require governance authority for strategy.option.select (covers selection and rejection)
  await requireStrategyGovernanceAuthority(ctx, "strategy.option.select", {
    workspaceId: ctx.workspaceId,
  });

  return await db.transaction(async (tx) => {
    const [targetOption] = await tx
      .select()
      .from(towsOptions)
      .where(and(eq(towsOptions.id, targetOptionId), eq(towsOptions.workspaceId, wsId)))
      .for("update");

    if (!targetOption) {
      throw APIError.notFound("TOWS option not found in workspace");
    }

    const settings = await getWorkspaceStrategySettings(String(wsId));
    const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

    const evalRows = await tx
      .select()
      .from(towsOptionEvaluations)
      .where(
        and(
          eq(towsOptionEvaluations.towsOptionId, targetOptionId),
          eq(towsOptionEvaluations.workspaceId, wsId)
        )
      )
      .orderBy(desc(towsOptionEvaluations.createdAt));

    const candidateRanking = [
      {
        optionId: targetOption.id.toString(),
        title: targetOption.title,
        quadrant: targetOption.quadrant,
        impactScore: evalRows[0]?.impactScore,
        difficultyScore: evalRows[0]?.difficultyScore,
        priorityScore: evalRows[0]
          ? calculatePriorityScore(evalRows[0].impactScore, evalRows[0].difficultyScore)
          : undefined,
        status: "REJECTED",
      },
    ];

    const decisionId = await recordTowsDecision(
      {
        workspaceId: wsId,
        strategicObjectiveId: targetOption.strategicObjectiveId,
        towsOptionId: targetOptionId,
        action: "REJECTED",
        actorMemberId,
        actorRole: ctx.membershipRole,
        reason: input.reason,
        candidateRanking,
        selectedOptionIds: [],
        settingsRevision: settings.revision,
      },
      tx
    );

    const [updatedRow] = await tx
      .update(towsOptions)
      .set({
        status: "REJECTED",
        decisionId: BigInt(decisionId),
        updatedByMemberId: actorMemberId,
        revision: targetOption.revision + 1,
        updatedAt: new Date(),
      })
      .where(eq(towsOptions.id, targetOptionId))
      .returning();

    const evaluations = evalRows.map(toTowsOptionEvaluation);
    return toTowsOption(updatedRow, evaluations);
  });
}
