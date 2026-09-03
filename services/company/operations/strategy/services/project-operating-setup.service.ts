import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";
import { projectOperatingSetups } from "../../../shared/db/schema/strategy";
import { TenantContext } from "../../../shared/types/tenant_context";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { PROJECT_OPERATING_SETUP_ACTIVATED } from "../../../shared/events";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  transitionProjectStageInTransaction,
  ProjectLifecycleStage,
} from "./project-stage-lifecycle.service";
import { Project } from "../../services/project.service";
import { materializeFirstWeekPlan } from "./project-kickoff-materialize.service";

export type OperatingSetupStatus = "NOT_STARTED" | "IN_PROGRESS" | "ACTIVE";

export type EvidenceLevel =
  | "NONE"
  | "ONE_TO_FOUR_INTERVIEWS"
  | "FIVE_PLUS_INTERVIEWS"
  | "PROTOTYPE_OR_REVENUE";

export type BasicKickoffStage = "P0_DISCOVERY" | "P1_PROBLEM_VALIDATION";

export interface FirstWeekAction {
  id: string;
  title: string;
}

export interface ProjectOperatingSetupView {
  projectId: string;
  workspaceId: string;
  status: OperatingSetupStatus;
  targetCustomer: string | null;
  problemStatement: string | null;
  evidenceLevel: EvidenceLevel | null;
  recommendedStage: BasicKickoffStage | null;
  selectedStage: BasicKickoffStage | null;
  stageDurationWeeks: number | null;
  stageTargetDate: string | null;
  roundStartDate: string | null;
  weeklyReviewWeekday: number | null;
  weeklyReviewTime: string | null;
  firstWeekOutcome: string | null;
  firstWeekActions: FirstWeekAction[];
  updatedAt: string | null;
}

export interface SaveProjectOperatingSetupRequest {
  targetCustomer?: string | null;
  problemStatement?: string | null;
  evidenceLevel?: EvidenceLevel | null;
  selectedStage?: BasicKickoffStage | null;
  stageDurationWeeks?: number | null;
  roundStartDate?: string | null;
  weeklyReviewWeekday?: number | null;
  weeklyReviewTime?: string | null;
  firstWeekOutcome?: string | null;
  firstWeekActions?: Array<{ id?: string; title: string }>;
}

export interface ActivateProjectOperatingSetupRequest {
  targetCustomer: string;
  problemStatement: string;
  evidenceLevel: EvidenceLevel;
  selectedStage: BasicKickoffStage;
  stageDurationWeeks: number;
  roundStartDate?: string | null;
  weeklyReviewWeekday: number;
  weeklyReviewTime: string;
  firstWeekOutcome: string;
  firstWeekActions: Array<{ id?: string; title: string }>;
}

export const DURATION_LIMITS: Record<BasicKickoffStage, readonly [number, number]> = {
  P0_DISCOVERY: [1, 2],
  P1_PROBLEM_VALIDATION: [2, 4],
};

export function startOfUtcDay(d: Date): Date {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
}

// Mặc định vòng bắt đầu Thứ Hai (chuẩn ISO-8601: tuần làm việc bắt đầu T2)
// vào/đúng sau `from`. Nếu `from` đã là Thứ Hai thì bắt đầu luôn hôm đó.
export function nextMondayOnOrAfter(from: Date): Date {
  const base = startOfUtcDay(from);
  const iso = base.getUTCDay() === 0 ? 7 : base.getUTCDay(); // 1=Mon..7=Sun
  const add = iso === 1 ? 0 : 8 - iso;
  base.setUTCDate(base.getUTCDate() + add);
  return base;
}

// Chuẩn hoá mốc bắt đầu vòng: rỗng -> Thứ Hai kế tiếp; có giá trị -> ép về
// đầu ngày UTC và bắt buộc nằm trong cửa sổ [hôm nay-1d, hôm nay+60d].
function resolveRoundStart(raw: string | null | undefined, now: Date): Date {
  if (raw === undefined || raw === null || !raw.trim()) {
    return nextMondayOnOrAfter(now);
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    throw APIError.invalidArgument("roundStartDate không phải ISO date hợp lệ");
  }
  const day = startOfUtcDay(parsed);
  const lo = startOfUtcDay(new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000));
  const hi = startOfUtcDay(new Date(now.getTime() + 60 * 24 * 60 * 60 * 1000));
  if (day.getTime() < lo.getTime() || day.getTime() > hi.getTime()) {
    throw APIError.invalidArgument("roundStartDate phải nằm trong 60 ngày tới");
  }
  return day;
}

const VALID_EVIDENCE_LEVELS: readonly EvidenceLevel[] = [
  "NONE",
  "ONE_TO_FOUR_INTERVIEWS",
  "FIVE_PLUS_INTERVIEWS",
  "PROTOTYPE_OR_REVENUE",
];

const VALID_STAGES: readonly BasicKickoffStage[] = [
  "P0_DISCOVERY",
  "P1_PROBLEM_VALIDATION",
];

export function recommendKickoffStage(level: EvidenceLevel | null): BasicKickoffStage {
  return level === "FIVE_PLUS_INTERVIEWS" || level === "PROTOTYPE_OR_REVENUE"
    ? "P1_PROBLEM_VALIDATION"
    : "P0_DISCOVERY";
}

function normalizeFirstWeekActions(
  actions: Array<{ id?: string; title: string }> | undefined,
  knownIds: ReadonlySet<string>
): FirstWeekAction[] {
  if (!actions || !Array.isArray(actions)) return [];
  return actions
    .map((a) => {
      // Chỉ tin id do client gửi lên nếu nó khớp id server đã từng mint cho
      // chính project này (đã tồn tại trong firstWeekActions đã lưu trước đó).
      // Không tin mù id tuỳ ý từ client — tránh BigInt() ném lỗi trần trên chuỗi
      // sai định dạng và tránh phụ thuộc id client cho việc ghi task.
      const candidate = a.id && a.id.trim() ? a.id.trim() : null;
      const id = candidate && knownIds.has(candidate) ? candidate : generateSnowflake().toString();
      return { id, title: (a.title || "").trim() };
    })
    .filter((a) => a.title.length > 0)
    .slice(0, 3);
}

function toView(row: typeof projectOperatingSetups.$inferSelect): ProjectOperatingSetupView {
  return {
    projectId: row.projectId.toString(),
    workspaceId: row.workspaceId.toString(),
    status: row.status as OperatingSetupStatus,
    targetCustomer: row.targetCustomer,
    problemStatement: row.problemStatement,
    evidenceLevel: row.evidenceLevel as EvidenceLevel | null,
    recommendedStage: row.recommendedStage as BasicKickoffStage | null,
    selectedStage: row.selectedStage as BasicKickoffStage | null,
    stageDurationWeeks: row.stageDurationWeeks,
    stageTargetDate: row.stageTargetDate ? row.stageTargetDate.toISOString() : null,
    roundStartDate: row.roundStartDate ? row.roundStartDate.toISOString() : null,
    weeklyReviewWeekday: row.weeklyReviewWeekday,
    weeklyReviewTime: row.weeklyReviewTime,
    firstWeekOutcome: row.firstWeekOutcome,
    firstWeekActions: (row.firstWeekActions as FirstWeekAction[]) || [],
    updatedAt: row.updatedAt ? row.updatedAt.toISOString() : null,
  };
}

function toProject(row: typeof projects.$inferSelect): Project {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    description: row.description,
    lifecycleStage: row.lifecycleStage,
    stageEnteredAt: row.stageEnteredAt ? row.stageEnteredAt.toISOString() : null,
    status: row.status,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    projectType: row.projectType,
    strategicPriority: row.strategicPriority,
    portfolioId: row.portfolioId ? row.portfolioId.toString() : null,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    endDate: row.endDate ? row.endDate.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getProjectOperatingSetup(
  ctx: TenantContext,
  projectId: string
): Promise<ProjectOperatingSetupView> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  const [proj] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  const [setup] = await db
    .select()
    .from(projectOperatingSetups)
    .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)))
    .limit(1);

  if (!setup) {
    return {
      projectId,
      workspaceId: ctx.workspaceId,
      status: "NOT_STARTED",
      targetCustomer: null,
      problemStatement: null,
      evidenceLevel: null,
      recommendedStage: "P0_DISCOVERY",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      stageTargetDate: null,
      roundStartDate: null,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: null,
      firstWeekActions: [],
      updatedAt: null,
    };
  }

  return toView(setup);
}

export async function saveProjectOperatingSetup(
  ctx: TenantContext,
  projectId: string,
  req: SaveProjectOperatingSetupRequest
): Promise<ProjectOperatingSetupView> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  return db.transaction(async (tx) => {
    const [proj] = await tx
      .select({ id: projects.id })
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);

    if (!proj) {
      throw APIError.notFound("Project không tồn tại trong workspace này");
    }

    const [existing] = await tx
      .select()
      .from(projectOperatingSetups)
      .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)))
      .limit(1);

    if (existing && existing.status === "ACTIVE") {
      throw APIError.failedPrecondition("Operating setup đã được kích hoạt (ACTIVE), không thể lưu draft");
    }

    if (req.evidenceLevel && !VALID_EVIDENCE_LEVELS.includes(req.evidenceLevel)) {
      throw APIError.invalidArgument(`evidenceLevel không hợp lệ: ${req.evidenceLevel}`);
    }

    if (req.selectedStage && !VALID_STAGES.includes(req.selectedStage)) {
      throw APIError.invalidArgument(`selectedStage không hợp lệ: ${req.selectedStage}`);
    }

    if (req.firstWeekActions && req.firstWeekActions.length > 3) {
      throw APIError.invalidArgument("firstWeekActions cannot exceed 3 items");
    }

    const selectedStage = req.selectedStage ?? (existing?.selectedStage as BasicKickoffStage | null);
    const evidenceLevel = req.evidenceLevel ?? (existing?.evidenceLevel as EvidenceLevel | null);

    if (
      selectedStage === "P1_PROBLEM_VALIDATION" &&
      evidenceLevel &&
      !["FIVE_PLUS_INTERVIEWS", "PROTOTYPE_OR_REVENUE"].includes(evidenceLevel)
    ) {
      throw APIError.invalidArgument("P1 requires founder-confirmed qualifying evidence");
    }

    if (req.stageDurationWeeks !== undefined && req.stageDurationWeeks !== null) {
      const stageForDuration = selectedStage ?? "P0_DISCOVERY";
      const [min, max] = DURATION_LIMITS[stageForDuration] ?? [1, 2];
      if (req.stageDurationWeeks < min || req.stageDurationWeeks > max) {
        throw APIError.invalidArgument(
          `stageDurationWeeks must be between ${min} and ${max} for ${stageForDuration}`
        );
      }
    }

    if (req.weeklyReviewWeekday !== undefined && req.weeklyReviewWeekday !== null) {
      if (req.weeklyReviewWeekday < 1 || req.weeklyReviewWeekday > 7) {
        throw APIError.invalidArgument("weeklyReviewWeekday must be between 1 and 7");
      }
    }

    if (req.weeklyReviewTime !== undefined && req.weeklyReviewTime !== null) {
      if (!/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(req.weeklyReviewTime)) {
        throw APIError.invalidArgument("weeklyReviewTime must use HH:mm");
      }
    }

    const durationWeeks = req.stageDurationWeeks === undefined
      ? existing?.stageDurationWeeks ?? null
      : req.stageDurationWeeks;

    const now = new Date();
    // Mốc bắt đầu vòng: request gửi rõ -> resolve/validate; không gửi -> giữ mốc cũ.
    // Ngoại lệ: nếu giá trị gửi lên TRÙNG mốc đã lưu (cùng đầu ngày UTC) thì chấp
    // nhận nguyên trạng và bỏ qua kiểm tra cửa sổ 60 ngày — nếu không, Founder
    // resume một setup dở dang sau >60 ngày sẽ khiến mọi `saveCurrentStep()` /
    // "Quay lại" ném `invalidArgument`. `activate` vẫn giữ nguyên (strict).
    const resolvedRoundStart = ((): Date | null => {
      if (req.roundStartDate === undefined) {
        return existing?.roundStartDate ?? null;
      }
      if (req.roundStartDate !== null && req.roundStartDate.trim() && existing?.roundStartDate) {
        const parsed = new Date(req.roundStartDate);
        // NaN rơi xuống resolveRoundStart để ném lỗi invalid-date như cũ.
        if (
          !Number.isNaN(parsed.getTime()) &&
          startOfUtcDay(parsed).getTime() === startOfUtcDay(existing.roundStartDate).getTime()
        ) {
          return startOfUtcDay(existing.roundStartDate);
        }
      }
      return resolveRoundStart(req.roundStartDate, now);
    })();
    // stageTargetDate luôn neo vào mốc vòng (fallback `now` khi chưa có mốc).
    const anchorForTarget = resolvedRoundStart ?? now;
    const stageTargetDate =
      durationWeeks === null
        ? (req.stageDurationWeeks === undefined ? existing?.stageTargetDate ?? null : null)
        : new Date(anchorForTarget.getTime() + durationWeeks * 7 * 24 * 60 * 60 * 1000);

    const previousActions = (existing?.firstWeekActions as FirstWeekAction[]) || [];

    const knownActionIds = new Set(previousActions.map((a) => a.id));
    const actions = req.firstWeekActions !== undefined
      ? normalizeFirstWeekActions(req.firstWeekActions, knownActionIds)
      : previousActions;

    const resolvedOutcome = req.firstWeekOutcome !== undefined ? req.firstWeekOutcome : existing?.firstWeekOutcome ?? null;

    const recommendedStage = req.evidenceLevel !== undefined
      ? recommendKickoffStage(req.evidenceLevel)
      : existing?.recommendedStage ?? (evidenceLevel ? recommendKickoffStage(evidenceLevel) : null);

    const [saved] = await tx
      .insert(projectOperatingSetups)
      .values({
        projectId: pId,
        workspaceId: wsId,
        status: "IN_PROGRESS",
        targetCustomer: req.targetCustomer !== undefined ? req.targetCustomer : existing?.targetCustomer ?? null,
        problemStatement: req.problemStatement !== undefined ? req.problemStatement : existing?.problemStatement ?? null,
        evidenceLevel: req.evidenceLevel !== undefined ? req.evidenceLevel : existing?.evidenceLevel ?? null,
        recommendedStage: recommendedStage as string | null,
        selectedStage: req.selectedStage !== undefined ? req.selectedStage : existing?.selectedStage ?? null,
        stageDurationWeeks: durationWeeks,
        stageTargetDate,
        roundStartDate: resolvedRoundStart,
        weeklyReviewWeekday: req.weeklyReviewWeekday !== undefined ? req.weeklyReviewWeekday : existing?.weeklyReviewWeekday ?? null,
        weeklyReviewTime: req.weeklyReviewTime !== undefined ? req.weeklyReviewTime : existing?.weeklyReviewTime ?? null,
        firstWeekOutcome: resolvedOutcome,
        firstWeekActions: actions,
        createdAt: existing?.createdAt ?? now,
        updatedAt: now,
      })
      .onConflictDoUpdate({
        target: projectOperatingSetups.projectId,
        set: {
          status: "IN_PROGRESS",
          targetCustomer: req.targetCustomer !== undefined ? req.targetCustomer : existing?.targetCustomer ?? null,
          problemStatement: req.problemStatement !== undefined ? req.problemStatement : existing?.problemStatement ?? null,
          evidenceLevel: req.evidenceLevel !== undefined ? req.evidenceLevel : existing?.evidenceLevel ?? null,
          recommendedStage: recommendedStage as string | null,
          selectedStage: req.selectedStage !== undefined ? req.selectedStage : existing?.selectedStage ?? null,
          stageDurationWeeks: durationWeeks,
          stageTargetDate,
          roundStartDate: resolvedRoundStart,
          weeklyReviewWeekday: req.weeklyReviewWeekday !== undefined ? req.weeklyReviewWeekday : existing?.weeklyReviewWeekday ?? null,
          weeklyReviewTime: req.weeklyReviewTime !== undefined ? req.weeklyReviewTime : existing?.weeklyReviewTime ?? null,
          firstWeekOutcome: resolvedOutcome,
          firstWeekActions: actions,
          updatedAt: now,
        },
      })
      .returning();

    await materializeFirstWeekPlan(tx, ctx, {
      projectId,
      previousActions,
      actions,
      firstWeekOutcome: resolvedOutcome,
      selectedStage: (saved.selectedStage as BasicKickoffStage | null),
      stageDurationWeeks: saved.stageDurationWeeks,
    });

    return toView(saved);
  });
}

export async function activateProjectOperatingSetup(
  ctx: TenantContext,
  projectId: string,
  req: ActivateProjectOperatingSetupRequest
): Promise<{ setup: ProjectOperatingSetupView; project: Project }> {
  // Pre-transaction validations
  if (!req.targetCustomer || !req.targetCustomer.trim()) {
    throw APIError.invalidArgument("targetCustomer is required");
  }
  if (!req.problemStatement || !req.problemStatement.trim()) {
    throw APIError.invalidArgument("problemStatement is required");
  }
  if (!req.evidenceLevel || !VALID_EVIDENCE_LEVELS.includes(req.evidenceLevel)) {
    throw APIError.invalidArgument("Valid evidenceLevel is required");
  }
  if (!req.selectedStage || !VALID_STAGES.includes(req.selectedStage)) {
    throw APIError.invalidArgument("Valid selectedStage is required");
  }
  if (
    req.selectedStage === "P1_PROBLEM_VALIDATION" &&
    !["FIVE_PLUS_INTERVIEWS", "PROTOTYPE_OR_REVENUE"].includes(req.evidenceLevel)
  ) {
    throw APIError.invalidArgument("P1 requires founder-confirmed qualifying evidence");
  }

  const [minWeeks, maxWeeks] = DURATION_LIMITS[req.selectedStage];
  if (
    typeof req.stageDurationWeeks !== "number" ||
    req.stageDurationWeeks < minWeeks ||
    req.stageDurationWeeks > maxWeeks
  ) {
    throw APIError.invalidArgument(
      `stageDurationWeeks must be between ${minWeeks} and ${maxWeeks} for ${req.selectedStage}`
    );
  }

  if (
    typeof req.weeklyReviewWeekday !== "number" ||
    req.weeklyReviewWeekday < 1 ||
    req.weeklyReviewWeekday > 7
  ) {
    throw APIError.invalidArgument("weeklyReviewWeekday must be between 1 and 7");
  }

  if (!req.weeklyReviewTime || !/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(req.weeklyReviewTime)) {
    throw APIError.invalidArgument("weeklyReviewTime must use HH:mm");
  }

  if (!req.firstWeekOutcome || !req.firstWeekOutcome.trim()) {
    throw APIError.invalidArgument("firstWeekOutcome is required");
  }

  if (!req.firstWeekActions || !Array.isArray(req.firstWeekActions)) {
    throw APIError.invalidArgument("firstWeekActions must be an array");
  }

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);
  const now = new Date();
  // stageTargetDate neo vào mốc bắt đầu vòng (mặc định Thứ Hai kế tiếp).
  const roundStartDate = resolveRoundStart(req.roundStartDate, now);
  const stageTargetDate = new Date(
    roundStartDate.getTime() + req.stageDurationWeeks * 7 * 24 * 60 * 60 * 1000
  );
  const recommendedStage = recommendKickoffStage(req.evidenceLevel);

  return db.transaction(async (tx) => {
    const [proj] = await tx
      .select()
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);

    if (!proj) {
      throw APIError.notFound("Project không tồn tại trong workspace này");
    }

    // Mốc "đã triển khai bao lâu" cho Founder — chỉ set lần đầu, không ghi đè.
    if (!proj.startDate) {
      await tx
        .update(projects)
        .set({ startDate: roundStartDate })
        .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)));
    }

    const [existing] = await tx
      .select({ firstWeekActions: projectOperatingSetups.firstWeekActions })
      .from(projectOperatingSetups)
      .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)))
      .limit(1);
    const previousActions = (existing?.firstWeekActions as FirstWeekAction[]) || [];

    const knownActionIds = new Set(previousActions.map((a) => a.id));
    const normalizedActions = normalizeFirstWeekActions(req.firstWeekActions, knownActionIds);
    if (normalizedActions.length < 1 || normalizedActions.length > 3 || req.firstWeekActions.length > 3 || req.firstWeekActions.length < 1) {
      throw APIError.invalidArgument("firstWeekActions must contain 1 to 3 non-empty items");
    }

    if (req.selectedStage === "P1_PROBLEM_VALIDATION" && proj.lifecycleStage === "P0_DISCOVERY") {
      await transitionProjectStageInTransaction(tx, {
        workspaceId: wsId,
        projectId: pId,
        toStage: "P1_PROBLEM_VALIDATION",
        reason: "Founder operating setup activated with qualifying evidence",
        actorMemberId: ctx.userId ? BigInt(ctx.userId) : undefined,
        actorRole: ctx.membershipRole,
        source: "manual",
      });
    }

    const [savedSetup] = await tx
      .insert(projectOperatingSetups)
      .values({
        projectId: pId,
        workspaceId: wsId,
        status: "ACTIVE",
        targetCustomer: req.targetCustomer.trim(),
        problemStatement: req.problemStatement.trim(),
        evidenceLevel: req.evidenceLevel,
        recommendedStage,
        selectedStage: req.selectedStage,
        stageDurationWeeks: req.stageDurationWeeks,
        stageTargetDate,
        roundStartDate,
        weeklyReviewWeekday: req.weeklyReviewWeekday,
        weeklyReviewTime: req.weeklyReviewTime,
        firstWeekOutcome: req.firstWeekOutcome.trim(),
        firstWeekActions: normalizedActions,
        createdAt: now,
        updatedAt: now,
      })
      .onConflictDoUpdate({
        target: projectOperatingSetups.projectId,
        set: {
          status: "ACTIVE",
          targetCustomer: req.targetCustomer.trim(),
          problemStatement: req.problemStatement.trim(),
          evidenceLevel: req.evidenceLevel,
          recommendedStage,
          selectedStage: req.selectedStage,
          stageDurationWeeks: req.stageDurationWeeks,
          stageTargetDate,
          roundStartDate,
          weeklyReviewWeekday: req.weeklyReviewWeekday,
          weeklyReviewTime: req.weeklyReviewTime,
          firstWeekOutcome: req.firstWeekOutcome.trim(),
          firstWeekActions: normalizedActions,
          updatedAt: now,
        },
      })
      .returning();

    const event = makeBusinessEvent({
      eventType: PROJECT_OPERATING_SETUP_ACTIVATED,
      workspaceId: ctx.workspaceId,
      aggregateType: "project",
      aggregateId: projectId,
      correlationId: randomUUID(),
      actor: {
        kind: ctx.userId ? "user" : "system",
        id: ctx.userId ?? "strategy.operating_setup",
      },
      classification: "internal",
      payload: {
        projectId,
        workspaceId: ctx.workspaceId,
        selectedStage: req.selectedStage,
        stageDurationWeeks: req.stageDurationWeeks,
        actionCount: normalizedActions.length,
        weeklyReviewWeekday: req.weeklyReviewWeekday,
        activatedAt: now.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    await materializeFirstWeekPlan(tx, ctx, {
      projectId,
      previousActions,
      actions: normalizedActions,
      firstWeekOutcome: req.firstWeekOutcome.trim(),
      selectedStage: req.selectedStage,
      stageDurationWeeks: req.stageDurationWeeks,
    });

    const [refreshedProject] = await tx
      .select()
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);

    return {
      setup: toView(savedSetup),
      project: toProject(refreshedProject ?? proj),
    };
  });
}
