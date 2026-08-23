import { describe, it, expect } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { createInvoice, listInvoices, createSubscription } from "../handlers/billing.handler";

describe("Billing Service", () => {
  it("creates an invoice and lists it", async () => {
    const user = await registerUserService({
      email: `billing-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      password: "password123",
      displayName: "Billing Test",
    });
    const authorization = `Bearer ${user.accessToken}`;
    const invoiceNumber = `INV-${Date.now()}`;

    const invoice = await createInvoice({
      workspaceId: user.workspaceId,
      invoiceNumber,
      amount: 15000000,
      currency: "VND",
      dueDate: "2026-09-30T00:00:00Z",
      authorization,
    });

    expect(invoice.id).toBeDefined();
    expect(invoice.workspaceId).toBe(user.workspaceId);
    expect(invoice.invoiceNumber).toBe(invoiceNumber);
    expect(invoice.amount).toBe(15000000);
    expect(invoice.status).toBe("draft");

    const list = await listInvoices({ workspaceId: user.workspaceId, authorization });
    expect(list.invoices.some((inv) => inv.id === invoice.id)).toBe(true);
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const owner = await registerUserService({
      email: `billing-owner-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      password: "password123",
      displayName: "Billing Owner",
    });
    const outsider = await registerUserService({
      email: `billing-outsider-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      password: "password123",
      displayName: "Billing Outsider",
    });

    await expect(
      createInvoice({
        workspaceId: owner.workspaceId,
        invoiceNumber: `INV-${Date.now()}`,
        amount: 1000,
        authorization: `Bearer ${outsider.accessToken}`,
      })
    ).rejects.toThrow();
  });

  it("creates a subscription", async () => {
    const user = await registerUserService({
      email: `billing-sub-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      password: "password123",
      displayName: "Billing Sub Test",
    });
    const authorization = `Bearer ${user.accessToken}`;

    const subscription = await createSubscription({
      workspaceId: user.workspaceId,
      planName: "Enterprise AI Tier 1",
      billingCycle: "monthly",
      price: 25000000,
      currency: "VND",
      authorization,
    });

    expect(subscription.id).toBeDefined();
    expect(subscription.planName).toBe("Enterprise AI Tier 1");
    expect(subscription.price).toBe(25000000);
    expect(subscription.status).toBe("active");
  });
});
