import { describe, expect, it } from "vitest";
import { eq, and } from "drizzle-orm";
import { registerUserService } from "../../identity/services/auth.service";
import { db as identityDb, schema as identitySchema } from "../../identity/models/db";
import {
  recordFinancialTransaction,
  approveFinancialTransaction,
  getFinancialTransaction,
  listFinancialTransactions,
} from "../handlers/financial-transaction.handler";

const { identityWorkspaceMembers } = identitySchema;

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, userId: user.userId, authorization: `Bearer ${user.accessToken}` };
}

describe("recordFinancialTransaction", () => {
  it("records a transaction with the exact decimal amount as a string", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Txn Test Inc");
    const txn = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-15",
      description: "Client invoice payment",
      amount: "12345678.90",
      direction: "IN",
      authorization,
    });
    expect(txn.id).toBeTruthy();
    expect(txn.amount).toBe("12345678.90");
    expect(txn.direction).toBe("IN");
  });

  it("rejects a transaction for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Test");
    await expect(
      recordFinancialTransaction({
        workspaceId: 999999999,
        transactionDate: "2026-01-15",
        description: "Orphan",
        amount: "1.00",
        direction: "IN",
        authorization,
      })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Txn Ws");
    const outsider = await makeAuthedWorkspace("Outsider Txn Test");
    await expect(
      recordFinancialTransaction({
        workspaceId,
        transactionDate: "2026-01-15",
        description: "Should be blocked",
        amount: "1.00",
        direction: "IN",
        authorization: outsider.authorization,
      })
    ).rejects.toThrow();
  });

  it("returns the original transaction instead of double-charging for a repeated idempotencyKey", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Idempotency Txn Test Inc");

    const first = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-20",
      description: "Vendor payment",
      amount: "999.00",
      direction: "OUT",
      idempotencyKey: "agent-financial-run-7",
      authorization,
    });
    const retried = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-20",
      description: "Vendor payment (retry)",
      amount: "999.00",
      direction: "OUT",
      idempotencyKey: "agent-financial-run-7",
      authorization,
    });

    expect(retried.id).toBe(first.id);
    expect(retried.description).toBe("Vendor payment");

    const { transactions } = await listFinancialTransactions({ workspaceId, authorization });
    expect(transactions.filter((t) => t.idempotencyKey === "agent-financial-run-7")).toHaveLength(1);
  });
});

describe("getFinancialTransaction/listFinancialTransactions", () => {
  it("fetches a transaction and lists it by workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("List Txn Test Inc");
    const created = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-16",
      description: "Fetch me",
      amount: "500.00",
      direction: "OUT",
      authorization,
    });

    const fetched = await getFinancialTransaction({ id: created.id, authorization });
    expect(fetched).toEqual(created);

    const { transactions } = await listFinancialTransactions({ workspaceId, authorization });
    expect(transactions.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Txn Test");
    await expect(getFinancialTransaction({ id: 999999999, authorization })).rejects.toThrow();
  });
});

describe("approveFinancialTransaction (approval gate for large OUT transactions)", () => {
  it("marks a large OUT transaction as PENDING_APPROVAL instead of recording it outright", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Approval Gate Test Inc");
    const txn = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-18",
      description: "Vendor payout above threshold",
      amount: "50000000.00",
      direction: "OUT",
      authorization,
    });

    expect(txn.approvalStatus).toBe("PENDING_APPROVAL");
  });

  it("auto-approves a small OUT transaction and any IN transaction", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Auto Approve Test Inc");
    const small = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-18",
      description: "Small vendor payout",
      amount: "1000.00",
      direction: "OUT",
      authorization,
    });
    const incoming = await recordFinancialTransaction({
      workspaceId,
      transactionDate: "2026-01-18",
      description: "Large client payment",
      amount: "50000000.00",
      direction: "IN",
      authorization,
    });

    expect(small.approvalStatus).toBe("AUTO_APPROVED");
    expect(incoming.approvalStatus).toBe("AUTO_APPROVED");
  });

  it("rejects approval from a member without founder/co-founder permission", async () => {
    const user = await registerUserService({
      email: `finance-approve-denied-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      password: "Password123!",
      displayName: "Regular Admin",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const txn = await recordFinancialTransaction({
      workspaceId: user.workspaceId,
      transactionDate: "2026-01-18",
      description: "Needs approval",
      amount: "20000000.00",
      direction: "OUT",
      authorization,
    });

    await expect(
      approveFinancialTransaction({
        id: txn.id,
        authorization,
      })
    ).rejects.toThrow();
  });

  it("approves once caller has founder permission, and rejects a second approval attempt", async () => {
    const user = await registerUserService({
      email: `finance-approve-ok-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      password: "Password123!",
      displayName: "Founder User",
    });
    const authorization = `Bearer ${user.accessToken}`;

    await identityDb
      .update(identityWorkspaceMembers)
      .set({ role: "founder" })
      .where(
        and(
          eq(identityWorkspaceMembers.workspaceId, BigInt(user.workspaceId)),
          eq(identityWorkspaceMembers.userId, BigInt(user.userId))
        )
      );

    const txn = await recordFinancialTransaction({
      workspaceId: user.workspaceId,
      transactionDate: "2026-01-18",
      description: "Founder-approved payout",
      amount: "20000000.00",
      direction: "OUT",
      authorization,
    });
    expect(txn.approvalStatus).toBe("PENDING_APPROVAL");

    const approved = await approveFinancialTransaction({
      id: txn.id,
      authorization,
    });

    expect(approved.approvalStatus).toBe("APPROVED");
    expect(approved.approvedByUserId).toBe(user.userId);

    await expect(
      approveFinancialTransaction({
        id: txn.id,
        authorization,
      })
    ).rejects.toThrow();
  });
});
