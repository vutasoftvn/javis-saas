import { APIError } from "encore.dev/api";
import { and, desc, eq, isNull } from "drizzle-orm";
import { db } from "../models/db";
import { keyResults, krObservations } from "../../shared/db/schema/operations";
import { TenantContext } from "../../shared/types/tenant_context";
import { computeLinearProgress } from "./execution-outcome.service";

export interface RecordKrObservationInput {
  krId: string;
  value: number | string;
  measurementAt?: string | Date;
  windowStart?: string | Date | null;
  windowEnd?: string | Date | null;
  evidenceRefs?: string[];
  sourceRef?: string | null;
  metricContractVersion?: number | null;
  idempotencyKey?: string | null;
}

export interface KrObservationView {
  id: string;
  workspaceId: string;
  krId: string;
  valueDecimal: string;
  measurementAt: string;
  windowStart: string | null;
  windowEnd: string | null;
  evidenceRefs: unknown[];
  sourceRef: string | null;
  recordedBy: string | null;
  metricContractVersion: number | null;
  idempotencyKey: string | null;
  createdAt: string;
  projectedProgress: number | null;
}

/**
 * Records an append-only observation for a Key Result.
 * Enforces workspace isolation, idempotency, and preserves projection consistency
 * (late-arriving observations do not roll back the current projection).
 */
export async function recordKrObservation(
  ctx: TenantContext,
  input: RecordKrObservationInput
): Promise<KrObservationView> {
  const wsId = BigInt(ctx.workspaceId);
  const krIdBig = BigInt(input.krId);

  const numVal = typeof input.value === "string" ? parseFloat(input.value) : input.value;
  if (!Number.isFinite(numVal)) {
    throw APIError.invalidArgument(`Invalid numeric observation value: ${input.value}`);
  }

  const measurementAt = input.measurementAt
    ? (input.measurementAt instanceof Date ? input.measurementAt : new Date(input.measurementAt))
    : new Date();

  if (Number.isNaN(measurementAt.getTime())) {
    throw APIError.invalidArgument("Invalid measurementAt timestamp");
  }

  return await db.transaction(async (tx) => {
    // 1. Check KR exists in workspace
    const [kr] = await tx
      .select()
      .from(keyResults)
      .where(and(eq(keyResults.id, krIdBig), eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)))
      .limit(1);

    if (!kr) {
      throw APIError.notFound(`Key result ${input.krId} not found`);
    }

    // 2. Check idempotency
    if (input.idempotencyKey && input.idempotencyKey.trim()) {
      const [existing] = await tx
        .select()
        .from(krObservations)
        .where(
          and(
            eq(krObservations.workspaceId, wsId),
            eq(krObservations.krId, krIdBig),
            eq(krObservations.idempotencyKey, input.idempotencyKey.trim())
          )
        )
        .limit(1);

      if (existing) {
        const progress = computeLinearProgress({
          baseline: kr.baselineValue,
          target: kr.targetValue,
          current: kr.currentValue,
        });

        return {
          id: existing.id,
          workspaceId: existing.workspaceId.toString(),
          krId: existing.krId.toString(),
          valueDecimal: existing.valueDecimal,
          measurementAt: existing.measurementAt.toISOString(),
          windowStart: existing.windowStart ? existing.windowStart.toISOString() : null,
          windowEnd: existing.windowEnd ? existing.windowEnd.toISOString() : null,
          evidenceRefs: (existing.evidenceRefs as unknown[]) || [],
          sourceRef: existing.sourceRef,
          recordedBy: existing.recordedBy ? existing.recordedBy.toString() : null,
          metricContractVersion: existing.metricContractVersion,
          idempotencyKey: existing.idempotencyKey,
          createdAt: existing.createdAt.toISOString(),
          projectedProgress: progress,
        };
      }
    }

    // 3. Find latest existing observation measurement timestamp for this KR
    const [latestObs] = await tx
      .select({ measurementAt: krObservations.measurementAt })
      .from(krObservations)
      .where(and(eq(krObservations.workspaceId, wsId), eq(krObservations.krId, krIdBig)))
      .orderBy(desc(krObservations.measurementAt))
      .limit(1);

    const isLatest = !latestObs || measurementAt.getTime() >= latestObs.measurementAt.getTime();

    // 4. Insert observation append-only
    const [created] = await tx
      .insert(krObservations)
      .values({
        workspaceId: wsId,
        krId: krIdBig,
        valueDecimal: numVal.toFixed(4),
        measurementAt,
        windowStart: input.windowStart ? new Date(input.windowStart) : null,
        windowEnd: input.windowEnd ? new Date(input.windowEnd) : null,
        evidenceRefs: input.evidenceRefs || [],
        sourceRef: input.sourceRef || null,
        recordedBy: ctx.userId ? BigInt(ctx.userId) : null,
        metricContractVersion: input.metricContractVersion ?? kr.metricContractVersion ?? null,
        idempotencyKey: input.idempotencyKey ? input.idempotencyKey.trim() : null,
      })
      .returning();

    // 5. If this is latest, update KR's currentValue
    let currentVal = kr.currentValue;
    if (isLatest) {
      currentVal = numVal;
      await tx
        .update(keyResults)
        .set({
          currentValue: numVal,
          updatedAt: new Date(),
        })
        .where(and(eq(keyResults.id, krIdBig), eq(keyResults.workspaceId, wsId)));
    }

    const progress = computeLinearProgress({
      baseline: kr.baselineValue,
      target: kr.targetValue,
      current: currentVal,
    });

    return {
      id: created!.id,
      workspaceId: created!.workspaceId.toString(),
      krId: created!.krId.toString(),
      valueDecimal: created!.valueDecimal,
      measurementAt: created!.measurementAt.toISOString(),
      windowStart: created!.windowStart ? created!.windowStart.toISOString() : null,
      windowEnd: created!.windowEnd ? created!.windowEnd.toISOString() : null,
      evidenceRefs: (created!.evidenceRefs as unknown[]) || [],
      sourceRef: created!.sourceRef,
      recordedBy: created!.recordedBy ? created!.recordedBy.toString() : null,
      metricContractVersion: created!.metricContractVersion,
      idempotencyKey: created!.idempotencyKey,
      createdAt: created!.createdAt.toISOString(),
      projectedProgress: progress,
    };
  });
}
