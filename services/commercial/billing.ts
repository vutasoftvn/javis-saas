import { api, APIError } from "encore.dev/api";
import { SQLDatabase } from "encore.dev/storage/sqldb";

const db = SQLDatabase.named("commercial");

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

    const row = await db.queryRow<Invoice>`
      INSERT INTO commercial.invoices (
        workspace_id, customer_id, invoice_number, amount, currency, due_date
      ) VALUES (
        ${req.workspaceId}, ${req.customerId ?? null}, ${req.invoiceNumber},
        ${req.amount}, ${req.currency ?? "VND"}, ${req.dueDate ?? null}
      )
      RETURNING
        id, workspace_id as "workspaceId", customer_id as "customerId",
        invoice_number as "invoiceNumber", amount, currency, status,
        due_date as "dueDate", paid_at as "paidAt", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create invoice");
    return row;
  }
);

export const listInvoices = api(
  { expose: true, method: "GET", path: "/commercial/workspaces/:workspaceId/invoices" },
  async (params: { workspaceId: number }): Promise<{ invoices: Invoice[] }> => {
    const rows = db.query<Invoice>`
      SELECT
        id, workspace_id as "workspaceId", customer_id as "customerId",
        invoice_number as "invoiceNumber", amount, currency, status,
        due_date as "dueDate", paid_at as "paidAt", created_at as "createdAt"
      FROM commercial.invoices
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY id DESC
    `;
    const invoices: Invoice[] = [];
    for await (const row of rows) invoices.push(row);
    return { invoices };
  }
);

// ─── Subscriptions Endpoints ───

export const createSubscription = api(
  { expose: true, method: "POST", path: "/commercial/subscriptions" },
  async (req: CreateSubscriptionRequest): Promise<Subscription> => {
    if (!req.workspaceId || !req.planName || req.price === undefined) {
      throw APIError.invalidArgument("workspaceId, planName, and price are required");
    }

    const row = await db.queryRow<Subscription>`
      INSERT INTO commercial.subscriptions (
        workspace_id, customer_id, plan_name, billing_cycle, price, currency
      ) VALUES (
        ${req.workspaceId}, ${req.customerId ?? null}, ${req.planName},
        ${req.billingCycle ?? "monthly"}, ${req.price}, ${req.currency ?? "VND"}
      )
      RETURNING
        id, workspace_id as "workspaceId", customer_id as "customerId",
        plan_name as "planName", billing_cycle as "billingCycle", price, currency,
        status, current_period_start as "currentPeriodStart",
        current_period_end as "currentPeriodEnd", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create subscription");
    return row;
  }
);
