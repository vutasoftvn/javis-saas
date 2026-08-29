// M2 §6 / ADR-SLUG-001 — chuẩn hoá + kiểm tra slug workspace.
// slug = lowercase ASCII DNS label, unique toàn cầu khi link platform.
// name (display, Unicode, mutable) KHÔNG phải DNS identity.

export const SLUG_MIN_LENGTH = 3;
export const SLUG_MAX_LENGTH = 63;

// ADR-SLUG-001 §4 — chốt danh sách. Thêm mục qua PR sửa ADR + hằng số này.
export const RESERVED_SLUGS: ReadonlySet<string> = new Set([
  "admin", "api", "app", "apps", "www", "mail", "smtp", "imap", "pop", "ftp", "ns1", "ns2", "dns",
  "support", "help", "status", "docs", "blog", "about", "legal", "privacy", "terms", "security",
  "static", "assets", "cdn", "img", "images", "media", "files", "download", "downloads",
  "auth", "login", "logout", "signup", "register", "account", "accounts", "billing", "pay",
  "payment", "payments",
  "dashboard", "console", "portal", "internal", "system", "root", "superuser", "test", "staging",
  "dev", "demo",
  "cosa", "platform", "control", "controlplane", "workspace", "workspaces", "runtime", "vault",
  "gateway", "relay",
]);

/**
 * Chuẩn hoá theo thứ tự cố định (ADR-SLUG-001 §3): NFKC → NFKD + bỏ dấu tổ hợp
 * (giữ chữ gốc cho tên có dấu: "Nguyễn" → "nguyen") → lowercase → trim →
 * khoảng trắng thành `-` → bỏ ký tự ngoài [a-z0-9-] → collapse `-` → trim `-`.
 * KHÔNG kiểm tra độ dài / reserved ở đây (xem validateSlug).
 */
export function normalizeSlug(input: string): string {
  return input
    .normalize("NFKC")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // combining diacritical marks
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "");
}

export type SlugValidation =
  | { ok: true; slug: string }
  | { ok: false; reason: "empty" | "too_short" | "too_long" | "reserved" };

/** Chuẩn hoá + áp mọi ràng buộc. Không chạm DB (uniqueness kiểm ở tầng reservation). */
export function validateSlug(input: string): SlugValidation {
  const slug = normalizeSlug(input);
  if (slug.length === 0) return { ok: false, reason: "empty" };
  if (slug.length < SLUG_MIN_LENGTH) return { ok: false, reason: "too_short" };
  if (slug.length > SLUG_MAX_LENGTH) return { ok: false, reason: "too_long" };
  if (RESERVED_SLUGS.has(slug)) return { ok: false, reason: "reserved" };
  return { ok: true, slug };
}

/**
 * Derive slug mặc định từ `name`. Trả về null nếu name không tạo được slug hợp lệ
 * (rỗng sau normalize / quá ngắn / reserved) — caller phải yêu cầu user nhập tay.
 */
export function deriveSlugFromName(name: string): string | null {
  const v = validateSlug(name);
  return v.ok ? v.slug : null;
}

/** Gợi ý slug thay thế khi bị trùng: `<slug>-2`, `-3`, ... (giữ trong giới hạn độ dài). */
export function suggestAlternativeSlug(slug: string, attempt: number): string {
  const suffix = `-${attempt + 1}`;
  const base = slug.slice(0, SLUG_MAX_LENGTH - suffix.length).replace(/-+$/g, "");
  return `${base}${suffix}`;
}
