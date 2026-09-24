import { eq, isNull, isNotNull } from "drizzle-orm";
import { db, schema } from "../models/db";

export interface BackfillResult {
  pausedDefinitionIds: string[];
  alreadyBoundDefinitionIds: string[];
  skippedDefinitionIds: string[];
}

export async function backfillLegacyScheduleProjectIds(
  _companyBaseUrl?: string,
  _serviceToken?: string
): Promise<BackfillResult> {
  const boundRows = await db
    .select({ id: schema.workspaceScheduleDefinitions.id })
    .from(schema.workspaceScheduleDefinitions)
    .where(isNotNull(schema.workspaceScheduleDefinitions.projectId));
  const alreadyBoundDefinitionIds = boundRows.map((r) => r.id);

  const rows = await db
    .select()
    .from(schema.workspaceScheduleDefinitions)
    .where(isNull(schema.workspaceScheduleDefinitions.projectId));

  const pausedDefinitionIds: string[] = [];
  const skippedDefinitionIds: string[] = [];

  for (const row of rows) {
    try {
      console.log(
        `[ScheduleRemediation] Pausing legacy schedule definition_id=${row.id} workspace_id=${row.organizationId} reason=PROJECT_CONTEXT_REQUIRED`
      );
      await db
        .update(schema.workspaceScheduleDefinitions)
        .set({
          state: "paused",
          isLegacyUnscoped: true,
          updatedAt: new Date(),
        })
        .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
      pausedDefinitionIds.push(row.id);
    } catch (err) {
      console.error(
        `[ScheduleRemediation] Failed to pause definition_id=${row.id} workspace_id=${row.organizationId}: ${err instanceof Error ? err.message : String(err)}`
      );
      skippedDefinitionIds.push(row.id);
    }
  }

  return { pausedDefinitionIds, alreadyBoundDefinitionIds, skippedDefinitionIds };
}

if (require.main === module) {
  backfillLegacyScheduleProjectIds().then((result) => {
    console.log(
      `Remediation complete: ${result.pausedDefinitionIds.length} paused, ${result.alreadyBoundDefinitionIds.length} already bound, ${result.skippedDefinitionIds.length} skipped`
    );
    process.exit(0);
  });
}

