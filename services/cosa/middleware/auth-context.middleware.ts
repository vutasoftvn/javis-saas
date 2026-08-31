import { APIError } from "encore.dev/api";
import { verifyPlatformToken, PlatformJwtPayload } from "../services/token.service";

export interface AuthContext {
  userID: string;
  workspaceId: string;
  claims: PlatformJwtPayload & Record<string, unknown>;
}

/**
 * Extract and verify authentication context from HTTP headers.
 *
 * Called by handlers to avoid copy-pasting auth extraction across handlers.
 *
 * @param authHeader - Authorization header value (e.g., "Bearer <token>")
 * @param workspaceHeader - X-Workspace-Id header value
 * @returns Verified AuthContext with user ID, workspace, and token claims
 * @throws APIError.unauthenticated if token is missing or invalid
 * @throws APIError.permissionDenied if workspace header is missing or not allowed
 */
export function extractAuthContext(
  authHeader: string | undefined,
  workspaceHeader: string | undefined
): AuthContext {
  // 1. Validate Authorization header
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }

  const token = authHeader.slice("Bearer ".length);

  // 2. Verify and decode token
  let decoded: PlatformJwtPayload & Record<string, unknown>;
  try {
    decoded = verifyPlatformToken(token) as PlatformJwtPayload & Record<string, unknown>;
  } catch {
    throw APIError.unauthenticated("invalid or expired platform token");
  }

  const userID = decoded.sub;
  if (!userID) {
    throw APIError.unauthenticated("token missing user ID claim");
  }

  // 3. Validate workspace header
  if (!workspaceHeader) {
    throw APIError.permissionDenied("missing X-Workspace-Id header");
  }

  // 4. Verify workspace match if token explicitly specifies workspaceId
  if (decoded.workspaceId && decoded.workspaceId !== workspaceHeader) {
    throw APIError.permissionDenied(
      `user does not have access to workspace ${workspaceHeader}`
    );
  }

  const workspaceIds = (decoded.workspace_ids as string[] | undefined) || [];
  if (workspaceIds.length > 0 && !workspaceIds.includes(workspaceHeader)) {
    throw APIError.permissionDenied(
      `user does not have access to workspace ${workspaceHeader}`
    );
  }

  return {
    userID,
    workspaceId: workspaceHeader,
    claims: decoded,
  };
}

/**
 * Middleware factory: returns a handler wrapper that injects auth context.
 */
export function withAuthContext(
  handler: (context: AuthContext) => Promise<unknown>
) {
  return async (authHeader?: string, workspaceHeader?: string) => {
    const context = extractAuthContext(authHeader, workspaceHeader);
    return handler(context);
  };
}
