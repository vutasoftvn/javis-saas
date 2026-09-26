import { describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { createBankConnectionService } from "../services/bank-connection.service";
import { ingestBankTransactionService } from "../services/bank-transaction.service";
import { createDraftDocumentService } from "../services/accounting-document.service";
import { postReconciliationProposal } from "../handlers/finance-tt58.handler";

// Agent tài chính (finance.transaction.classify_propose) tạo đề xuất đối soát
// PENDING qua POST /finance/reconciliation-proposals.
function delegation(userId: string, workspaceId: string, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${userId}`,
    workspace_id: workspaceId,
    run_id: "run-reconcile",
    capability_ids: capabilityIds,
  })}`;
}

async function seedPair(workspaceId: string) {
  const wsId = BigInt(workspaceId);
  const conn = await createBankConnectionService({
    workspaceId: wsId,
    provider: "cas",
    secretRef: `secret://cosa-connectors/cas/ws_${workspaceId}`,
  });
  const txn = await ingestBankTransactionService({
    workspaceId: wsId,
    bankConnectionId: BigInt(conn.id),
    externalTransactionId: `cas_txn_${workspaceId}`,
    postedAt: "2026-09-20T10:00:00Z",
    amount: "2000000",
    currency: "VND",
    direction: "IN",
    description: "Thanh toan hop dong",
  });
  const doc = await createDraftDocumentService({
    workspaceId: wsId,
    documentType: "RECEIPT",
    number: `PT-${workspaceId}`,
    documentDate: "2026-09-20",
    amount: "2000000",
    description: "Phieu thu hop dong",
  });
  return { txnId: txn.id, docId: doc.id };
}

describe("POST /finance/reconciliation-proposals", () => {
  it("lets the finance agent propose a match inside its workspace", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const { txnId, docId } = await seedPair(ws.workspaceId);

    const proposal = await postReconciliationProposal({
      workspaceId: ws.workspaceId,
      authorization: delegation(ws.userId, ws.workspaceId, ["finance.transaction.classify_propose"]),
      bankTransactionId: txnId,
      accountingDocumentId: docId,
      confidence: 0.92,
    });
    expect(proposal.status).toBe("PENDING");
    expect(proposal.workspaceId).toBe(ws.workspaceId);
  });

  it("rejects a delegation without classify_propose", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const { txnId, docId } = await seedPair(ws.workspaceId);

    await expect(
      postReconciliationProposal({
        workspaceId: ws.workspaceId,
        authorization: delegation(ws.userId, ws.workspaceId, ["finance.transaction.read"]),
        bankTransactionId: txnId,
        accountingDocumentId: docId,
        confidence: 0.9,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("does not match records from another workspace", async () => {
    const a = await createTestWorkspaceWithMember({ role: "founder" });
    const b = await createTestWorkspaceWithMember({ role: "founder" });
    const other = await seedPair(b.workspaceId);

    await expect(
      postReconciliationProposal({
        workspaceId: a.workspaceId,
        authorization: a.bearerToken,
        bankTransactionId: other.txnId,
        accountingDocumentId: other.docId,
        confidence: 0.9,
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("rejects confidence outside 0..1 and non-numeric ids", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const { txnId, docId } = await seedPair(ws.workspaceId);

    await expect(
      postReconciliationProposal({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        bankTransactionId: txnId,
        accountingDocumentId: docId,
        confidence: 1.5,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
    await expect(
      postReconciliationProposal({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        bankTransactionId: "abc",
        accountingDocumentId: docId,
        confidence: 0.5,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });
});
