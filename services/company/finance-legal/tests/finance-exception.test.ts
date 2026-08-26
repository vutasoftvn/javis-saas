import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { recordFinancialTransaction } from "../handlers/financial-transaction.handler";
import { raiseFinanceException, getFinanceException, resolveFinanceException } from "../handlers/finance-exception.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("raiseFinanceException", () => {
  it("raises an exception linked to a transaction with the default WARNING severity", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Exception Test Inc");
    const txn = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-15",
      description: "Suspicious txn",
      amount: "999999.99",
      direction: "OUT",
      authorization,
    });

    const exception = await raiseFinanceException({
      workspaceId,
      transactionId: txn.id,
      exceptionType: "UNUSUAL_AMOUNT",
      authorization,
    });
    expect(exception.id).toBeTruthy();
    expect(exception.severity).toBe("WARNING");
    expect(exception.status).toBe("OPEN");
  });

  it("rejects an exception for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Exception Test");
    await expect(
      raiseFinanceException({ workspaceId: "999999999", exceptionType: "ORPHAN", authorization })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Exception Ws");
    const outsider = await makeAuthedWorkspace("Outsider Exception Test");
    await expect(
      raiseFinanceException({ workspaceId, exceptionType: "ORPHAN", authorization: outsider.authorization })
    ).rejects.toThrow();
  });
});

describe("getFinanceException/resolveFinanceException", () => {
  it("fetches an exception and resolves it", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Resolve Exception Test Inc");
    const created = await raiseFinanceException({
      workspaceId,
      exceptionType: "MISSING_RECEIPT",
      authorization,
    });

    const fetched = await getFinanceException({ id: created.id, authorization });
    expect(fetched).toEqual(created);

    const resolved = await resolveFinanceException({ id: created.id, authorization });
    expect(resolved.status).toBe("RESOLVED");
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Exception Test");
    await expect(getFinanceException({ id: "999999999", authorization })).rejects.toThrow();
  });
});
