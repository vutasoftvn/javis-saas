import { APIError } from "encore.dev/api";
import { eq, and, or, isNull, lte, gt } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

const { engagementEscalationRoutes } = schema;

export interface SetEscalationRouteParams {
  workspaceId: string;
  routeKey: string;
  role: "primary" | "backup" | "duty_manager";
  workforceMemberId: string;
  activeUntil?: Date;
}

export interface EscalationRouteResult {
  workforceMemberId: string;
  role: string;
}

/**
 * Set or upsert an escalation route.
 * If an active route exists for the same (workspaceId, routeKey, role), closes it.
 * Then inserts the new route.
 */
export async function setEscalationRoute(
  params: SetEscalationRouteParams,
  ctx: TenantContext
): Promise<void> {
  if (String(params.workspaceId) !== String(ctx.workspaceId)) {
    throw APIError.permissionDenied("workspace mismatch");
  }

  const workspaceId = BigInt(params.workspaceId);
  const memberId = BigInt(params.workforceMemberId);
  const now = new Date();

  // Find and close existing active route for this (workspace, routeKey, role)
  const existingActive = await db
    .select()
    .from(engagementEscalationRoutes)
    .where(
      and(
        eq(engagementEscalationRoutes.workspaceId, workspaceId),
        eq(engagementEscalationRoutes.routeKey, params.routeKey),
        eq(engagementEscalationRoutes.role, params.role),
        isNull(engagementEscalationRoutes.activeUntil)
      )
    )
    .limit(1);

  if (existingActive.length > 0) {
    // Close the existing active route
    await db
      .update(engagementEscalationRoutes)
      .set({ activeUntil: now })
      .where(
        eq(engagementEscalationRoutes.id, existingActive[0].id)
      );
  }

  // Insert new route
  await db.insert(engagementEscalationRoutes).values({
    id: BigInt(generateSnowflake()),
    workspaceId,
    routeKey: params.routeKey,
    role: params.role,
    workforceMemberId: memberId,
    activeFrom: now,
    activeUntil: params.activeUntil ?? null,
    createdAt: now,
  });
}

/**
 * Resolve an escalation route by level (1=primary, 2=backup, 3+=duty_manager).
 * Returns the active workforce member for that role.
 * Throws failedPrecondition if no active route exists.
 */
export async function resolveEscalationRoute(
  routeKey: string,
  level: number,
  ctx: TenantContext
): Promise<EscalationRouteResult> {
  const role = level === 1 ? "primary" : level === 2 ? "backup" : "duty_manager";
  const now = new Date();

  const routes = await db
    .select()
    .from(engagementEscalationRoutes)
    .where(
      and(
        eq(engagementEscalationRoutes.workspaceId, BigInt(ctx.workspaceId)),
        eq(engagementEscalationRoutes.routeKey, routeKey),
        eq(engagementEscalationRoutes.role, role),
        lte(engagementEscalationRoutes.activeFrom, now),
        or(
          isNull(engagementEscalationRoutes.activeUntil),
          gt(engagementEscalationRoutes.activeUntil, now)
        )
      )
    )
    .limit(1);

  if (routes.length === 0) {
    throw APIError.failedPrecondition(
      `no active ${role} for route ${routeKey} in workspace ${ctx.workspaceId}`
    );
  }

  return {
    workforceMemberId: String(routes[0].workforceMemberId),
    role,
  };
}

/**
 * Assert that a route has an active primary binding.
 * Used by openThread to fail-closed when on_call mode requires escalation.
 * Throws failedPrecondition if no active primary route exists.
 */
export async function assertRouteBound(routeKey: string, ctx: TenantContext): Promise<void> {
  const now = new Date();

  const primaryRoutes = await db
    .select()
    .from(engagementEscalationRoutes)
    .where(
      and(
        eq(engagementEscalationRoutes.workspaceId, BigInt(ctx.workspaceId)),
        eq(engagementEscalationRoutes.routeKey, routeKey),
        eq(engagementEscalationRoutes.role, "primary"),
        lte(engagementEscalationRoutes.activeFrom, now),
        or(
          isNull(engagementEscalationRoutes.activeUntil),
          gt(engagementEscalationRoutes.activeUntil, now)
        )
      )
    )
    .limit(1);

  if (primaryRoutes.length === 0) {
    throw APIError.failedPrecondition(
      `no active primary for route ${routeKey} in workspace ${ctx.workspaceId}`
    );
  }
}
