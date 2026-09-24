import { APIError } from "encore.dev/api";
import { authorizeAndProjectCoreAccess, looksLikeJwt } from "../services/core-access.service";
import { verifyControlDelegationToken } from "../services/token.service";

export interface AuthClaims {
  sub: string;
  aud: "cosa";
  /** Role trong organization theo core. */
  role: string;
  organizationId: string;
}

export interface AuthContext {
  userID: string;
  organizationId: string;
  claims: AuthClaims;
  /** Role trong organization theo core. */
  organizationRole: string;
  membershipVersion: number;
}

/**
 * Extract and verify authentication context from HTTP headers.
 *
 * Danh tính và quyền do backend/core quyết định: access token OIDC (chuỗi opaque) được introspect, sau
 * đó core hỏi user có phải thành viên organization (id organization, lấy từ tham số đường dẫn `:organizationId`)
 * không; kết quả được chiếu vào DB COSA. Ngoại lệ nội bộ: control-plane delegation (JWT) do apps/cosa ký.
 *
 * @param authHeader - Authorization header value (e.g., "Bearer <token>")
 * @param workspaceHeader - id organization (tham số đường dẫn)
 * @returns Verified AuthContext with user ID, workspace, and token claims
 * @throws APIError.unauthenticated if token is missing or invalid
 * @throws APIError.permissionDenied if workspace header is missing or not allowed
 */
export async function extractAuthContext(
  authHeader: string | undefined,
  workspaceHeader: string | undefined
): Promise<AuthContext> {
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }

  const token = authHeader.slice("Bearer ".length);
  if (!token) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  if (!workspaceHeader) {
    throw APIError.permissionDenied("missing organization id");
  }

  // Token dạng JWT: control-plane delegation do apps/cosa ký (COSA_CONTROL_DELEGATION_SECRET) sau khi ĐÃ
  // kiểm tra thành viên workspace thật. Tin claim, không hỏi lại core (cùng quy ước với
  // resolveCallerAuthorizedForWorkspace).
  if (looksLikeJwt(token)) {
    const delegation = verifyControlDelegationToken(token);
    if (delegation.organizationId !== workspaceHeader) {
      throw APIError.permissionDenied("control-plane delegation token scoped cho workspace khác");
    }
    return {
      userID: delegation.sub,
      organizationId: workspaceHeader,
      claims: { sub: delegation.sub, aud: "cosa", role: delegation.role, organizationId: workspaceHeader },
      organizationRole: delegation.role,
      membershipVersion: 0,
    };
  }

  // Core quyết định quyền; nếu cho phép thì bản chiếu cục bộ (user, organization, role) được cập nhật.
  const access = await authorizeAndProjectCoreAccess(token, workspaceHeader, "cosa.workspace.read");

  return {
    userID: access.userId,
    organizationId: workspaceHeader,
    claims: {
      sub: access.userId,
      aud: "cosa",
      role: access.role,
      organizationId: workspaceHeader,
    },
    organizationRole: access.role,
    membershipVersion: access.membershipVersion,
  };
}

/**
 * Middleware factory: returns a handler wrapper that injects auth context.
 */
export function withAuthContext(
  handler: (context: AuthContext) => Promise<unknown>
) {
  return async (authHeader?: string, workspaceHeader?: string) => {
    const context = await extractAuthContext(authHeader, workspaceHeader);
    return handler(context);
  };
}
