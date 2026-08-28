import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db } from "../../db";
import {
  engagementThreads,
  engagementThreadOutcomes,
} from "../../../shared/db/schema/customer-engagement";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { evaluateRulesSafe } from "./automation/evaluator";

export interface RecordCsatInput {
  score: number; // 1..5
  comment?: string;
}

export interface RecordCsatResult {
  outcomeId: string;
}

export async function recordCsat(
  threadId: string,
  input: RecordCsatInput,
  ctx: TenantContext
): Promise<RecordCsatResult> {
  const wsId = BigInt(ctx.workspaceId);
  const tId = BigInt(threadId);

  if (input.score < 1 || input.score > 5) {
    throw APIError.invalidArgument("CSAT score must be between 1 and 5");
  }

  // 1. Verify thread exists
  const threads = await db
    .select()
    .from(engagementThreads)
    .where(and(eq(engagementThreads.id, tId), eq(engagementThreads.workspaceId, wsId)));

  if (threads.length === 0) {
    throw APIError.notFound("Thread not found");
  }

  // 2. Check existing outcome or create new
  const existingOutcomes = await db
    .select()
    .from(engagementThreadOutcomes)
    .where(and(eq(engagementThreadOutcomes.threadId, tId), eq(engagementThreadOutcomes.workspaceId, wsId)));

  let outcomeId: bigint;
  if (existingOutcomes.length > 0) {
    outcomeId = existingOutcomes[0].id;
    await db
      .update(engagementThreadOutcomes)
      .set({
        csatScore: input.score,
        csatRecordedAt: new Date(),
      })
      .where(eq(engagementThreadOutcomes.id, outcomeId));
  } else {
    outcomeId = generateSnowflake();
    await db.insert(engagementThreadOutcomes).values({
      id: outcomeId,
      workspaceId: wsId,
      threadId: tId,
      csatScore: input.score,
      csatRecordedAt: new Date(),
    });
  }

  // 3. Trigger automation rule evaluation safely
  await evaluateRulesSafe({ trigger: "csat_recorded", threadId }, ctx);

  return { outcomeId: outcomeId.toString() };
}
