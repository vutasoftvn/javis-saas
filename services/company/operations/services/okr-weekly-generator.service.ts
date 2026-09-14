// services/company/operations/services/okr-weekly-generator.service.ts
//
// Sinh khung Operating Cycle + weekly_plans rỗng từ 1 Objective OKR đã
// publish. Không tự tạo initiative/commitment — founder/agent gắn KR vào
// từng tuần thủ công sau đó; generator chỉ dựng khung 12-week-cycle theo
// đúng durationWeeks yêu cầu.
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  createCycleAuthorized,
  createWeeklyPlanAuthorized,
  CycleDto,
} from "./project-operating-loop.service";

const { okrObjectives, twelveWeekCycles } = schema;

export async function generateCycleFromObjective(
  ctx: TenantContext,
  objectiveId: string,
  durationWeeks: number
): Promise<CycleDto> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(objectiveId);

  const [objective] = await db
    .select()
    .from(okrObjectives)
    .where(eq(okrObjectives.id, objId))
    .limit(1);

  if (!objective || objective.workspaceId !== wsId) {
    throw APIError.notFound(`Objective ${objectiveId} not found`);
  }
  if (objective.status !== "published") {
    throw APIError.failedPrecondition("Objective must be published before generating a weekly cycle");
  }

  const cycle = await createCycleAuthorized(ctx, {
    projectId: objective.projectId.toString(),
    durationWeeks,
  });

  await db
    .update(twelveWeekCycles)
    .set({ sourceObjectiveId: objId })
    .where(eq(twelveWeekCycles.id, BigInt(cycle.id)));

  for (let weekNo = 1; weekNo <= durationWeeks; weekNo++) {
    await createWeeklyPlanAuthorized(ctx, {
      projectId: objective.projectId.toString(),
      cycleId: cycle.id,
      weekNo,
    });
  }

  return { ...cycle, sourceObjectiveId: objectiveId };
}
