import { describe, expect, it } from "vitest";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { recordFinancialTransaction } from "../handlers/financial-transaction.handler";
import { raiseFinanceException, getFinanceException, resolveFinanceException } from "../handlers/finance-exception.handler";

describe("raiseFinanceException", () => {
  it("raises an exception linked to a transaction with the default WARNING severity", async () => {
    const workspace = await createWorkspace({ name: "Exception Test Inc" });
    const txn = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-15",
      description: "Suspicious txn",
      amount: "999999.99",
      direction: "OUT",
    });

    const exception = await raiseFinanceException({
      workspaceId: workspace.id,
      transactionId: txn.id,
      exceptionType: "UNUSUAL_AMOUNT",
    });
    expect(exception.id).toBeGreaterThan(0);
    expect(exception.severity).toBe("WARNING");
    expect(exception.status).toBe("OPEN");
  });

  it("rejects an exception for a workspace that doesn't exist", async () => {
    await expect(
      raiseFinanceException({ workspaceId: 999999999, exceptionType: "ORPHAN" })
    ).rejects.toThrow();
  });
});

describe("getFinanceException/resolveFinanceException", () => {
  it("fetches an exception and resolves it", async () => {
    const workspace = await createWorkspace({ name: "Resolve Exception Test Inc" });
    const created = await raiseFinanceException({ workspaceId: workspace.id, exceptionType: "MISSING_RECEIPT" });

    const fetched = await getFinanceException({ id: created.id });
    expect(fetched).toEqual(created);

    const resolved = await resolveFinanceException({ id: created.id });
    expect(resolved.status).toBe("RESOLVED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getFinanceException({ id: 999999999 })).rejects.toThrow();
  });
});
