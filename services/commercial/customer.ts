import { api, APIError } from "encore.dev/api";
import { commercialDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface CustomerRow {
  id: number;
  workspace_id: number;
  account_id: number;
  acquired_from_opportunity_id: number | null;
  lifecycle_status: string;
  activation_status: string | null;
  owner_id: number | null;
  first_purchase_at: Date | null;
  renewal_date: Date | null;
  health_status: string;
  created_at: Date;
  updated_at: Date;
}

function rowToCustomer(row: CustomerRow): Customer {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    accountId: row.account_id,
    acquiredFromOpportunityId: row.acquired_from_opportunity_id,
    lifecycleStatus: row.lifecycle_status,
    activationStatus: row.activation_status,
    ownerId: row.owner_id,
    firstPurchaseAt: row.first_purchase_at ? row.first_purchase_at.toISOString() : null,
    renewalDate: row.renewal_date ? row.renewal_date.toISOString() : null,
    healthStatus: row.health_status,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

export const createCustomer = api(
  { method: "POST", path: "/commercial/customers", expose: true },
  async (params: CreateCustomerParams): Promise<Customer> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await commercialDB.queryRow<CustomerRow>`
      INSERT INTO sales.customers (workspace_id, account_id, acquired_from_opportunity_id, owner_id)
      VALUES (${params.workspaceId}, ${params.accountId}, ${params.acquiredFromOpportunityId ?? null}, ${params.ownerId ?? null})
      RETURNING id, workspace_id, account_id, acquired_from_opportunity_id, lifecycle_status,
        activation_status, owner_id, first_purchase_at, renewal_date, health_status, created_at, updated_at
    `;
    if (!row) throw APIError.internal("failed to create customer");
    return rowToCustomer(row);
  }
);

export const getCustomer = api(
  { method: "GET", path: "/commercial/customers/:id", expose: true },
  async ({ id }: { id: number }): Promise<Customer> => {
    const row = await commercialDB.queryRow<CustomerRow>`
      SELECT id, workspace_id, account_id, acquired_from_opportunity_id, lifecycle_status,
        activation_status, owner_id, first_purchase_at, renewal_date, health_status, created_at, updated_at
      FROM sales.customers WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`customer ${id} not found`);
    return rowToCustomer(row);
  }
);
