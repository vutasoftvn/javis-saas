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
  acceptedBy: bigint;
}): Promise<ReconciliationProposalView> {
  return await db.transaction(async (tx) => {
    const [prop] = await tx
      .select()
      .from(documentReconciliationProposals)
      .where(eq(documentReconciliationProposals.id, p.proposalId));

    if (!prop) {
      throw APIError.notFound(`Reconciliation proposal '${p.proposalId}' not found`);
    }

    // Mark proposal accepted
    const [updatedProp] = await tx
      .update(documentReconciliationProposals)
      .set({ status: "ACCEPTED" })
      .where(eq(documentReconciliationProposals.id, p.proposalId))
      .returning();

    // Link bank transaction
    await tx
      .update(bankTransactions)
      .set({
        status: "MATCHED",
        matchedAccountingDocumentId: prop.accountingDocumentId,
        updatedAt: new Date(),
      })
      .where(eq(bankTransactions.id, prop.bankTransactionId));

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
