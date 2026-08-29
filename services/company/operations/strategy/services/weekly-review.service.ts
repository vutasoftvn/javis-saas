import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { WEEKLY_REVIEW_COMPLETED } from "../../../shared/events";
import { randomUUID } from "node:crypto";

const { weeklyReviews } = schema;

export interface WeeklyReviewView {
  id: string;
  workspaceId: string;
  weekStartDate: string;
  summary: string;
  stageAssessment: string | null;
  cashSummary: string | null;
  obligationsSummary: string | null;
  actionProposals: any[];
  status: "DRAFT" | "COMPLETED";
  createdAt: string;
  updatedAt: string;
}

export async function createWeeklyReviewService(p: {
  workspaceId: bigint;
  weekStartDate: string;
  summary: string;
  stageAssessment?: string;
  cashSummary?: string;
  obligationsSummary?: string;
  actionProposals?: any[];
}): Promise<WeeklyReviewView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(weeklyReviews)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      weekStartDate: p.weekStartDate as any,
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
    actionProposals: (created.actionProposals || []) as any[],
    status: created.status as any,
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
    actionProposals: (r.actionProposals || []) as any[],
    status: r.status as any,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

export async function completeWeeklyReviewService(p: {
  reviewId: bigint;
  completedBy: bigint;
}): Promise<WeeklyReviewView> {
  return await db.transaction(async (tx) => {
    const [review] = await tx
      .select()
      .from(weeklyReviews)
      .where(eq(weeklyReviews.id, p.reviewId));

    if (!review) {
      throw APIError.notFound(`Weekly review '${p.reviewId}' not found`);
    }

    const now = new Date();
    const [updated] = await tx
      .update(weeklyReviews)
      .set({
        status: "COMPLETED",
        updatedAt: now,
      })
      .where(eq(weeklyReviews.id, p.reviewId))
      .returning();

    const event = makeBusinessEvent({
      eventType: WEEKLY_REVIEW_COMPLETED,
      workspaceId: String(updated.workspaceId),
      aggregateType: "weekly_review",
      aggregateId: String(updated.id),
      correlationId: randomUUID(),
      actor: {
        kind: "user",
        id: String(p.completedBy),
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
      actionProposals: (updated.actionProposals || []) as any[],
      status: "COMPLETED",
      createdAt: updated.createdAt.toISOString(),
      updatedAt: updated.updatedAt.toISOString(),
    };
  });
}
