import { APIError } from "encore.dev/api";
import { eq, and, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  onboardSessions,
  conversationTurns,
  onboardSnapshots,
  onboardIdentity,
  onboardValues,
  onboardStageScale,
  onboardFounders,
  onboardTeamCulture,
  onboardMarket,
  onboardCompetitors,
  onboardChallenges,
  onboardGoalsAmbition,
  onboardReviewCadence,
} = schema;

export type OnboardDimension =
  | "identity"
  | "stage_scale"
  | "founder"
  | "team_culture"
  | "market"
  | "challenges"
  | "goals_ambition";

export interface CadenceSeedConfig {
  dimension: OnboardDimension;
  cadence: "slow" | "medium" | "fast" | "event";
  intervalDays: number;
}

export const DEFAULT_CADENCES: CadenceSeedConfig[] = [
  { dimension: "identity", cadence: "slow", intervalDays: 180 },
  { dimension: "stage_scale", cadence: "fast", intervalDays: 14 },
  { dimension: "founder", cadence: "slow", intervalDays: 180 },
  { dimension: "team_culture", cadence: "medium", intervalDays: 60 },
  { dimension: "market", cadence: "medium", intervalDays: 60 },
  { dimension: "challenges", cadence: "fast", intervalDays: 14 },
  { dimension: "goals_ambition", cadence: "medium", intervalDays: 90 },
];

export async function seedReviewCadenceService(workspaceId: bigint): Promise<void> {
  const now = new Date();
  for (const config of DEFAULT_CADENCES) {
    const nextDue = new Date(now.getTime() + config.intervalDays * 86400000);
    await db
      .insert(onboardReviewCadence)
      .values({
        id: generateSnowflake(),
        workspaceId,
        dimension: config.dimension,
        cadence: config.cadence,
        intervalDays: config.intervalDays,
        lastReviewedAt: now,
        nextDueAt: nextDue,
      })
      .onConflictDoNothing();
  }
}

export async function startOnboardSessionService(params: {
  workspaceId: string;
  sessionType: "initial" | "partial_update" | "event_driven";
  summary?: string;
  metadata?: Record<string, unknown>;
}): Promise<{ sessionId: string; status: string }> {
  const wsId = BigInt(params.workspaceId);
  const sessionId = generateSnowflake();

  await db.insert(onboardSessions).values({
    id: sessionId,
    workspaceId: wsId,
    sessionType: params.sessionType,
    status: "in_progress",
    summary: params.summary,
    metadata: params.metadata || {},
  });

  return { sessionId: sessionId.toString(), status: "in_progress" };
}

export async function recordConversationTurnService(params: {
  sessionId: string;
  turnNumber: number;
  role: "user" | "assistant" | "system";
  content: string;
  dimension?: string;
}): Promise<{ turnId: string }> {
  const sId = BigInt(params.sessionId);
  const turnId = generateSnowflake();

  await db.insert(conversationTurns).values({
    id: turnId,
    sessionId: sId,
    turnNumber: params.turnNumber,
    role: params.role,
    content: params.content,
    dimension: params.dimension,
  });

  return { turnId: turnId.toString() };
}

export async function updateDimensionService(params: {
  workspaceId: string;
  sessionId: string;
  dimension: OnboardDimension;
  data: any;
}): Promise<{ success: boolean; dimension: string; recordId: string }> {
  const wsId = BigInt(params.workspaceId);
  const sId = BigInt(params.sessionId);
  const recordId = generateSnowflake();
  const now = new Date();

  // 1. Cập nhật bản ghi chiều (Append-only với is_current = true)
  switch (params.dimension) {
    case "identity": {
      await db.insert(onboardIdentity).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        whatTheyDo: params.data.whatTheyDo,
        whoTheyServe: params.data.whoTheyServe,
        foundingWhy: params.data.foundingWhy,
        oneSentencePitch: params.data.oneSentencePitch,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });

      if (Array.isArray(params.data.values)) {
        for (let i = 0; i < params.data.values.length; i++) {
          const v = params.data.values[i];
          await db.insert(onboardValues).values({
            id: generateSnowflake(),
            workspaceId: wsId,
            identityId: recordId,
            valueText: typeof v === "string" ? v : v.valueText,
            isFireWorthy: v.isFireWorthy ?? false,
            realityStatus: v.realityStatus ?? "real",
            displayOrder: i,
          });
        }
      }
      break;
    }

    case "stage_scale": {
      await db.insert(onboardStageScale).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        headcountFt: params.data.headcountFt,
        headcountContractor: params.data.headcountContractor,
        revenueArr: params.data.revenueArr ? String(params.data.revenueArr) : null,
        revenueCurrency: params.data.revenueCurrency || "USD",
        runwayMonths: params.data.runwayMonths ? String(params.data.runwayMonths) : null,
        stage: params.data.stage,
        whatBrokeLast90d: params.data.whatBrokeLast90d,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });
      break;
    }

    case "founder": {
      await db.insert(onboardFounders).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        founderName: params.data.founderName,
        role: params.data.role,
        superpower: params.data.superpower,
        blindSpots: params.data.blindSpots,
        archetype: params.data.archetype,
        whatKeepsUp: params.data.whatKeepsUp,
        cofounderCritique: params.data.cofounderCritique,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });
      break;
    }

    case "team_culture": {
      await db.insert(onboardTeamCulture).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        threeWords: params.data.threeWords || [],
        lastRealConflict: params.data.lastRealConflict,
        conflictResolution: params.data.conflictResolution,
        strongestLeader: params.data.strongestLeader,
        weakestLeader: params.data.weakestLeader,
        hasRealConflict: params.data.hasRealConflict,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });
      break;
    }

    case "market": {
      await db.insert(onboardMarket).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        marketDescription: params.data.marketDescription,
        unfairAdvantage: params.data.unfairAdvantage,
        competitiveThreat: params.data.competitiveThreat,
        hasRealCompetition: params.data.hasRealCompetition,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });

      if (Array.isArray(params.data.competitors)) {
        for (let i = 0; i < params.data.competitors.length; i++) {
          const comp = params.data.competitors[i];
          await db.insert(onboardCompetitors).values({
            id: generateSnowflake(),
            marketId: recordId,
            name: comp.name,
            whyWinning: comp.whyWinning,
            threatLevel: comp.threatLevel || "medium",
            displayOrder: i,
          });
        }
      }
      break;
    }

    case "challenges": {
      await db.insert(onboardChallenges).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        priorityProduct: params.data.priorityProduct,
        priorityGrowth: params.data.priorityGrowth,
        priorityPeople: params.data.priorityPeople,
        priorityMoney: params.data.priorityMoney,
        priorityOperations: params.data.priorityOperations,
        avoidedDecision: params.data.avoidedDecision,
        extraDayAnswer: params.data.extraDayAnswer,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });
      break;
    }

    case "goals_ambition": {
      await db.insert(onboardGoalsAmbition).values({
        id: recordId,
        workspaceId: wsId,
        sessionId: sId,
        goal12MonthsText: params.data.goal12MonthsText,
        goal36MonthsText: params.data.goal36MonthsText,
        exitOrientation: params.data.exitOrientation,
        personalSuccessDefinition: params.data.personalSuccessDefinition,
        notCaptured: params.data.notCaptured || [],
        isCurrent: true,
      });
      break;
    }

    default:
      throw APIError.invalidArgument(`Chiều onboarding không hợp lệ: ${params.dimension}`);
  }

  // 2. Cập nhật review cadence cho chiều này
  const cadenceRows = await db
    .select()
    .from(onboardReviewCadence)
    .where(
      and(
        eq(onboardReviewCadence.workspaceId, wsId),
        eq(onboardReviewCadence.dimension, params.dimension)
      )
    )
    .limit(1);

  const intervalDays = cadenceRows[0]?.intervalDays ?? 14;
  const nextDue = new Date(now.getTime() + intervalDays * 86400000);

  if (cadenceRows.length > 0) {
    await db
      .update(onboardReviewCadence)
      .set({
        lastReviewedAt: now,
        nextDueAt: nextDue,
      })
      .where(eq(onboardReviewCadence.id, cadenceRows[0].id));
  } else {
    await db.insert(onboardReviewCadence).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      dimension: params.dimension,
      cadence: "fast",
      intervalDays,
      lastReviewedAt: now,
      nextDueAt: nextDue,
    });
  }

  return { success: true, dimension: params.dimension, recordId: recordId.toString() };
}

export async function createSnapshotService(params: {
  workspaceId: string;
  sessionId: string;
  changeReason?: string;
  changedDimensions?: string[];
}): Promise<{ snapshotId: string; capturedAt: string }> {
  const wsId = BigInt(params.workspaceId);
  const sId = BigInt(params.sessionId);
  const snapshotId = generateSnowflake();

  // Truy vấn toàn bộ 7 chiều hiện tại
  const fullContext = await assembleCurrentCompanyContext(wsId);

  await db.insert(onboardSnapshots).values({
    id: snapshotId,
    workspaceId: wsId,
    sessionId: sId,
    fullContext,
    changedDimensions: params.changedDimensions || [],
    changeReason: params.changeReason || "Onboarding session snapshot",
    isCurrent: true,
  });

  return { snapshotId: snapshotId.toString(), capturedAt: new Date().toISOString() };
}

export async function assembleCurrentCompanyContext(workspaceId: bigint): Promise<Record<string, unknown>> {
  const [identity] = await db
    .select()
    .from(onboardIdentity)
    .where(and(eq(onboardIdentity.workspaceId, workspaceId), eq(onboardIdentity.isCurrent, true)))
    .limit(1);

  const values = identity
    ? await db
        .select()
        .from(onboardValues)
        .where(eq(onboardValues.identityId, identity.id))
        .orderBy(onboardValues.displayOrder)
    : [];

  const [stageScale] = await db
    .select()
    .from(onboardStageScale)
    .where(and(eq(onboardStageScale.workspaceId, workspaceId), eq(onboardStageScale.isCurrent, true)))
    .limit(1);

  const founders = await db
    .select()
    .from(onboardFounders)
    .where(and(eq(onboardFounders.workspaceId, workspaceId), eq(onboardFounders.isCurrent, true)));

  const [teamCulture] = await db
    .select()
    .from(onboardTeamCulture)
    .where(and(eq(onboardTeamCulture.workspaceId, workspaceId), eq(onboardTeamCulture.isCurrent, true)))
    .limit(1);

  const [market] = await db
    .select()
    .from(onboardMarket)
    .where(and(eq(onboardMarket.workspaceId, workspaceId), eq(onboardMarket.isCurrent, true)))
    .limit(1);

  const competitors = market
    ? await db
        .select()
        .from(onboardCompetitors)
        .where(eq(onboardCompetitors.marketId, market.id))
        .orderBy(onboardCompetitors.displayOrder)
    : [];

  const [challenges] = await db
    .select()
    .from(onboardChallenges)
    .where(and(eq(onboardChallenges.workspaceId, workspaceId), eq(onboardChallenges.isCurrent, true)))
    .limit(1);

  const [goalsAmbition] = await db
    .select()
    .from(onboardGoalsAmbition)
    .where(and(eq(onboardGoalsAmbition.workspaceId, workspaceId), eq(onboardGoalsAmbition.isCurrent, true)))
    .limit(1);

  return {
    identity: identity ? { ...identity, values } : null,
    stage_scale: stageScale || null,
    founders,
    team_culture: teamCulture || null,
    market: market ? { ...market, competitors } : null,
    challenges: challenges || null,
    goals_ambition: goalsAmbition || null,
  };
}

export async function getCadenceStatusService(workspaceId: string): Promise<{
  cadences: Array<{
    dimension: string;
    cadence: string;
    intervalDays: number | null;
    lastReviewedAt: string | null;
    nextDueAt: string | null;
    daysSinceLastReview: number;
    urgency: "critical" | "recommended" | "optional" | "ok";
  }>;
}> {
  const wsId = BigInt(workspaceId);
  const rows = await db
    .select()
    .from(onboardReviewCadence)
    .where(eq(onboardReviewCadence.workspaceId, wsId));

  const now = new Date().getTime();

  const cadences = rows.map((r) => {
    const lastRev = r.lastReviewedAt ? new Date(r.lastReviewedAt).getTime() : 0;
    const nextDue = r.nextDueAt ? new Date(r.nextDueAt).getTime() : 0;
    const daysSince = lastRev > 0 ? Math.floor((now - lastRev) / 86400000) : 999;

    let urgency: "critical" | "recommended" | "optional" | "ok" = "ok";
    if (nextDue > 0) {
      const overdueDays = (now - nextDue) / 86400000;
      if (overdueDays > 14) {
        urgency = "critical";
      } else if (overdueDays >= 0) {
        urgency = "recommended";
      } else if (overdueDays >= -7) {
        urgency = "optional";
      }
    }

    return {
      dimension: r.dimension,
      cadence: r.cadence,
      intervalDays: r.intervalDays,
      lastReviewedAt: r.lastReviewedAt ? r.lastReviewedAt.toISOString() : null,
      nextDueAt: r.nextDueAt ? r.nextDueAt.toISOString() : null,
      daysSinceLastReview: daysSince,
      urgency,
    };
  });

  return { cadences };
}
