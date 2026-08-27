// services/company/shared/services/workspace-resolver.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../../identity/models/db";

const { identityWorkspaces } = schema;

export interface ResolveWorkspaceIdParams {
  workspaceId?: string | number;
  companyId?: string | number;
}

/**
 * Public product resolver: require explicit workspaceId, no company fallback.
 *
 * Use this for endpoints that accept a workspace-scoped request. If workspaceId
 * is missing or invalid, fail closed (invalidArgument, not found).
 */
export async function resolveProductWorkspaceId(
  workspaceId: string | number | undefined
): Promise<bigint> {
  if (workspaceId === undefined || workspaceId === null || workspaceId === "") {
    throw APIError.invalidArgument("workspaceId is required");
  }

  const wsId = BigInt(workspaceId);

  // Verify workspace exists
  const [ws] = await db
    .select({ id: identityWorkspaces.id })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.id, wsId))
    .limit(1);

  if (!ws) {
    throw APIError.notFound(`workspace ${workspaceId} not found`);
  }

  return ws.id;
}

// companyId (platform-side id) chỉ dùng để tra ra workspaceId local qua
// core.workspaces.platform_company_id — business row không lưu song song
// company_id + workspace_id (xem Plan B, nguyên tắc canonical tenant key).
//
// TODO(Task 3): strategy handlers should stop using this path; move them to
// resolveProductWorkspaceId and pass workspaceId explicitly, not companyId.
export async function resolveWorkspaceId(params: ResolveWorkspaceIdParams): Promise<bigint> {
  if (params.workspaceId !== undefined && params.workspaceId !== null && params.workspaceId !== "") {
    return BigInt(params.workspaceId);
  }

  if (params.companyId === undefined || params.companyId === null || params.companyId === "") {
    throw APIError.invalidArgument("workspaceId hoặc companyId là bắt buộc");
  }

  const [ws] = await db
    .select({ id: identityWorkspaces.id })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.platformCompanyId, String(params.companyId)))
    .limit(1);

  if (!ws) {
    throw APIError.notFound(`không tìm thấy workspace projection cho companyId ${params.companyId}`);
  }

  return ws.id;
}
