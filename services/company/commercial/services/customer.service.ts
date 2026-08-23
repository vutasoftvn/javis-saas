import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

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

function toCustomer(row: typeof customers.$inferSelect): Customer {
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

export async function createCustomerService(
  params: CreateCustomerParams,
  authorization: string | undefined
): Promise<Customer> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
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
  return toCustomer(row);
}

export async function getCustomerService(id: number, authorization: string | undefined): Promise<Customer> {
  const [row] = await db
    .select()
    .from(customers)
    .where(eq(customers.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`customer ${id} not found`);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toCustomer(row);
}
