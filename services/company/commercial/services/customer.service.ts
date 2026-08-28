import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { customers } = schema;

export interface Customer {
  id: string;
  workspaceId: string;
  accountId: string;
  acquiredFromOpportunityId: string | null;
  lifecycleStatus: string;
  activationStatus: string | null;
  ownerMemberId: string | null;
  firstPurchaseAt: string | null;
  renewalDate: string | null;
  healthStatus: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateCustomerParams {
  workspaceId: string;
  accountId: string;
  acquiredFromOpportunityId?: string;
  ownerMemberId?: string;
}

function toCustomer(row: typeof customers.$inferSelect): Customer {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    accountId: String(row.accountId),
    acquiredFromOpportunityId: row.acquiredFromOpportunityId ? String(row.acquiredFromOpportunityId) : null,
    lifecycleStatus: row.lifecycleStatus,
    activationStatus: row.activationStatus,
    ownerMemberId: row.ownerMemberId ? String(row.ownerMemberId) : null,
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
  await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(customers)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(String(params.workspaceId)),
      accountId: BigInt(String(params.accountId)),
      acquiredFromOpportunityId: params.acquiredFromOpportunityId ? BigInt(String(params.acquiredFromOpportunityId)) : null,
      ownerMemberId: params.ownerMemberId ? BigInt(String(params.ownerMemberId)) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create customer");
  return toCustomer(row);
}

export async function getCustomerService(id: string, ctx: TenantContext): Promise<Customer> {
  const [row] = await db
    .select()
    .from(customers)
    .where(and(eq(customers.id, BigInt(id)), eq(customers.workspaceId, BigInt(ctx.workspaceId))))
    .limit(1);

  if (!row) throw APIError.notFound(`customer ${id} not found`);
  return toCustomer(row);
}

