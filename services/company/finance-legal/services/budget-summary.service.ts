import { APIError } from "encore.dev/api";
import { and, eq, gte, lte, inArray, isNull, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireFounderCommand } from "../../shared/auth/workspace-access";

import { projects } from "../../shared/db/schema/operations";

const { projectBudgetEnvelopes, paymentRequests, paymentAllocations } = schema;

export async function assertProjectInWorkspace(
  workspaceId: string | number,
  projectId: string | number
): Promise<void> {
  const [row] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(
      and(
        eq(projects.id, BigInt(projectId)),
        eq(projects.workspaceId, BigInt(workspaceId)),
        isNull(projects.deletedAt)
      )
    )
    .limit(1);
  if (!row) throw APIError.notFound("Project không tồn tại trong workspace này");
}

export type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

export type BudgetCoverage = "NO_ENVELOPE" | "COMPLETE";

export interface BudgetPosition {
  envelopeId: string | null;
  limitMinor: bigint;
  actualPaidMinor: bigint;
  committedUnpaidMinor: bigint;
  forecastUnapprovedMinor: bigint;
  coverage: BudgetCoverage;
}

export interface BudgetPositionParams {
  workspaceId: string;
  projectId: string;
  currency: string;
  asOf: Date;
}

const OPEN_SETTLEMENT_STATES = ["UNPAID", "REPORTED", "PARTIAL", "EXCEPTION"];

/**
 * Tính vị trí ngân sách hiện tại của một project — dùng chung cho
 * getBudgetSummary (đọc, lockEnvelope=false) và
 * approvePaymentRequestService (enforcement, lockEnvelope=true, gọi trong
 * cùng transaction với việc duyệt chi để khóa envelope, chống 2 request
 * đồng thời cùng đọc "còn dư" rồi cùng được duyệt).
 */
export async function computeProjectBudgetPosition(
  tx: Tx,
  params: BudgetPositionParams,
  lockEnvelope: boolean
): Promise<BudgetPosition> {
  const wsId = BigInt(params.workspaceId);
  const projectId = BigInt(params.projectId);
  const asOfDate = params.asOf.toISOString().split("T")[0];

  const envelopeQuery = tx
    .select()
    .from(projectBudgetEnvelopes)
    .where(
      and(
        eq(projectBudgetEnvelopes.workspaceId, wsId),
        eq(projectBudgetEnvelopes.projectId, projectId),
        eq(projectBudgetEnvelopes.currency, params.currency),
        lte(projectBudgetEnvelopes.periodStart, asOfDate),
        gte(projectBudgetEnvelopes.periodEnd, asOfDate),
        isNull(projectBudgetEnvelopes.deletedAt)
      )
    );

  const envelopeRows = lockEnvelope ? await envelopeQuery.for("update") : await envelopeQuery;
  // Không có unique constraint chống chồng kỳ (out of scope, xem spec) —
  // nếu có nhiều hơn 1 dòng phủ asOf, lấy dòng tạo gần nhất.
  const envelope = envelopeRows.length
    ? envelopeRows.reduce((latest, row) => (row.createdAt > latest.createdAt ? row : latest))
    : undefined;

  if (!envelope) {
    return {
      envelopeId: null,
      limitMinor: 0n,
      actualPaidMinor: 0n,
      committedUnpaidMinor: 0n,
      forecastUnapprovedMinor: 0n,
      coverage: "NO_ENVELOPE",
    };
  }

  const requests = await tx
    .select()
    .from(paymentRequests)
    .where(
      and(
        eq(paymentRequests.workspaceId, wsId),
        eq(paymentRequests.projectId, projectId),
        eq(paymentRequests.currency, params.currency),
        isNull(paymentRequests.deletedAt)
      )
    );

  const requestIds = requests.map((r) => r.id);
  const allocations = requestIds.length
    ? await tx
        .select()
        .from(paymentAllocations)
        .where(and(inArray(paymentAllocations.requestId, requestIds), eq(paymentAllocations.status, "ACTIVE")))
    : [];

  const allocatedByRequest = new Map<string, bigint>();
  for (const a of allocations) {
    const key = String(a.requestId);
    allocatedByRequest.set(key, (allocatedByRequest.get(key) ?? 0n) + BigInt(a.amountMinor));
  }

  let actualPaidMinor = 0n;
  let committedUnpaidMinor = 0n;
  let forecastUnapprovedMinor = 0n;

  for (const r of requests) {
    const allocated = allocatedByRequest.get(String(r.id)) ?? 0n;
    actualPaidMinor += allocated;

    if (r.approvalState === "APPROVED" && OPEN_SETTLEMENT_STATES.includes(r.settlementState)) {
      const outstanding = BigInt(r.amountMinor) - allocated;
      if (outstanding > 0n) committedUnpaidMinor += outstanding;
    } else if (r.approvalState === "DRAFT" || r.approvalState === "SUBMITTED") {
      forecastUnapprovedMinor += BigInt(r.amountMinor);
    }
  }

  return {
    envelopeId: String(envelope.id),
    limitMinor: BigInt(envelope.limitMinor),
    actualPaidMinor,
    committedUnpaidMinor,
    forecastUnapprovedMinor,
    coverage: "COMPLETE",
  };
}

export interface BudgetSummaryView {
  currency: string;
  // null (KHÔNG phải "0") khi coverage === "NO_ENVELOPE" — không dựng số 0 giả
  // như thể là dữ liệu thật.
  limitMinor: string | null;
  actualPaidMinor: string | null;
  committedUnpaidMinor: string | null;
  forecastUnapprovedMinor: string | null;
  remainingAfterCommitmentsMinor: string | null;
  coverage: BudgetCoverage;
  asOf: string;
}

export async function getBudgetSummary(
  ctx: TenantContext,
  projectId: string,
  currency: string = "VND"
): Promise<BudgetSummaryView> {
  await assertProjectInWorkspace(ctx.workspaceId, projectId);
  const asOf = new Date();
  const position = await db.transaction((tx) =>
    computeProjectBudgetPosition(
      tx,
      { workspaceId: ctx.workspaceId, projectId, currency, asOf },
      false
    )
  );

  if (position.coverage === "NO_ENVELOPE") {
    return {
      currency,
      limitMinor: null,
      actualPaidMinor: null,
      committedUnpaidMinor: null,
      forecastUnapprovedMinor: null,
      remainingAfterCommitmentsMinor: null,
      coverage: "NO_ENVELOPE",
      asOf: asOf.toISOString(),
    };
  }

  const remaining = position.limitMinor - position.actualPaidMinor - position.committedUnpaidMinor;

  return {
    currency,
    limitMinor: String(position.limitMinor),
    actualPaidMinor: String(position.actualPaidMinor),
    committedUnpaidMinor: String(position.committedUnpaidMinor),
    forecastUnapprovedMinor: String(position.forecastUnapprovedMinor),
    remainingAfterCommitmentsMinor: String(remaining),
    coverage: position.coverage,
    asOf: asOf.toISOString(),
  };
}

export interface CreateBudgetEnvelopeInput {
  projectId: string;
  legalEntityId: string;
  currency?: string;
  periodStart: string;
  periodEnd: string;
  limitMinor: string;
}

export interface BudgetEnvelopeView {
  id: string;
  projectId: string;
  legalEntityId: string;
  currency: string;
  periodStart: string;
  periodEnd: string;
  limitMinor: string;
  version: number;
}

export async function createBudgetEnvelopeService(
  ctx: TenantContext,
  input: CreateBudgetEnvelopeInput
): Promise<BudgetEnvelopeView> {
  requireFounderCommand(ctx, "finance.budget.envelope.set");

  const amount = BigInt(input.limitMinor);
  if (amount <= 0n) {
    throw APIError.invalidArgument("limitMinor must be positive");
  }

  const [row] = await db
    .insert(projectBudgetEnvelopes)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      projectId: BigInt(input.projectId),
      legalEntityId: BigInt(input.legalEntityId),
      currency: input.currency ?? "VND",
      periodStart: input.periodStart,
      periodEnd: input.periodEnd,
      limitMinor: input.limitMinor,
      ownerMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId),
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create budget envelope");

  return {
    id: String(row.id),
    projectId: String(row.projectId),
    legalEntityId: String(row.legalEntityId),
    currency: row.currency,
    periodStart: String(row.periodStart),
    periodEnd: String(row.periodEnd),
    limitMinor: row.limitMinor,
    version: row.version,
  };
}
