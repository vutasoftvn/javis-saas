import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { WEEKLY_REVIEW_COMPLETED } from "../../../shared/events";
import { randomUUID } from "node:crypto";
import { JsonValue, toJsonArray } from "./strategy-json";

const { weeklyReviews } = schema;

export type WeeklyReviewStatus = "DRAFT" | "COMPLETED";

export interface WeeklyReviewView {
  id: string;
  workspaceId: string;
  weekStartDate: string;
  summary: string;
  stageAssessment: string | null;
  cashSummary: string | null;
  obligationsSummary: string | null;
  actionProposals: JsonValue[];
  status: WeeklyReviewStatus;
  createdAt: string;
  updatedAt: string;
}

export interface CreateWeeklyReviewServiceInput {
  workspaceId: bigint;
  weekStartDate: string;
  summary: string;
  stageAssessment?: string;
  cashSummary?: string;
  obligationsSummary?: string;
  actionProposals?: JsonValue[];
}

export async function createWeeklyReviewService(p: CreateWeeklyReviewServiceInput): Promise<WeeklyReviewView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(weeklyReviews)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      weekStartDate: p.weekStartDate,
      summary: p.summary,
      stageAssessment: p.stageAssessment ?? null,
      cashSummary: p.cashSummary ?? null,
      obligationsSummary: p.obligationsSummary ?? null,
      actionProposals: p.actionProposals ?? [],
      status: "DRAFT",
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    weekStartDate: typeof created.weekStartDate === "string" ? created.weekStartDate : new Date(created.weekStartDate).toISOString().split("T")[0],
    summary: created.summary,
    stageAssessment: created.stageAssessment,
    cashSummary: created.cashSummary,
    obligationsSummary: created.obligationsSummary,
    actionProposals: toJsonArray(created.actionProposals),
    status: created.status as WeeklyReviewStatus,
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}

export async function listWeeklyReviewsService(
  workspaceId: bigint
): Promise<WeeklyReviewView[]> {
  const rows = await db
    .select()
    .from(weeklyReviews)
    .where(eq(weeklyReviews.workspaceId, workspaceId))
    .orderBy(desc(weeklyReviews.weekStartDate));

  return rows.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    weekStartDate: typeof r.weekStartDate === "string" ? r.weekStartDate : new Date(r.weekStartDate).toISOString().split("T")[0],
    summary: r.summary,
    stageAssessment: r.stageAssessment,
    cashSummary: r.cashSummary,
    obligationsSummary: r.obligationsSummary,
    actionProposals: toJsonArray(r.actionProposals),
    status: r.status as WeeklyReviewStatus,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

import type { TenantContext } from "../../../shared/types/tenant_context";

export interface CompleteWeeklyReviewInput {
  reviewId: bigint;
  completedBy: bigint;
  ctx?: TenantContext;
}

export async function completeWeeklyReviewService(p: CompleteWeeklyReviewInput): Promise<WeeklyReviewView> {
  return await db.transaction(async (tx) => {
    const whereConditions = [eq(weeklyReviews.id, p.reviewId)];
    if (p.ctx) {
      whereConditions.push(eq(weeklyReviews.workspaceId, BigInt(p.ctx.workspaceId)));
    }

    const [review] = await tx
      .select()
      .from(weeklyReviews)
      .where(and(...whereConditions));

    if (!review) {
      throw APIError.notFound(`Weekly review '${p.reviewId}' not found`);
    }

    // Idempotent: return existing COMPLETED state without emitting another outbox event
    if (review.status === "COMPLETED") {
      return {
        id: String(review.id),
        workspaceId: String(review.workspaceId),
        weekStartDate: typeof review.weekStartDate === "string" ? review.weekStartDate : new Date(review.weekStartDate).toISOString().split("T")[0],
        summary: review.summary,
        stageAssessment: review.stageAssessment,
        cashSummary: review.cashSummary,
        obligationsSummary: review.obligationsSummary,
        actionProposals: toJsonArray(review.actionProposals),
        status: "COMPLETED",
        createdAt: review.createdAt.toISOString(),
        updatedAt: review.updatedAt.toISOString(),
      };
    }

    if (review.status !== "DRAFT") {
      throw APIError.failedPrecondition(`Weekly review must be in DRAFT status to complete (current: ${review.status})`);
    }

    const now = new Date();
    const updateConditions = [
      eq(weeklyReviews.id, p.reviewId),
      eq(weeklyReviews.status, "DRAFT"),
    ];
    if (p.ctx) {
      updateConditions.push(eq(weeklyReviews.workspaceId, BigInt(p.ctx.workspaceId)));
    }

    const [updated] = await tx
      .update(weeklyReviews)
      .set({
        status: "COMPLETED",
        updatedAt: now,
      })
      .where(and(...updateConditions))
      .returning();

    if (!updated) {
      const [recheck] = await tx
        .select()
        .from(weeklyReviews)
        .where(eq(weeklyReviews.id, p.reviewId));
      if (recheck && recheck.status === "COMPLETED") {
        return {
          id: String(recheck.id),
          workspaceId: String(recheck.workspaceId),
          weekStartDate: typeof recheck.weekStartDate === "string" ? recheck.weekStartDate : new Date(recheck.weekStartDate).toISOString().split("T")[0],
          summary: recheck.summary,
          stageAssessment: recheck.stageAssessment,
          cashSummary: recheck.cashSummary,
          obligationsSummary: recheck.obligationsSummary,
          actionProposals: toJsonArray(recheck.actionProposals),
          status: "COMPLETED",
          createdAt: recheck.createdAt.toISOString(),
          updatedAt: recheck.updatedAt.toISOString(),
        };
      }
      throw APIError.failedPrecondition(`Weekly review could not be transitioned to COMPLETED`);
    }

    const actorId = p.ctx?.userId ? String(p.ctx.userId) : String(p.completedBy);
    const correlationId = p.ctx?.correlationId || randomUUID();

    const event = makeBusinessEvent({
      eventType: WEEKLY_REVIEW_COMPLETED,
      workspaceId: String(updated.workspaceId),
      aggregateType: "weekly_review",
      aggregateId: String(updated.id),
      correlationId,
      actor: {
        kind: "user",
        id: actorId,
      },
      classification: "internal",
      payload: {
        workspaceId: String(updated.workspaceId),
        reviewId: String(updated.id),
        weekStartDate: String(updated.weekStartDate),
        completedAt: now.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      weekStartDate: typeof updated.weekStartDate === "string" ? updated.weekStartDate : new Date(updated.weekStartDate).toISOString().split("T")[0],
      summary: updated.summary,
      stageAssessment: updated.stageAssessment,
      cashSummary: updated.cashSummary,
      obligationsSummary: updated.obligationsSummary,
      actionProposals: toJsonArray(updated.actionProposals),
      status: "COMPLETED",
      createdAt: updated.createdAt.toISOString(),
      updatedAt: updated.updatedAt.toISOString(),
    };
  });
}
