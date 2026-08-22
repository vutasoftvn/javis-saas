export interface TenantContext {
  readonly companyId: string;
  readonly workspaceId: string;
  readonly userId: string;
  readonly workforceMemberId?: string;
  readonly membershipRole: string;
  readonly permissions: readonly string[];
  readonly correlationId: string;
}
