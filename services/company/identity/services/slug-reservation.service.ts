// M2 §6 / ADR-SLUG-001 — reservation + rename slug. Uniqueness-while-active của
// core.workspace_slugs là cơ chế giữ chỗ atomic. workspace_id KHÔNG đổi khi rename.
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  validateSlug,
  suggestAlternativeSlug,
  SLUG_MAX_LENGTH,
} from "../../shared/services/slug";

const { identityWorkspaces, identityWorkspaceSlugs } = schema;

const MAX_AUTO_SUGGESTIONS = 25;

function isUniqueViolation(err: unknown): boolean {
  // Drizzle bọc lỗi pg trong transaction ⇒ phải dò cả chuỗi `.cause`.
  let cur: unknown = err;
  for (let depth = 0; depth < 5 && cur; depth++) {
    if (typeof cur === "object" && cur !== null) {
      const obj = cur as { code?: string; message?: string; cause?: unknown };
      if (obj.code === "23505") return true;
      if (typeof obj.message === "string" && obj.message.includes("duplicate key value")) {
        return true;
      }
      cur = obj.cause;
    } else {
      break;
    }
  }
  return false;
}

async function insertActiveSlug(workspaceId: bigint, slug: string): Promise<boolean> {
  try {
    await db.transaction(async (tx) => {
      await tx.insert(identityWorkspaceSlugs).values({
        id: generateSnowflake(),
        workspaceId,
        slug,
        status: "ACTIVE",
      });
      await tx
        .update(identityWorkspaces)
        .set({ slug, updatedAt: new Date() })
        .where(eq(identityWorkspaces.id, workspaceId));
    });
    return true;
  } catch (err) {
    if (isUniqueViolation(err)) return false;
    throw err;
  }
}

export interface ReserveSlugResult {
  slug: string;
}

/**
 * Giữ chỗ `requestedSlug` cho workspace. Trùng ⇒ APIError.alreadyExists kèm gợi ý.
 * Yêu cầu workspace CHƯA có slug ACTIVE (dùng renameWorkspaceSlug để đổi).
 */
export async function reserveWorkspaceSlug(p: {
  workspaceId: bigint;
  requestedSlug: string;
}): Promise<ReserveSlugResult> {
  const v = validateSlug(p.requestedSlug);
  if (!v.ok) {
    throw APIError.invalidArgument(`slug không hợp lệ: ${v.reason}`);
  }

  const [existingActive] = await db
    .select({ slug: identityWorkspaceSlugs.slug })
    .from(identityWorkspaceSlugs)
    .where(
      and(
        eq(identityWorkspaceSlugs.workspaceId, p.workspaceId),
        eq(identityWorkspaceSlugs.status, "ACTIVE")
      )
    )
    .limit(1);
  if (existingActive) {
    throw APIError.failedPrecondition(
      `workspace đã có slug '${existingActive.slug}' — dùng rename thay vì reserve`
    );
  }

  if (await insertActiveSlug(p.workspaceId, v.slug)) {
    return { slug: v.slug };
  }
  // Trùng — gợi ý slug thay thế.
  for (let attempt = 1; attempt <= 3; attempt++) {
    const alt = suggestAlternativeSlug(v.slug, attempt);
    if (validateSlug(alt).ok && (await insertActiveSlug(p.workspaceId, alt))) {
      throw APIError.alreadyExists(
        `slug '${v.slug}' đã được dùng; đã giữ chỗ '${alt}' thay thế`
      );
    }
  }
  throw APIError.alreadyExists(`slug '${v.slug}' đã được dùng và không tìm được biến thể trống`);
}

/**
 * Auto-reserve khi tạo workspace: best-effort, KHÔNG throw. Trả slug đã giữ hoặc null.
 */
export async function autoReserveSlugFromName(
  workspaceId: bigint,
  name: string
): Promise<string | null> {
  const v = validateSlug(name);
  if (!v.ok) return null;

  if (await insertActiveSlug(workspaceId, v.slug)) return v.slug;
  for (let attempt = 1; attempt <= MAX_AUTO_SUGGESTIONS; attempt++) {
    const alt = suggestAlternativeSlug(v.slug, attempt);
    if (alt.length > SLUG_MAX_LENGTH || !validateSlug(alt).ok) continue;
    if (await insertActiveSlug(workspaceId, alt)) return alt;
  }
  return null;
}

/**
 * Đổi slug: slug cũ ACTIVE → REDIRECT (redirect_to_slug = mới), slug mới ACTIVE.
 * workspace_id không đổi. Trùng slug mới ⇒ APIError.alreadyExists.
 */
export async function renameWorkspaceSlug(p: {
  workspaceId: bigint;
  newSlug: string;
}): Promise<ReserveSlugResult> {
  const v = validateSlug(p.newSlug);
  if (!v.ok) throw APIError.invalidArgument(`slug không hợp lệ: ${v.reason}`);

  try {
    await db.transaction(async (tx) => {
      const [current] = await tx
        .select()
        .from(identityWorkspaceSlugs)
        .where(
          and(
            eq(identityWorkspaceSlugs.workspaceId, p.workspaceId),
            eq(identityWorkspaceSlugs.status, "ACTIVE")
          )
        )
        .limit(1);

      if (current) {
        if (current.slug === v.slug) return; // no-op
        await tx
          .update(identityWorkspaceSlugs)
          .set({ status: "REDIRECT", redirectToSlug: v.slug, updatedAt: new Date() })
          .where(eq(identityWorkspaceSlugs.id, current.id));
      }

      await tx.insert(identityWorkspaceSlugs).values({
        id: generateSnowflake(),
        workspaceId: p.workspaceId,
        slug: v.slug,
        status: "ACTIVE",
      });
      await tx
        .update(identityWorkspaces)
        .set({ slug: v.slug, updatedAt: new Date() })
        .where(eq(identityWorkspaces.id, p.workspaceId));
    });
  } catch (err) {
    if (isUniqueViolation(err)) {
      throw APIError.alreadyExists(`slug '${v.slug}' đã được dùng bởi workspace khác`);
    }
    throw err;
  }
  return { slug: v.slug };
}
