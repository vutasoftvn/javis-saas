import { APIError } from "encore.dev/api";
import { eq, and, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { OnboardDimension, validateOnboardDimensionData } from "./onboard-dimension-fields";

export type { OnboardDimension } from "./onboard-dimension-fields";

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

// Seed chỉ tạo lịch rà soát — CHƯA có dữ liệu chiều nào được ghi nhận, nên
// lastReviewedAt/nextDueAt để null (trước đây gán `now` khiến mọi chiều báo "tươi"
// dù Founder chưa trả lời gì).
export async function seedReviewCadenceService(workspaceId: bigint): Promise<void> {
  for (const config of DEFAULT_CADENCES) {
    await db
      .insert(onboardReviewCadence)
      .values({
        id: generateSnowflake(),
        workspaceId,
        dimension: config.dimension,
        cadence: config.cadence,
        intervalDays: config.intervalDays,
        lastReviewedAt: null,
        nextDueAt: null,
      })
      .onConflictDoNothing();
  }
}

function defaultCadenceFor(dimension: OnboardDimension): CadenceSeedConfig {
  const config = DEFAULT_CADENCES.find((c) => c.dimension === dimension);
  if (!config) {
    throw APIError.internal(`missing default cadence for onboard dimension '${dimension}'`);
  }
  return config;
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

// Session onboarding do caller gửi lên phải thuộc workspace đã được guard ở
// handler — không thì ghi được dimension/turn vào session của workspace khác.
async function assertOnboardSessionInWorkspace(wsId: bigint, sessionId: bigint): Promise<void> {
  const [row] = await db
    .select({ id: onboardSessions.id })
    .from(onboardSessions)
    .where(and(eq(onboardSessions.id, sessionId), eq(onboardSessions.workspaceId, wsId)))
    .limit(1);
  if (!row) {
    throw APIError.notFound("Không tìm thấy phiên onboarding trong workspace này.");
  }
}

export async function recordConversationTurnService(params: {
  workspaceId: string;
  sessionId: string;
  turnNumber: number;
  role: "user" | "assistant" | "system";
  content: string;
  dimension?: string;
}): Promise<{ turnId: string }> {
  const sId = BigInt(params.sessionId);
  await assertOnboardSessionInWorkspace(BigInt(params.workspaceId), sId);
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
  dimension: string;
  data: any;
}): Promise<{ success: boolean; dimension: string; recordId: string }> {
  // Kiểm payload trước mọi side effect: field lạ/sai kiểu bị từ chối thay vì ghi null.
  const { dimension } = validateOnboardDimensionData(params.dimension, params.data);
  const wsId = BigInt(params.workspaceId);
  const sId = BigInt(params.sessionId);
  await assertOnboardSessionInWorkspace(wsId, sId);
  const recordId = generateSnowflake();
  const now = new Date();

  // 1. Cập nhật bản ghi chiều (Append-only với is_current = true)
  switch (dimension) {
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
        eq(onboardReviewCadence.dimension, dimension)
      )
    )
    .limit(1);

  const defaults = defaultCadenceFor(dimension);
  const intervalDays = cadenceRows[0]?.intervalDays ?? defaults.intervalDays;
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
      dimension,
      cadence: defaults.cadence,
      intervalDays,
      lastReviewedAt: now,
      nextDueAt: nextDue,
    });
  }

  return { success: true, dimension, recordId: recordId.toString() };
}

export async function createSnapshotService(params: {
  workspaceId: string;
  sessionId: string;
  changeReason?: string;
  changedDimensions?: string[];
}): Promise<{ snapshotId: string; capturedAt: string }> {
  const wsId = BigInt(params.workspaceId);
  const sId = BigInt(params.sessionId);
  await assertOnboardSessionInWorkspace(wsId, sId);
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

  return toJsonSafe({
    identity: identity ? { ...identity, values } : null,
    stage_scale: stageScale || null,
    founders,
    team_culture: teamCulture || null,
    market: market ? { ...market, competitors } : null,
    challenges: challenges || null,
    goals_ambition: goalsAmbition || null,
  });
}

type JsonSafe = string | number | boolean | null | JsonSafe[] | { [key: string]: JsonSafe };

// Row Drizzle chứa id bigint và Date: JSON.stringify ném "Do not know how to serialize
// a BigInt" — làm hỏng cả response context/current lẫn cột jsonb full_context của
// snapshot. Chuẩn hoá: bigint → chuỗi (id Snowflake vượt Number.MAX_SAFE_INTEGER),
// Date → ISO string.
export function toJsonSafe(value: unknown): { [key: string]: JsonSafe } {
  const converted = convertJsonSafe(value);
  if (converted === null || typeof converted !== "object" || Array.isArray(converted)) {
    throw APIError.internal("company context must be an object");
  }
  return converted;
}

function convertJsonSafe(value: unknown): JsonSafe {
  if (value === null || value === undefined) return null;
  if (typeof value === "bigint") return value.toString();
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return value;
  if (Array.isArray(value)) return value.map(convertJsonSafe);
  if (typeof value === "object") {
    const out: { [key: string]: JsonSafe } = {};
    for (const [key, v] of Object.entries(value)) {
      out[key] = convertJsonSafe(v);
    }
    return out;
  }
  return null;
}

export type CadenceUrgency = "critical" | "recommended" | "optional" | "ok";

export interface DimensionCadenceStatus {
  dimension: OnboardDimension;
  cadence: string;
  intervalDays: number;
  lastReviewedAt: string | null;
  nextDueAt: string | null;
  // null khi chiều chưa từng được ghi nhận — không dùng số giả (trước đây 999).
  daysSinceLastReview: number | null;
  neverReviewed: boolean;
  urgency: CadenceUrgency;
}

/**
 * Trạng thái độ tươi của đủ 7 chiều (theo DEFAULT_CADENCES), kể cả khi workspace
 * chưa seed cadence. Chiều chưa từng ghi nhận là `critical` — không coi là "ok".
 */
export async function getCadenceStatusService(
  workspaceId: string,
  nowMs: number = Date.now()
): Promise<{ cadences: DimensionCadenceStatus[] }> {
  const wsId = BigInt(workspaceId);
  const rows = await db
    .select()
    .from(onboardReviewCadence)
    .where(eq(onboardReviewCadence.workspaceId, wsId));
  const rowByDimension = new Map(rows.map((r) => [r.dimension, r]));

  const cadences = DEFAULT_CADENCES.map((config): DimensionCadenceStatus => {
    const r = rowByDimension.get(config.dimension);
    const intervalDays = r?.intervalDays ?? config.intervalDays;
    const lastReviewedAt = r?.lastReviewedAt ?? null;
    const nextDueAt = r?.nextDueAt ?? null;

    if (!lastReviewedAt) {
      return {
        dimension: config.dimension,
        cadence: r?.cadence ?? config.cadence,
        intervalDays,
        lastReviewedAt: null,
        nextDueAt: nextDueAt ? nextDueAt.toISOString() : null,
        daysSinceLastReview: null,
        neverReviewed: true,
        urgency: "critical",
      };
    }

    const daysSince = Math.floor((nowMs - lastReviewedAt.getTime()) / 86400000);
    const dueMs = nextDueAt ? nextDueAt.getTime() : lastReviewedAt.getTime() + intervalDays * 86400000;
    const overdueDays = (nowMs - dueMs) / 86400000;
    let urgency: CadenceUrgency = "ok";
    if (overdueDays > 14) {
      urgency = "critical";
    } else if (overdueDays >= 0) {
      urgency = "recommended";
    } else if (overdueDays >= -7) {
      urgency = "optional";
    }

    return {
      dimension: config.dimension,
      cadence: r?.cadence ?? config.cadence,
      intervalDays,
      lastReviewedAt: lastReviewedAt.toISOString(),
      nextDueAt: new Date(dueMs).toISOString(),
      daysSinceLastReview: daysSince,
      neverReviewed: false,
      urgency,
    };
  });

  return { cadences };
}
