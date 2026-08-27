// services/company/shared/services/workspace-resolver.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../../identity/models/db";

const { identityWorkspaces } = schema;

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
