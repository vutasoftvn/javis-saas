export interface TenantContext {
  readonly workspaceId: string;
  readonly userId: string;
  readonly workforceMemberId?: string;
  readonly membershipRole: string;
  readonly permissions: readonly string[];
  readonly correlationId: string;
  // B5 fix — platform_user_id thật (identityUserProjections.platformUserId)
  // của local user này, nếu đã từng sync qua `sync-from-platform`. apps/cosa
  // dùng field này để mint control-plane delegation (services/cosa) khi
  // identity gốc là local_session — local user id KHÔNG cùng ID space với
  // platform user id (xem apps/cosa/auth/jwt.py::mint_control_plane_delegation).
  // `null`/`undefined` nếu user local này chưa từng sync từ platform.
  readonly platformUserId?: string | null;
}
