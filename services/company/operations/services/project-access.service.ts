import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";

const { projects } = schema;

/**
 * Lấy project theo ID, chỉ nếu nó thuộc workspace của caller.
 * Throw APIError.notFound nếu project không tồn tại hoặc không phải
 * của workspace này (fail-closed, không disclosure về ownership).
 */
export async function getProjectInWorkspace(id: string | number, ctx: TenantContext): Promise<typeof projects.$inferSelect> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, BigInt(id)), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!row) throw APIError.notFound("Project not found");
  return row;
}

