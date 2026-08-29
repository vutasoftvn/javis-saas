import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { FINANCE_ACCOUNTING_DOCUMENT_CONFIRMED } from "../../shared/events";
import { randomUUID } from "node:crypto";

const { accountingDocuments } = schema;

export interface AccountingDocumentView {
  id: string;
  workspaceId: string;
  documentType: "RECEIPT" | "PAYMENT" | "INVOICE" | "JOURNAL";
  number: string;
  documentDate: string;
  amount: string;
  currency: string;
  description: string;
  status: "DRAFT" | "CONFIRMED" | "VOID";
  regimePolicyId: string | null;
  lineItems: any[];
  confirmedAt: string | null;
  confirmedBy: string | null;
  voidReason: string | null;
  createdAt: string;
  updatedAt: string;
}

export async function listAccountingDocumentsService(
  workspaceId: bigint,
  status?: string
): Promise<AccountingDocumentView[]> {
  const rows = await db
    .select()
    .from(accountingDocuments)
    .where(eq(accountingDocuments.workspaceId, workspaceId))
    .orderBy(desc(accountingDocuments.documentDate));

  let filtered = rows;
  if (status) {
    filtered = rows.filter((r) => r.status.toUpperCase() === status.toUpperCase());
  }

  return filtered.map((r) => ({
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    documentType: r.documentType as any,
    number: r.number,
    documentDate: typeof r.documentDate === "string" ? r.documentDate : new Date(r.documentDate).toISOString().split("T")[0],
    amount: String(r.amount),
    currency: r.currency,
    description: r.description,
    status: r.status as any,
    regimePolicyId: r.regimePolicyId ? String(r.regimePolicyId) : null,
    lineItems: (r.lineItems || []) as any[],
    confirmedAt: r.confirmedAt ? r.confirmedAt.toISOString() : null,
    confirmedBy: r.confirmedBy ? String(r.confirmedBy) : null,
    voidReason: r.voidReason,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
  }));
}

export async function createDraftDocumentService(p: {
  workspaceId: bigint;
  documentType: "RECEIPT" | "PAYMENT" | "INVOICE" | "JOURNAL";
  number: string;
  documentDate: string;
  amount: string | number;
  currency?: string;
  description: string;
  regimePolicyId?: bigint;
  lineItems?: any[];
}): Promise<AccountingDocumentView> {
  const newId = generateSnowflake();
  const [created] = await db
    .insert(accountingDocuments)
    .values({
      id: newId,
      workspaceId: p.workspaceId,
      documentType: p.documentType,
      number: p.number,
      documentDate: p.documentDate as any,
      amount: String(p.amount) as any,
      currency: p.currency || "VND",
      description: p.description,
      regimePolicyId: p.regimePolicyId ?? null,
      lineItems: p.lineItems ?? [],
      status: "DRAFT",
    })
    .returning();

  return {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    documentType: created.documentType as any,
    number: created.number,
    documentDate: typeof created.documentDate === "string" ? created.documentDate : new Date(created.documentDate).toISOString().split("T")[0],
    amount: String(created.amount),
    currency: created.currency,
    description: created.description,
    status: "DRAFT",
    regimePolicyId: created.regimePolicyId ? String(created.regimePolicyId) : null,
    lineItems: (created.lineItems || []) as any[],
    confirmedAt: null,
    confirmedBy: null,
    voidReason: null,
    createdAt: created.createdAt.toISOString(),
    updatedAt: created.updatedAt.toISOString(),
  };
}

export async function confirmAccountingDocumentService(p: {
  documentId: bigint;
  confirmedBy: bigint;
}): Promise<AccountingDocumentView> {
  return await db.transaction(async (tx) => {
    const [doc] = await tx
      .select()
      .from(accountingDocuments)
      .where(eq(accountingDocuments.id, p.documentId));

    if (!doc) {
      throw APIError.notFound(`Accounting document '${p.documentId}' not found`);
    }

    if (doc.status === "CONFIRMED") {
      throw APIError.failedPrecondition(`Document '${p.documentId}' is already confirmed`);
    }

    const now = new Date();
    const [updated] = await tx
      .update(accountingDocuments)
      .set({
        status: "CONFIRMED",
        confirmedAt: now,
        confirmedBy: p.confirmedBy,
        updatedAt: now,
      })
      .where(eq(accountingDocuments.id, p.documentId))
      .returning();

    const event = makeBusinessEvent({
      eventType: FINANCE_ACCOUNTING_DOCUMENT_CONFIRMED,
      workspaceId: String(updated.workspaceId),
      aggregateType: "accounting_document",
      aggregateId: String(updated.id),
      correlationId: randomUUID(),
      actor: {
        kind: "user",
        id: String(p.confirmedBy),
      },
      classification: "internal",
      payload: {
        workspaceId: String(updated.workspaceId),
        documentId: String(updated.id),
        documentType: updated.documentType,
        number: updated.number,
        amount: String(updated.amount),
        confirmedAt: now.toISOString(),
      },
    });

    await appendOutboxEvent(tx, event);

    return {
      id: String(updated.id),
      workspaceId: String(updated.workspaceId),
      documentType: updated.documentType as any,
      number: updated.number,
      documentDate: typeof updated.documentDate === "string" ? updated.documentDate : new Date(updated.documentDate).toISOString().split("T")[0],
      amount: String(updated.amount),
      currency: updated.currency,
      description: updated.description,
      status: "CONFIRMED",
      regimePolicyId: updated.regimePolicyId ? String(updated.regimePolicyId) : null,
      lineItems: (updated.lineItems || []) as any[],
      confirmedAt: now.toISOString(),
      confirmedBy: String(p.confirmedBy),
      voidReason: updated.voidReason,
      createdAt: updated.createdAt.toISOString(),
      updatedAt: updated.updatedAt.toISOString(),
    };
  });
}

export async function voidAccountingDocumentService(p: {
  documentId: bigint;
  voidReason: string;
}): Promise<AccountingDocumentView> {
  const [updated] = await db
    .update(accountingDocuments)
    .set({
      status: "VOID",
      voidReason: p.voidReason,
      updatedAt: new Date(),
    })
    .where(eq(accountingDocuments.id, p.documentId))
    .returning();

  if (!updated) {
    throw APIError.notFound(`Accounting document '${p.documentId}' not found`);
  }

  return {
    id: String(updated.id),
    workspaceId: String(updated.workspaceId),
    documentType: updated.documentType as any,
    number: updated.number,
    documentDate: typeof updated.documentDate === "string" ? updated.documentDate : new Date(updated.documentDate).toISOString().split("T")[0],
    amount: String(updated.amount),
    currency: updated.currency,
    description: updated.description,
    status: "VOID",
    regimePolicyId: updated.regimePolicyId ? String(updated.regimePolicyId) : null,
    lineItems: (updated.lineItems || []) as any[],
    confirmedAt: updated.confirmedAt ? updated.confirmedAt.toISOString() : null,
    confirmedBy: updated.confirmedBy ? String(updated.confirmedBy) : null,
    voidReason: updated.voidReason,
    createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
  };
}
