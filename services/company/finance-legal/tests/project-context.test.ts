import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { makeTenantContext } from "../../operations/tests/tenant-context.fixture";
import { getBudgetSummary } from "../services/budget-summary.service";
import { recordFinancialTransactionService } from "../services/financial-transaction.service";

async function makeProject(workspaceId: string, title = "Finance Project"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title });
  return id.toString();
}

describe("Finance & Legal Project Context Scoping", () => {
  it("rejects getBudgetSummary for a project belonging to another workspace", async () => {
    const a = await createTestSession({ role: "founder" });
    const b = await createTestSession({ role: "founder" });
    const ctxA = makeTenantContext({ workspaceId: a.workspaceId, userId: a.userId });
    const projectB = await makeProject(b.workspaceId);

    await expect(getBudgetSummary(ctxA, projectB)).rejects.toThrow(/project/i);
  });

  it("rejects recording financial transaction with another workspace's projectId", async () => {
    const a = await createTestSession({ role: "founder" });
    const b = await createTestSession({ role: "founder" });
    const projectB = await makeProject(b.workspaceId);

    await expect(
      recordFinancialTransactionService({
        workspaceId: a.workspaceId,
        projectId: projectB,
        transactionDate: "2026-09-10",
        description: "Cross-project transaction",
        amount: "500000",
        direction: "OUT",
        authorization: "Bearer " + a.accessToken,
      })
    ).rejects.toThrow(/project/i);
  });

  it("succeeds recording financial transaction with own workspace's projectId", async () => {
    const a = await createTestSession({ role: "founder" });
    const projectA = await makeProject(a.workspaceId);

    const tx = await recordFinancialTransactionService({
      workspaceId: a.workspaceId,
      projectId: projectA,
      transactionDate: "2026-09-10",
      description: "Valid project transaction",
      amount: "500000",
      direction: "OUT",
      authorization: "Bearer " + a.accessToken,
    });

    expect(tx.projectId).toBe(projectA);
  });
});
