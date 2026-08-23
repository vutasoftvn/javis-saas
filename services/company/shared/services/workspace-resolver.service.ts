// services/company/shared/services/workspace-resolver.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../../identity/models/db";

const { identityWorkspaces } = schema;

export interface ResolveWorkspaceIdParams {
  workspaceId?: string | number;
  companyId?: string | number;
}

// companyId (platform-side id) chỉ dùng để tra ra workspaceId local qua
// core.workspaces.platform_company_id — business row không lưu song song
// company_id + workspace_id (xem Plan B, nguyên tắc canonical tenant key).
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
