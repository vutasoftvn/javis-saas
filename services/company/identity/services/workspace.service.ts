import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { resolveTenantContext, ResolveTenantContextParams } from "./tenant-context.service";

const { identityWorkspaces } = schema;

export interface Workspace {
  id: string;
  name: string;
  companyStage: string;
  createdAt: string;
}

export interface CreateWorkspaceParams {
  name: string;
}

export async function createWorkspaceRecord(params: CreateWorkspaceParams): Promise<Workspace> {
  const [row] = await db
    .insert(identityWorkspaces)
    .values({
      id: generateSnowflake(),
      name: params.name,
    })
    .returning({
      id: identityWorkspaces.id,
      name: identityWorkspaces.name,
      companyStage: identityWorkspaces.companyStage,
      createdAt: identityWorkspaces.createdAt,
    });

  if (!row) throw APIError.internal("failed to create workspace");
  return {
    id: row.id.toString(),
    name: row.name,
    companyStage: row.companyStage,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function getWorkspaceRecord(id: string | number): Promise<Workspace> {
  const [row] = await db
    .select({
      id: identityWorkspaces.id,
      name: identityWorkspaces.name,
      companyStage: identityWorkspaces.companyStage,
      createdAt: identityWorkspaces.createdAt,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workspace ${id} not found`);
  return {
    id: row.id.toString(),
    name: row.name,
    companyStage: row.companyStage,
    createdAt: row.createdAt.toISOString(),
  };
}

export interface WorkspacePlatformCompanyResponse {
  platformCompanyId: string | null;
  membershipRole: string;
}

/**
 * Resolve workspace → platform_company_id + caller's membership role.
 * Verifies caller is a member of the workspace via resolveTenantContext (membership check).
 * Returns null platformCompanyId for local-only workspaces (không kết nối platform company).
 */
export async function getWorkspacePlatformCompany(
  params: ResolveTenantContextParams
): Promise<WorkspacePlatformCompanyResponse> {
  // Verify membership + get context (throws if not a member)
  const tenantContext = await resolveTenantContext(params);

  // Lấy workspace record với platform_company_id
  const [wsRow] = await db
    .select({
      platformCompanyId: identityWorkspaces.platformCompanyId,
    })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, BigInt(params.workspaceId)))
    .limit(1);

  if (!wsRow) {
    throw APIError.notFound(`workspace ${params.workspaceId} not found`);
  }

  return {
    platformCompanyId: wsRow.platformCompanyId?.toString() || null,
    membershipRole: tenantContext.membershipRole,
  };
}
