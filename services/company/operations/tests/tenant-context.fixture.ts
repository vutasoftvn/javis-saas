import type { TenantContext } from "../../shared/types/tenant_context";

type TenantIdentity = Pick<TenantContext, "workspaceId" | "userId">;
type TenantOverrides = Partial<Omit<TenantContext, "workspaceId" | "userId">>;

export function makeTenantContext(
  identity: TenantIdentity,
  overrides: TenantOverrides = {},
): TenantContext {
  return {
    workspaceId: identity.workspaceId,
    userId: identity.userId,
    membershipRole: "member",
    permissions: [],
    correlationId: "test-correlation-id",
    ...overrides,
  };
}
