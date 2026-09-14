// services/company/operations/services/okr-weekly-generator.service.ts
//
// Sinh khung Operating Cycle + weekly_plans rỗng từ 1 Objective OKR đã
// publish. Không tự tạo initiative/commitment — founder/agent gắn KR vào
// từng tuần thủ công sau đó; generator chỉ dựng khung 12-week-cycle theo
// đúng durationWeeks yêu cầu.
//
// Task 5 (2026-09-14 remediation) — createCycleAuthorized giờ tự materialize
// toàn bộ weekly_plans 1..durationWeeks VÀ nhận thẳng sourceObjectiveId
// trong cùng 1 lệnh gọi/transaction; generator không còn tự lặp gọi
// createWeeklyPlanAuthorized N lần hay UPDATE sourceObjectiveId tách rời sau
// khi cycle đã commit (2 bước cũ để lộ khoảng hở cycle tồn tại mà thiếu
// tuần/chưa gắn objective).
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createCycleAuthorized, CycleDto } from "./project-operating-loop.service";

const { okrObjectives } = schema;

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

  return createCycleAuthorized(ctx, {
    projectId: objective.projectId.toString(),
    durationWeeks,
    sourceObjectiveId: objectiveId,
  });
}
