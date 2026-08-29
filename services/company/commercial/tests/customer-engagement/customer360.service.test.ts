import { describe, expect, it } from "vitest";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getCustomer360 } from "../../services/customer-engagement/customer360.service";

async function ws(name: string) {
  const u = await createTestSession({
    email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`,
    displayName: name,
  });
  const ctx = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);
  return { ctx, workspaceId: u.workspaceId };
}

describe("customer360.service", () => {
  it("getCustomer360 returns full profile with contact, account, leads, opportunities, customer, invoices, subscriptions, recentInteractions", async () => {
    const a = await ws("c360-full");
    const workspaceId = BigInt(a.workspaceId);

    // Seed account
    const accountId = BigInt(generateSnowflake());
    await db.insert(schema.accounts).values({
      id: accountId,
      workspaceId,
      name: "Test Account",
    });

    // Seed contact linked to account
    const contactId = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values({
      id: contactId,
      workspaceId,
      accountId,
      name: "Test Contact",
      email: "test@example.com",
      doNotContact: false,
    });

    // Seed customer linked to account
    const customerId = BigInt(generateSnowflake());
    await db.insert(schema.customers).values({
      id: customerId,
      workspaceId,
      accountId,
      lifecycleStatus: "ACTIVE",
      healthStatus: "HEALTHY",
    });

    // Seed invoices
    const invoice1Id = BigInt(generateSnowflake());
    const invoice2Id = BigInt(generateSnowflake());
    await db.insert(schema.invoices).values([
      {
        id: invoice1Id,
        workspaceId,
        customerId,
        invoiceNumber: "INV-001",
        amount: 1000,
        currency: "VND",
        status: "paid",
      },
      {
        id: invoice2Id,
        workspaceId,
        customerId,
        invoiceNumber: "INV-002",
        amount: 2000,
        currency: "VND",
        status: "draft",
      },
    ]);

    // Seed subscription
    const subscriptionId = BigInt(generateSnowflake());
    await db.insert(schema.subscriptions).values({
      id: subscriptionId,
      workspaceId,
      customerId,
      planName: "Premium",
      billingCycle: "monthly",
      price: 500,
      currency: "VND",
      status: "active",
    });

    // Call getCustomer360
    const result = (await getCustomer360(String(contactId), a.ctx)) as any;

    expect(result.contact).toBeDefined();
    expect(result.contact.id).toBe(String(contactId));
    expect(result.account).toBeDefined();
    expect(result.account?.id).toBe(String(accountId));
    expect(result.invoices).toHaveLength(2);
    expect(result.subscriptions).toHaveLength(1);
    expect(result.customer).toBeDefined();
    expect(result.customer?.id).toBe(String(customerId));
  });

  it("getCustomer360 from another workspace throws notFound without leaking data", async () => {
    const a = await ws("c360-ws-a");
    const b = await ws("c360-ws-b");
    const workspaceId = BigInt(a.workspaceId);

    // Seed in workspace A
    const accountId = BigInt(generateSnowflake());
    await db.insert(schema.accounts).values({
      id: accountId,
      workspaceId,
      name: "Account in A",
    });

    const contactId = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values({
      id: contactId,
      workspaceId,
      accountId,
      name: "Contact in A",
      doNotContact: false,
    });

    // Try to access from workspace B
    await expect(getCustomer360(String(contactId), b.ctx)).rejects.toThrow(/not found/i);
  });

  it("getCustomer360 with identityVerified=false hides customer, invoices, subscriptions", async () => {
    const a = await ws("c360-unverified");
    const workspaceId = BigInt(a.workspaceId);

    // Seed account
    const accountId = BigInt(generateSnowflake());
    await db.insert(schema.accounts).values({
      id: accountId,
      workspaceId,
      name: "Test Account",
    });

    // Seed contact
    const contactId = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values({
      id: contactId,
      workspaceId,
      accountId,
      name: "Test Contact",
      doNotContact: false,
    });

    // Seed customer, invoices, subscriptions
    const customerId = BigInt(generateSnowflake());
    await db.insert(schema.customers).values({
      id: customerId,
      workspaceId,
      accountId,
      lifecycleStatus: "ACTIVE",
      healthStatus: "HEALTHY",
    });

    await db.insert(schema.invoices).values({
      id: BigInt(generateSnowflake()),
      workspaceId,
      customerId,
      invoiceNumber: "INV-001",
      amount: 1000,
      currency: "VND",
    });

    // Call with identityVerified: false
    const result = await getCustomer360(String(contactId), a.ctx, { identityVerified: false });

    // Should have contact and account
    expect(result.contact).toBeDefined();
    expect(result.account).toBeDefined();
    expect(result.leads).toBeDefined();
    expect(result.opportunities).toBeDefined();

    // Should NOT have customer, invoices, subscriptions keys
    expect(result).not.toHaveProperty("customer");
    expect(result).not.toHaveProperty("invoices");
    expect(result).not.toHaveProperty("subscriptions");
    expect(result).not.toHaveProperty("recentInteractions");
  });

  it("getCustomer360 without customer still returns empty arrays for invoices/subscriptions", async () => {
    const a = await ws("c360-no-customer");
    const workspaceId = BigInt(a.workspaceId);

    // Seed account
    const accountId = BigInt(generateSnowflake());
    await db.insert(schema.accounts).values({
      id: accountId,
      workspaceId,
      name: "Test Account",
    });

    // Seed contact without a customer
    const contactId = BigInt(generateSnowflake());
    await db.insert(schema.contacts).values({
      id: contactId,
      workspaceId,
      accountId,
      name: "Test Contact",
      doNotContact: false,
    });

    const result = (await getCustomer360(String(contactId), a.ctx)) as any;

    expect(result.contact).toBeDefined();
    expect(result.customer).toBeNull();
    expect(result.invoices).toEqual([]);
    expect(result.subscriptions).toEqual([]);
  });

  it("getCustomer360 missing contact throws notFound", async () => {
    const a = await ws("c360-missing");
    await expect(getCustomer360("999999999", a.ctx)).rejects.toThrow(/not found/i);
  });
});
