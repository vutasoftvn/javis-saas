/**
 * Internal-only service: map platform company ID to local workspace ID.
 *
 * This is called ONLY from platform-token path in tenant-context.service.ts
 * and from identity sync/policy integration — NOT from public Encore handlers.
 *
 * Separation: verifyPlatformToken + validatePlatformMembership are in platform.client.ts
 * because they verify token validity. resolveWorkspaceForPlatformCompany is here
 * because it handles the local projection lookup after validation.
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
