import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { resolveTenantContext, ResolveTenantContextParams } from "./tenant-context.service";
import { autoReserveSlugFromName } from "./slug-reservation.service";

const { identityWorkspaces } = schema;

// M4 §5 — KHÔNG gộp legal status nhiều entity thành "trạng thái workspace cao nhất".
// Workspace chỉ giữ `primaryLegalEntityId`; danh sách legal entity + status lấy qua
// finance-legal `listLegalEntityProfiles`.

export interface Workspace {
  id: string;
  name: string;
  slug: string | null;
  status: string;
  runtimeMode: string;
  syncPolicy: string;
  syncStatus: string;
  stageVersion: number;
  primaryLegalEntityId: string | null;
  lifecycleStage: string;
  stageEnteredAt: string | null;
  platformWorkspaceId: string | null;
  archivedAt: string | null;
  createdAt: string;
}

export interface CreateWorkspaceParams {
  name: string;
}

// Cột canonical trả về cho mọi workspace view (M2 §1).
const WORKSPACE_VIEW_COLUMNS = {
  id: identityWorkspaces.id,
  name: identityWorkspaces.name,
  slug: identityWorkspaces.slug,
  status: identityWorkspaces.status,
  runtimeMode: identityWorkspaces.runtimeMode,
  syncPolicy: identityWorkspaces.syncPolicy,
  syncStatus: identityWorkspaces.syncStatus,
  stageVersion: identityWorkspaces.stageVersion,
  primaryLegalEntityId: identityWorkspaces.primaryLegalEntityId,
  lifecycleStage: identityWorkspaces.lifecycleStage,
  stageEnteredAt: identityWorkspaces.stageEnteredAt,
  platformWorkspaceId: identityWorkspaces.platformWorkspaceId,
  archivedAt: identityWorkspaces.archivedAt,
  createdAt: identityWorkspaces.createdAt,
} as const;

type WorkspaceRow = Pick<
  typeof identityWorkspaces.$inferSelect,
  keyof typeof WORKSPACE_VIEW_COLUMNS
>;

function mapWorkspaceRow(row: WorkspaceRow): Workspace {
  return {
    id: row.id.toString(),
    name: row.name,
    slug: row.slug ?? null,
    status: row.status,
    runtimeMode: row.runtimeMode,
    syncPolicy: row.syncPolicy,
    syncStatus: row.syncStatus,
    stageVersion: row.stageVersion,
    primaryLegalEntityId: row.primaryLegalEntityId ? row.primaryLegalEntityId.toString() : null,
    lifecycleStage: row.lifecycleStage,
    stageEnteredAt: row.stageEnteredAt ? row.stageEnteredAt.toISOString() : null,
    platformWorkspaceId: row.platformWorkspaceId ?? null,
    archivedAt: row.archivedAt ? row.archivedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createWorkspaceRecord(params: CreateWorkspaceParams): Promise<Workspace> {
  const [row] = await db
    .insert(identityWorkspaces)
    .values({
      id: generateSnowflake(),
      name: params.name,
    })
    .returning(WORKSPACE_VIEW_COLUMNS);

  if (!row) throw APIError.internal("failed to create workspace");

  // M2 §6 — auto-derive + giữ chỗ slug từ name (best-effort, không chặn tạo workspace).
  const slug = await autoReserveSlugFromName(row.id, params.name);
  return mapWorkspaceRow({ ...row, slug });
}

export async function getWorkspaceRecord(id: string | number): Promise<Workspace> {
  const [row] = await db
    .select(WORKSPACE_VIEW_COLUMNS)
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workspace ${id} not found`);
  return mapWorkspaceRow(row);
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
