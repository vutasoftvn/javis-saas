import { eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";

interface BackfillResult {
  updated: number;
  disabled: number;
  skippedDueToFetchError: number;
}

export async function backfillLegacyScheduleProjectIds(
  companyBaseUrl: string,
  serviceToken?: string
): Promise<BackfillResult> {
  const rows = await db
    .select()
    .from(schema.workspaceScheduleDefinitions)
    .where(isNull(schema.workspaceScheduleDefinitions.projectId));

  let updated = 0;
  let disabled = 0;
  let skippedDueToFetchError = 0;

  // Sequential backfill loop (intentional — bounded one-off migration, not concurrent)
  for (const row of rows) {
    try {
      const token = serviceToken || process.env.COSA_WORKER_SERVICE_TOKEN || "dev-worker-service-token";
      const resp = await fetch(
        `${companyBaseUrl}/operations/projects`,
        {
          method: "GET",
          headers: {
            "X-Workspace-Id": row.workspaceId,
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (!resp.ok) {
        console.warn(`Fetch failed for workspace ${row.workspaceId}: ${resp.status}. Skipping row.`);
        skippedDueToFetchError += 1;
        continue;
      }

      const body = await resp.json();
      const firstProjectId: string | undefined = body.projects?.[0]?.id;

      if (firstProjectId) {
        await db
          .update(schema.workspaceScheduleDefinitions)
          .set({ projectId: firstProjectId, isLegacyUnscoped: true, updatedAt: new Date() })
          .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
        updated += 1;
      } else {
        // Workspace confirmed to have zero projects — safe to pause the schedule
        await db
          .update(schema.workspaceScheduleDefinitions)
          .set({ state: "paused", updatedAt: new Date() })
          .where(eq(schema.workspaceScheduleDefinitions.id, row.id));
        disabled += 1;
      }
    } catch (err) {
      console.warn(`Fetch threw for workspace ${row.workspaceId}: ${err instanceof Error ? err.message : String(err)}. Skipping row.`);
      skippedDueToFetchError += 1;
    }
  }

  return { updated, disabled, skippedDueToFetchError };
}

if (require.main === module) {
  const companyBaseUrl = process.env.COMPANY_SERVICE_URL || "http://localhost:4000";
  backfillLegacyScheduleProjectIds(companyBaseUrl).then((result) => {
    console.log(`Backfill complete: ${result.updated} updated, ${result.disabled} disabled, ${result.skippedDueToFetchError} skipped due to fetch errors`);
    process.exit(0);
  });
}
