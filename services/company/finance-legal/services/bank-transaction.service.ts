import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { bankTransactions } = schema;

export interface BankTransactionView {
  id: string;
  workspaceId: string;
  bankConnectionId: string;
  ingestionEventId: string | null;
  externalTransactionId: string;
  postedAt: string;
  amount: string;
  currency: string;
  direction: "IN" | "OUT";
  description: string;
  counterpartyName: string | null;
  counterpartyAccount: string | null;
  status: "UNRECONCILED" | "MATCHED" | "CONFIRMED";
  matchedAccountingDocumentId: string | null;
  createdAt: string;
}

export async function listBankTransactionsService(
  workspaceId: bigint,
  status?: string
): Promise<BankTransactionView[]> {
  const rows = await db
    .select()
    .from(bankTransactions)
    .where(eq(bankTransactions.workspaceId, workspaceId))
    .orderBy(desc(bankTransactions.postedAt));

  let filtered = rows;
  if (status) {
    filtered = rows.filter((r) => r.status.toUpperCase() === status.toUpperCase());
  }

  return filtered.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    bankConnectionId: String(r.bankConnectionId),
    ingestionEventId: r.ingestionEventId ? String(r.ingestionEventId) : null,
    externalTransactionId: r.externalTransactionId,
    postedAt: r.postedAt.toISOString(),
    amount: String(r.amount),
    currency: r.currency,
    direction: r.direction as any,
    description: r.description,
    counterpartyName: r.counterpartyName,
    counterpartyAccount: r.counterpartyAccount,
    status: r.status as any,
    matchedAccountingDocumentId: r.matchedAccountingDocumentId
      ? String(r.matchedAccountingDocumentId)
      : null,
    createdAt: r.createdAt.toISOString(),
  }));
}

export async function ingestBankTransactionService(p: {
  workspaceId: bigint;
  bankConnectionId: bigint;
  ingestionEventId?: bigint;
  externalTransactionId: string;
  postedAt: string;
  amount: string | number;
  currency?: string;
  direction: "IN" | "OUT";
  description: string;
  counterpartyName?: string;
  counterpartyAccount?: string;
  rawPayload?: any;
}): Promise<BankTransactionView> {
  // Idempotent upsert based on (bank_connection_id, external_transaction_id)
  const [existing] = await db
    .select()
    .from(bankTransactions)
    .where(
      and(
        eq(bankTransactions.bankConnectionId, p.bankConnectionId),
        eq(bankTransactions.externalTransactionId, p.externalTransactionId)
      )
    );

  if (existing) {
    return {
      id: String(existing.id),
      workspaceId: String(existing.workspaceId),
      bankConnectionId: String(existing.bankConnectionId),
      ingestionEventId: existing.ingestionEventId ? String(existing.ingestionEventId) : null,
      externalTransactionId: existing.externalTransactionId,
      postedAt: existing.postedAt.toISOString(),
      amount: String(existing.amount),
      currency: existing.currency,
      direction: existing.direction as any,
      description: existing.description,
      counterpartyName: existing.counterpartyName,
      counterpartyAccount: existing.counterpartyAccount,
      status: existing.status as any,
      matchedAccountingDocumentId: existing.matchedAccountingDocumentId
        ? String(existing.matchedAccountingDocumentId)
        : null,
      createdAt: existing.createdAt.toISOString(),
    };
  }

  const newId = generateSnowflake();
  const [created] = await db
    .insert(bankTransactions)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      bankConnectionId: p.bankConnectionId,
      ingestionEventId: p.ingestionEventId ?? null,
      externalTransactionId: p.externalTransactionId,
      postedAt: new Date(p.postedAt),
      amount: String(p.amount) as any,
      currency: p.currency || "VND",
      direction: p.direction,
      description: p.description,
      counterpartyName: p.counterpartyName ?? null,
      counterpartyAccount: p.counterpartyAccount ?? null,
      rawPayload: p.rawPayload ?? null,
      status: "UNRECONCILED",
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    bankConnectionId: String(created.bankConnectionId),
    ingestionEventId: created.ingestionEventId ? String(created.ingestionEventId) : null,
    externalTransactionId: created.externalTransactionId,
    postedAt: created.postedAt.toISOString(),
    amount: String(created.amount),
    currency: created.currency,
    direction: created.direction as any,
    description: created.description,
    counterpartyName: created.counterpartyName,
    counterpartyAccount: created.counterpartyAccount,
    status: created.status as any,
    matchedAccountingDocumentId: null,
    createdAt: created.createdAt.toISOString(),
  };
}
