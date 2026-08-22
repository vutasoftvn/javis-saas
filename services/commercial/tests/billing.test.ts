import { describe, it, expect } from "vitest";
import { createInvoice, listInvoices, createSubscription } from "../handlers/billing.handler";

describe("Billing Service", () => {
  const workspaceId = 500;

  it("creates an invoice and lists it", async () => {
    const invoice = await createInvoice({
      workspaceId,
      invoiceNumber: "INV-2026-001",
      amount: 15000000,
      currency: "VND",
      dueDate: "2026-09-30T00:00:00Z",
    });

    expect(invoice.id).toBeDefined();
    expect(invoice.workspaceId).toBe(workspaceId);
    expect(invoice.invoiceNumber).toBe("INV-2026-001");
    expect(invoice.amount).toBe(15000000);
    expect(invoice.status).toBe("draft");

    const list = await listInvoices({ workspaceId });
    expect(list.invoices.some((inv) => inv.id === invoice.id)).toBe(true);
  });

  it("creates a subscription", async () => {
    const subscription = await createSubscription({
      workspaceId,
      planName: "Enterprise AI Tier 1",
      billingCycle: "monthly",
      price: 25000000,
      currency: "VND",
    });

    expect(subscription.id).toBeDefined();
    expect(subscription.planName).toBe("Enterprise AI Tier 1");
    expect(subscription.price).toBe(25000000);
    expect(subscription.status).toBe("active");
  });
});
