import { describe, it, expect, beforeEach } from "vitest";
import { db, schema } from "../models/db";
import {
  getAccountingRegimePolicyService,
  setAccountingRegimePolicyService,
} from "../services/accounting-regime-policy.service";
import {
  listBankConnectionsService,
  createBankConnectionService,
  updateConsentStateService,
} from "../services/bank-connection.service";
import { recordIngestionEventService } from "../services/ingestion.service";
import {
  listBankTransactionsService,
  ingestBankTransactionService,
} from "../services/bank-transaction.service";
import {
  listAccountingDocumentsService,
  createDraftDocumentService,
  confirmAccountingDocumentService,
} from "../services/accounting-document.service";
import {
  listReconciliationProposalsService,
  proposeReconciliationService,
  acceptReconciliationProposalService,
} from "../services/reconciliation-proposal.service";
import {
  getFinancialSnapshotsService,
  calculateAndSaveSnapshotService,
} from "../services/financial-snapshot.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("Finance TT58 Ingestion & Accounting Engine", () => {
  const wsId = generateSnowflake();

  it("enforces secretRef format on bank connections (no raw token)", async () => {
    // Should fail with raw token
    await expect(
      createBankConnectionService({
        workspaceId: wsId,
        provider: "cas",
        secretRef: "raw_token_xyz",
      })
    ).rejects.toThrow("Raw tokens are strictly forbidden");

    // Should succeed with secret:// schema
    const conn = await createBankConnectionService({
      workspaceId: wsId,
      provider: "cas",
      secretRef: "secret://cosa-connectors/cas/ws_1",
      scopes: ["balance:read", "transactions:read"],
    });

    expect(conn.id).toBeDefined();
    expect(conn.consentState).toBe("PENDING");
    expect(conn.secretRef).toBe("secret://cosa-connectors/cas/ws_1");

    // Update consent to GRANTED
    const updated = await updateConsentStateService({
      connectionId: BigInt(conn.id),
      consentState: "GRANTED",
    });
    expect(updated.consentState).toBe("GRANTED");
  });

  it("handles ingestion events and deduplicates duplicate provider events", async () => {
    const conn = await createBankConnectionService({
      workspaceId: wsId,
      provider: "cas",
      secretRef: "secret://cosa-connectors/cas/ws_test_dedup",
    });

    const res1 = await recordIngestionEventService({
      bankConnectionId: BigInt(conn.id),
      providerEventId: "evt_webhook_001",
      payloadStr: JSON.stringify({ amount: 1000000 }),
    });
    expect(res1.isDuplicate).toBe(false);

    // Second call with same event id must be detected as duplicate
    const res2 = await recordIngestionEventService({
      bankConnectionId: BigInt(conn.id),
      providerEventId: "evt_webhook_001",
      payloadStr: JSON.stringify({ amount: 1000000 }),
    });
    expect(res2.isDuplicate).toBe(true);
    expect(res2.event.id).toBe(res1.event.id);
  });

  it("ingests bank transactions idempotently and allows document reconciliation", async () => {
    const conn = await createBankConnectionService({
      workspaceId: wsId,
      provider: "cas",
      secretRef: "secret://cosa-connectors/cas/ws_test_txn",
    });

    // Ingest transaction
    const txn = await ingestBankTransactionService({
      workspaceId: wsId,
      bankConnectionId: BigInt(conn.id),
      externalTransactionId: "cas_txn_1001",
      postedAt: "2026-08-29T10:00:00Z",
      amount: "5000000",
      currency: "VND",
      direction: "IN",
      description: "Thanh toan hop dong SaaS #101",
      counterpartyName: "Khach hang ABC",
    });

    expect(txn.id).toBeDefined();
    expect(txn.status).toBe("UNRECONCILED");

    // Re-ingest same transaction -> returns existing
    const txnDup = await ingestBankTransactionService({
      workspaceId: wsId,
      bankConnectionId: BigInt(conn.id),
      externalTransactionId: "cas_txn_1001",
      postedAt: "2026-08-29T10:00:00Z",
      amount: "5000000",
      direction: "IN",
      description: "Thanh toan hop dong SaaS #101",
    });
    expect(txnDup.id).toBe(txn.id);

    // Create Draft Accounting Document
    const doc = await createDraftDocumentService({
      workspaceId: wsId,
      documentType: "RECEIPT",
      number: "PT-2026-001",
      documentDate: "2026-08-29",
      amount: "5000000",
      description: "Phieu thu hop dong SaaS #101",
    });
    expect(doc.status).toBe("DRAFT");

    // Propose Reconciliation
    const proposal = await proposeReconciliationService({
      workspaceId: wsId,
      bankTransactionId: BigInt(txn.id),
      accountingDocumentId: BigInt(doc.id),
      confidence: 0.98,
      candidateMatch: { reason: "Same amount 5000000 VND and description match" },
    });
    expect(proposal.status).toBe("PENDING");

    // Accept Reconciliation Proposal
    const accepted = await acceptReconciliationProposalService({
      proposalId: BigInt(proposal.id),
      acceptedBy: 9999n,
    });
    expect(accepted.status).toBe("ACCEPTED");

    // Verify transaction is now MATCHED
    const txns = await listBankTransactionsService(wsId);
    const matchedTxn = txns.find((t) => t.id === txn.id);
    expect(matchedTxn?.status).toBe("MATCHED");
    expect(matchedTxn?.matchedAccountingDocumentId).toBe(doc.id);

    // Confirm Document
    const confirmedDoc = await confirmAccountingDocumentService({
      documentId: BigInt(doc.id),
      confirmedBy: 9999n,
    });
    expect(confirmedDoc.status).toBe("CONFIRMED");
    expect(confirmedDoc.confirmedBy).toBe("9999");
  });

  it("calculates financial snapshot correctly and computes runway", async () => {
    const snapshot = await calculateAndSaveSnapshotService({
      workspaceId: wsId,
      snapshotDate: "2026-08-29",
    });

    expect(snapshot.workspaceId).toBe(String(wsId));
    expect(parseFloat(snapshot.cashIn)).toBeGreaterThanOrEqual(5000000);
    expect(snapshot.runwayMonths).toBeDefined();
  });
});
