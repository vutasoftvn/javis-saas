import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { makeTenantContext } from "../../operations/tests/tenant-context.fixture";
import { projects } from "../../shared/db/schema/operations";
import { getBudgetSummary } from "../services/budget-summary.service";
import { getFinancialSnapshotsService } from "../services/financial-snapshot.service";

const { financialSnapshots } = schema;

async function seed() {
  const s = await createTestSession();
  const ctx = makeTenantContext({ workspaceId: s.workspaceId, userId: s.userId });
  const projectId = generateSnowflake();
  await db
    .insert(projects)
    .values({ id: projectId, workspaceId: BigInt(s.workspaceId), title: "Finance RM" });
  return { s, ctx, projectId: projectId.toString() };
}

describe("Founder Trial finance read model — budget vs liquidity are independent and factual", () => {
  it("budget summary reports NO_ENVELOPE with null figures, not a fake zero", async () => {
    const { ctx, projectId } = await seed();
    const summary = await getBudgetSummary(ctx, projectId);

    expect(summary.coverage).toBe("NO_ENVELOPE");
    expect(summary.limitMinor).toBeNull();
    expect(summary.actualPaidMinor).toBeNull();
    expect(summary.remainingAfterCommitmentsMinor).toBeNull();
  });

  it("workspace liquidity is empty (no fabricated snapshot) when CAS has produced nothing", async () => {
    const { ctx } = await seed();
    const snapshots = await getFinancialSnapshotsService(BigInt(ctx.workspaceId));
    expect(snapshots).toEqual([]);
  });

  it("a real workspace snapshot surfaces independently of the project's missing budget", async () => {
    const { s, ctx, projectId } = await seed();
    await db.insert(financialSnapshots).values({
      id: generateSnowflake(),
      workspaceId: BigInt(s.workspaceId),
      snapshotDate: "2026-09-05",
      currency: "VND",
    });

    const [budget, snapshots] = await Promise.all([
      getBudgetSummary(ctx, projectId),
      getFinancialSnapshotsService(BigInt(ctx.workspaceId)),
    ]);

    expect(budget.coverage).toBe("NO_ENVELOPE");
    expect(snapshots).toHaveLength(1);
    expect(snapshots[0].snapshotDate).toBe("2026-09-05");
  });
});
