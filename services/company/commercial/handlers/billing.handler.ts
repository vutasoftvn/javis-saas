import { api, Header } from "encore.dev/api";
import {
  Invoice,
  CreateInvoiceRequest as BaseCreateInvoiceRequest,
  Subscription,
  CreateSubscriptionRequest as BaseCreateSubscriptionRequest,
  createInvoiceService,
  listInvoicesService,
  createSubscriptionService,
} from "../services/billing.service";

export { Invoice, Subscription };

export interface CreateInvoiceRequest extends BaseCreateInvoiceRequest {
  authorization?: Header<"Authorization">;
}
export interface CreateSubscriptionRequest extends BaseCreateSubscriptionRequest {
  authorization?: Header<"Authorization">;
}

// ─── Invoices Endpoints ───

export const createInvoice = api(
  { expose: true, method: "POST", path: "/commercial/invoices" },
  async (req: CreateInvoiceRequest): Promise<Invoice> => {
    return createInvoiceService(req, req.authorization);
  }
);

export const listInvoices = api(
  { expose: true, method: "GET", path: "/commercial/workspaces/:workspaceId/invoices" },
  async (params: { workspaceId: string; authorization?: Header<"Authorization"> }): Promise<{ invoices: Invoice[] }> => {
    const invoices = await listInvoicesService(params.workspaceId, params.authorization);
    return { invoices };
  }
);

// ─── Subscriptions Endpoints ───

export const createSubscription = api(
  { expose: true, method: "POST", path: "/commercial/subscriptions" },
  async (req: CreateSubscriptionRequest): Promise<Subscription> => {
    return createSubscriptionService(req, req.authorization);
  }
);
