/**
 * Internal-only service: map platform company ID to local workspace ID.
 *
 * Reserved for platform identity sync/policy integration (Task 3+); NOT imported
 * or called from any public Encore handler. Public product tenancy path
 * (tenant-context.service.ts) resolves membership directly by workspace,
 * never via company ID.
 *
 * Separation: verifyPlatformToken + validatePlatformMembership stay in
 * platform.client.ts (token verification); resolveWorkspaceForPlatformCompany
 * lives here (local projection lookup) để tiện quản lý phân tách: kiểm chứng
 * token vs. kiểm chứng local workspace mapping.
 */
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { identityWorkspaces } = schema;

/**
 * Internal: Given a platform company ID (from a validated platform token),
 * resolve the local workspace ID.
 *
 * Fail-closed: if no projection exists, return null (caller must decide
 * whether to use a supplied workspaceId or reject).
 */
export async function resolveWorkspaceForPlatformCompany(
  platformCompanyId: string
): Promise<{ id: string } | null> {
  const [ws] = await db
    .select({ id: identityWorkspaces.id })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.platformCompanyId, platformCompanyId))
    .limit(1);

  return ws ? { id: ws.id.toString() } : null;
}
