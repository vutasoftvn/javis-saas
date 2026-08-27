import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { generateAndRankNextActions, RankedAction } from "../services/next-best-action.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const {
  projects,
  assumptions,
  tasks,
  keyResults,
  okrObjectives,
  okrCycles,
  nextActionCandidates,
  nextActionRankings,
} = schema;

export interface NextBestActionsResponse {
  projectId: string | number;
  items: RankedAction[];
  generatedAt: string;
}

export const getNextBestActions = api(
  { method: "GET", path: "/operations/strategy/projects/:id/next-best-actions", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<NextBestActionsResponse> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    // 1. Verify project exists and belongs to workspace
    const projectRow = await getProjectInWorkspace(id, ctx);

    const projectIdBigInt = BigInt(id);

    // 2. Fetch assumptions for this project
    const assumptionRows = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.projectId, projectIdBigInt), eq(assumptions.workspaceId, wsId), isNull(assumptions.deletedAt)));

    // 3. Fetch blocked tasks in workspace
    const blockedTaskRows = await db
      .select()
      .from(tasks)
      .where(and(eq(tasks.workspaceId, wsId), eq(tasks.status, "blocked"), isNull(tasks.deletedAt)));

    // 4. Fetch key results with progress gaps
    const krRows = await db
      .select({
        id: keyResults.id,
        title: keyResults.title,
        currentValue: keyResults.currentValue,
        targetValue: keyResults.targetValue,
      })
      .from(keyResults)
      .where(and(eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)));

    const okrGaps = krRows.map((kr) => {
      const curr = kr.currentValue ?? 0;
      const target = kr.targetValue ?? 100;
      const progress = target > 0 ? (curr / target) * 100 : 0;
      const gapPercentage = Math.max(0, Math.min(100, Math.round(100 - progress)));
      return {
        id: kr.id.toString(),
        title: kr.title || "Key Result",
        currentValue: curr,
        targetValue: target,
        gapPercentage,
      };
    }).filter((k) => k.gapPercentage > 0);

    // 5. Generate and rank next actions deterministically
    const rankedActions = generateAndRankNextActions({
      projectId: id,
      currentStage: projectRow.phase ?? "S0_GENESIS",
      untestedAssumptions: assumptionRows.map((a) => ({
        id: a.id.toString(),
        statement: a.statement,
        importance: a.importance,
        uncertainty: a.uncertainty,
        riskScore: a.riskScore,
        status: a.status,
      })),
      blockedTasks: blockedTaskRows.map((t) => ({
        id: t.id.toString(),
        title: t.title,
        priority: t.priority,
        status: t.status,
      })),
      okrGaps,
    });

    // 6. Persist candidates & rankings in background/transaction for audit trail
    if (rankedActions.length > 0) {
      for (const item of rankedActions) {
        const [candidateRow] = await db
          .insert(nextActionCandidates)
          .values({
            id: generateSnowflake(),
            workspaceId: wsId,
            projectId: projectIdBigInt,
            source: item.candidate.source,
            score: item.candidate.score,
            rationale: item.candidate.rationale,
          })
          .returning();

        if (candidateRow) {
          await db
            .insert(nextActionRankings)
            .values({
              id: generateSnowflake(),
              workspaceId: wsId,
              projectId: projectIdBigInt,
              candidateId: candidateRow.id,
              rank: item.rank,
              llmRerankNote: item.llmRerankNote ?? null,
            });
        }
      }
    }

    return {
      projectId: id,
      items: rankedActions,
      generatedAt: new Date().toISOString(),
    };
  }
);
