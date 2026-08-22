import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { recordFinancialTransaction, getFinancialTransaction, listFinancialTransactions } from "./financial-transaction";

describe("recordFinancialTransaction", () => {
  it("records a transaction with the exact decimal amount as a string", async () => {
    const workspace = await createWorkspace({ name: "Txn Test Inc" });
    const txn = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-15",
      description: "Client invoice payment",
      amount: "12345678.90",
      direction: "IN",
    });
    expect(txn.id).toBeGreaterThan(0);
    expect(txn.amount).toBe("12345678.90");
    expect(txn.direction).toBe("IN");
  });

  it("rejects a transaction for a workspace that doesn't exist", async () => {
    await expect(
      recordFinancialTransaction({
        workspaceId: 999999999,
        transactionDate: "2026-01-15",
        description: "Orphan",
        amount: "1.00",
        direction: "IN",
      })
    ).rejects.toThrow();
  });

  it("returns the original transaction instead of double-charging for a repeated idempotencyKey", async () => {
    const workspace = await createWorkspace({ name: "Idempotency Txn Test Inc" });

    const first = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-20",
      description: "Vendor payment",
      amount: "999.00",
      direction: "OUT",
      idempotencyKey: "agent-financial-run-7",
    });
    const retried = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-20",
      description: "Vendor payment (retry)",
      amount: "999.00",
      direction: "OUT",
      idempotencyKey: "agent-financial-run-7",
    });

    expect(retried.id).toBe(first.id);
    expect(retried.description).toBe("Vendor payment");

    const { transactions } = await listFinancialTransactions({ workspaceId: workspace.id });
    expect(transactions.filter((t) => t.idempotencyKey === "agent-financial-run-7")).toHaveLength(1);
  });
});

describe("getFinancialTransaction/listFinancialTransactions", () => {
  it("fetches a transaction and lists it by workspace", async () => {
    const workspace = await createWorkspace({ name: "List Txn Test Inc" });
    const created = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-16",
      description: "Fetch me",
      amount: "500.00",
      direction: "OUT",
    });

    const fetched = await getFinancialTransaction({ id: created.id });
    expect(fetched).toEqual(created);

    const { transactions } = await listFinancialTransactions({ workspaceId: workspace.id });
    expect(transactions.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    await expect(getFinancialTransaction({ id: 999999999 })).rejects.toThrow();
  });
});
