import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { customers } = schema;

export interface Customer {
  id: number;
  workspaceId: number;
  accountId: number;
  acquiredFromOpportunityId: number | null;
  lifecycleStatus: string;
  activationStatus: string | null;
  ownerId: number | null;
  firstPurchaseAt: string | null;
  renewalDate: string | null;
  healthStatus: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateCustomerParams {
  workspaceId: number;
  accountId: number;
  acquiredFromOpportunityId?: number;
  ownerId?: number;
}

export const createCustomer = api(
  { method: "POST", path: "/commercial/customers", expose: true },
  async (params: CreateCustomerParams): Promise<Customer> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(customers)
      .values({
        workspaceId: BigInt(params.workspaceId),
        accountId: BigInt(params.accountId),
        acquiredFromOpportunityId: params.acquiredFromOpportunityId ? BigInt(params.acquiredFromOpportunityId) : null,
        ownerId: params.ownerId ? BigInt(params.ownerId) : null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create customer");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      accountId: Number(row.accountId),
      acquiredFromOpportunityId: row.acquiredFromOpportunityId ? Number(row.acquiredFromOpportunityId) : null,
      lifecycleStatus: row.lifecycleStatus,
      activationStatus: row.activationStatus,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      firstPurchaseAt: row.firstPurchaseAt ? row.firstPurchaseAt.toISOString() : null,
      renewalDate: row.renewalDate ? String(row.renewalDate) : null,
      healthStatus: row.healthStatus,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getCustomer = api(
  { method: "GET", path: "/commercial/customers/:id", expose: true },
  async ({ id }: { id: number }): Promise<Customer> => {
    const [row] = await db
      .select()
      .from(customers)
      .where(eq(customers.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`customer ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      accountId: Number(row.accountId),
      acquiredFromOpportunityId: row.acquiredFromOpportunityId ? Number(row.acquiredFromOpportunityId) : null,
      lifecycleStatus: row.lifecycleStatus,
      activationStatus: row.activationStatus,
      ownerId: row.ownerId ? Number(row.ownerId) : null,
      firstPurchaseAt: row.firstPurchaseAt ? row.firstPurchaseAt.toISOString() : null,
      renewalDate: row.renewalDate ? String(row.renewalDate) : null,
      healthStatus: row.healthStatus,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);
