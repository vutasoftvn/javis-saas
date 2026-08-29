import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { documentReconciliationProposals, bankTransactions, accountingDocuments } = schema;

export interface ReconciliationProposalView {
  id: string;
  workspaceId: string;
  bankTransactionId: string;
  accountingDocumentId: string;
  confidence: string;
  candidateMatch: any;
  status: "PENDING" | "ACCEPTED" | "REJECTED";
  createdAt: string;
}

export async function listReconciliationProposalsService(
  workspaceId: bigint,
  status?: string
): Promise<ReconciliationProposalView[]> {
  const rows = await db
    .select()
    .from(documentReconciliationProposals)
    .where(eq(documentReconciliationProposals.workspaceId, workspaceId));

  let filtered = rows;
  if (status) {
    filtered = rows.filter((r) => r.status.toUpperCase() === status.toUpperCase());
  }

  return filtered.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    bankTransactionId: String(r.bankTransactionId),
    accountingDocumentId: String(r.accountingDocumentId),
    confidence: String(r.confidence),
    candidateMatch: r.candidateMatch,
    status: r.status as any,
    createdAt: r.createdAt.toISOString(),
  }));
}

export async function proposeReconciliationService(p: {
  workspaceId: bigint;
  bankTransactionId: bigint;
  accountingDocumentId: bigint;
  confidence: number;
  candidateMatch?: any;
}): Promise<ReconciliationProposalView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(documentReconciliationProposals)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      bankTransactionId: p.bankTransactionId,
      accountingDocumentId: p.accountingDocumentId,
      confidence: String(p.confidence) as any,
      candidateMatch: p.candidateMatch ?? {},
      status: "PENDING",
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    bankTransactionId: String(created.bankTransactionId),
    accountingDocumentId: String(created.accountingDocumentId),
    confidence: String(created.confidence),
    candidateMatch: created.candidateMatch,
    status: created.status as any,
    createdAt: created.createdAt.toISOString(),
  };
}

export async function acceptReconciliationProposalService(p: {
  proposalId: bigint;
  workspaceId: bigint;
  acceptedBy: bigint;
}): Promise<ReconciliationProposalView> {
  return await db.transaction(async (tx) => {
    // Resolve proposal TRONG workspace của ctx.
    const [prop] = await tx
      .select()
      .from(documentReconciliationProposals)
      .where(
        and(
          eq(documentReconciliationProposals.id, p.proposalId),
          eq(documentReconciliationProposals.workspaceId, p.workspaceId)
        )
      );

    if (!prop) {
      throw APIError.notFound(`Reconciliation proposal '${p.proposalId}' not found`);
    }
    if (prop.status !== "PENDING") {
      throw APIError.failedPrecondition(
        `Reconciliation proposal '${p.proposalId}' is ${prop.status}, not PENDING`
      );
    }

    // Bank transaction + accounting document phải cùng workspace với proposal.
    const [bankTx] = await tx
      .select()
      .from(bankTransactions)
      .where(
        and(
          eq(bankTransactions.id, prop.bankTransactionId),
          eq(bankTransactions.workspaceId, p.workspaceId)
        )
      );
    if (!bankTx) {
      throw APIError.failedPrecondition("Linked bank transaction is not in this workspace");
    }
    if (bankTx.status !== "UNRECONCILED") {
      throw APIError.failedPrecondition(
        `Bank transaction is ${bankTx.status}, cannot accept a new match`
      );
    }

    const [doc] = await tx
      .select()
      .from(accountingDocuments)
      .where(
        and(
          eq(accountingDocuments.id, prop.accountingDocumentId),
          eq(accountingDocuments.workspaceId, p.workspaceId)
        )
      );
    if (!doc) {
      throw APIError.failedPrecondition(
        "Linked accounting document is not in this workspace"
      );
    }
    if (doc.status === "VOID") {
      throw APIError.failedPrecondition("Linked accounting document is VOID");
    }

    const now = new Date();
    // Mark proposal accepted — ghi acceptedBy, re-check PENDING chống race.
    const acceptedRows = await tx
      .update(documentReconciliationProposals)
      .set({ status: "ACCEPTED", acceptedBy: p.acceptedBy, acceptedAt: now })
      .where(
        and(
          eq(documentReconciliationProposals.id, p.proposalId),
          eq(documentReconciliationProposals.workspaceId, p.workspaceId),
          eq(documentReconciliationProposals.status, "PENDING")
        )
      )
      .returning();
    if (acceptedRows.length === 0) {
      throw APIError.failedPrecondition("Reconciliation proposal is no longer PENDING");
    }
    const [updatedProp] = acceptedRows;

    // Link bank transaction (scoped theo workspace).
    await tx
      .update(bankTransactions)
      .set({
        status: "MATCHED",
        matchedAccountingDocumentId: prop.accountingDocumentId,
        updatedAt: now,
      })
      .where(
        and(
          eq(bankTransactions.id, prop.bankTransactionId),
          eq(bankTransactions.workspaceId, p.workspaceId)
        )
      );

    return {
      id: String(updatedProp.id),
      workspaceId: String(updatedProp.workspaceId),
      bankTransactionId: String(updatedProp.bankTransactionId),
      accountingDocumentId: String(updatedProp.accountingDocumentId),
      confidence: String(updatedProp.confidence),
      candidateMatch: updatedProp.candidateMatch,
      status: "ACCEPTED",
      createdAt: updatedProp.createdAt.toISOString(),
    };
  });
}
