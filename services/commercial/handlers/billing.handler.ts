import { api, APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";

const { invoices, subscriptions } = schema;

export interface Invoice {
  id: number;
  workspaceId: number;
  customerId?: number | null;
  invoiceNumber: string;
  amount: number;
  currency: string;
  status: string;
  dueDate?: string | null;
  paidAt?: string | null;
  createdAt: string;
}

export interface CreateInvoiceRequest {
  workspaceId: number;
  customerId?: number | null;
  invoiceNumber: string;
  amount: number;
  currency?: string;
  dueDate?: string | null;
}

export interface Subscription {
  id: number;
  workspaceId: number;
  customerId?: number | null;
  planName: string;
  billingCycle: string;
  price: number;
  currency: string;
  status: string;
  currentPeriodStart?: string | null;
  currentPeriodEnd?: string | null;
  createdAt: string;
}

export interface CreateSubscriptionRequest {
  workspaceId: number;
  customerId?: number | null;
  planName: string;
  billingCycle?: string;
  price: number;
  currency?: string;
}

// ─── Invoices Endpoints ───

export const createInvoice = api(
  { expose: true, method: "POST", path: "/commercial/invoices" },
  async (req: CreateInvoiceRequest): Promise<Invoice> => {
    if (!req.workspaceId || !req.invoiceNumber || req.amount === undefined) {
      throw APIError.invalidArgument("workspaceId, invoiceNumber, and amount are required");
    }

    const [row] = await db
      .insert(invoices)
      .values({
        workspaceId: BigInt(req.workspaceId),
        customerId: req.customerId ? BigInt(req.customerId) : null,
        invoiceNumber: req.invoiceNumber,
        amount: req.amount,
        currency: req.currency || "VND",
        dueDate: req.dueDate ? new Date(req.dueDate) : null,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create invoice");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      customerId: row.customerId ? Number(row.customerId) : null,
      invoiceNumber: row.invoiceNumber,
      amount: row.amount,
      currency: row.currency,
      status: row.status,
      dueDate: row.dueDate ? row.dueDate.toISOString() : null,
      paidAt: row.paidAt ? row.paidAt.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const listInvoices = api(
  { expose: true, method: "GET", path: "/commercial/workspaces/:workspaceId/invoices" },
  async (params: { workspaceId: number }): Promise<{ invoices: Invoice[] }> => {
    const rows = await db
      .select()
      .from(invoices)
      .where(eq(invoices.workspaceId, BigInt(params.workspaceId)))
      .orderBy(desc(invoices.id));

    return {
      invoices: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        customerId: row.customerId ? Number(row.customerId) : null,
        invoiceNumber: row.invoiceNumber,
        amount: row.amount,
        currency: row.currency,
        status: row.status,
        dueDate: row.dueDate ? row.dueDate.toISOString() : null,
        paidAt: row.paidAt ? row.paidAt.toISOString() : null,
        createdAt: row.createdAt.toISOString(),
      })),
    };
  }
);

// ─── Subscriptions Endpoints ───

export const createSubscription = api(
  { expose: true, method: "POST", path: "/commercial/subscriptions" },
  async (req: CreateSubscriptionRequest): Promise<Subscription> => {
    if (!req.workspaceId || !req.planName || req.price === undefined) {
      throw APIError.invalidArgument("workspaceId, planName, and price are required");
    }

    const [row] = await db
      .insert(subscriptions)
      .values({
        workspaceId: BigInt(req.workspaceId),
        customerId: req.customerId ? BigInt(req.customerId) : null,
        planName: req.planName,
        billingCycle: req.billingCycle || "monthly",
        price: req.price,
        currency: req.currency || "VND",
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create subscription");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      customerId: row.customerId ? Number(row.customerId) : null,
      planName: row.planName,
      billingCycle: row.billingCycle,
      price: row.price,
      currency: row.currency,
      status: row.status,
      currentPeriodStart: row.currentPeriodStart ? row.currentPeriodStart.toISOString() : null,
      currentPeriodEnd: row.currentPeriodEnd ? row.currentPeriodEnd.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
