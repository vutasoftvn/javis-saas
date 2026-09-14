import { eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";

export async function backfillLegacyScheduleProjectIds(
  companyBaseUrl: string
): Promise<{ updated: number; disabled: number }> {
  const rows = await db
    .select()
    .from(schema.workspaceScheduleDefinitions)
    .where(isNull(schema.workspaceScheduleDefinitions.projectId));

  let updated = 0;
  let disabled = 0;

  for (const row of rows) {
    const resp = await fetch(
      `${companyBaseUrl}/operations/projects?workspaceId=${encodeURIComponent(row.workspaceId)}`
    );
    const body = resp.ok ? await resp.json() : { projects: [] };
    const firstProjectId: string | undefined = body.projects?.[0]?.id;

    if (firstProjectId) {
      await db
        .update(schema.workspaceScheduleDefinitions)
        .set({ projectId: firstProjectId, isLegacyUnscoped: true, updatedAt: new Date() })
        .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
      updated += 1;
    } else {
      await db
        .update(schema.workspaceScheduleDefinitions)
        .set({ state: "paused", updatedAt: new Date() })
        .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
      disabled += 1;
    }
  }

  return { updated, disabled };
}

if (require.main === module) {
  const companyBaseUrl = process.env.COMPANY_SERVICE_URL || "http://localhost:4000";
  backfillLegacyScheduleProjectIds(companyBaseUrl).then((result) => {
    console.log(`Backfill complete: ${result.updated} updated, ${result.disabled} disabled`);
    process.exit(0);
  });
}
