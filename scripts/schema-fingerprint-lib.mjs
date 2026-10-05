/**
 * Pure helpers for schema-fingerprint.mjs (kept import-safe for unit tests).
 */

/** True when the whole string is enclosed by a single matching paren pair. */
function isFullyWrapped(s) {
  if (s.length < 2 || s[0] !== "(" || s[s.length - 1] !== ")") return false;
  let depth = 0;
  let inQuote = false;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (inQuote) {
      if (ch === "'") inQuote = false; // '' escape re-enters quote on next char
      continue;
    }
    if (ch === "'") {
      inQuote = true;
    } else if (ch === "(") {
      depth++;
    } else if (ch === ")") {
      depth--;
      if (depth === 0 && i < s.length - 1) return false;
      if (depth < 0) return false;
    }
  }
  return depth === 0 && !inQuote;
}

/**
 * Normalize a CHECK clause so PostgreSQL <=17 and 18 agree: collapse
 * whitespace, strip all redundant outermost parens, wrap in exactly one pair.
 */
export function normalizeCheckClause(clause) {
  if (clause === null || clause === undefined) return null;
  let s = String(clause).trim().replace(/\s+/g, " ");
  if (!s) return null;
  while (isFullyWrapped(s)) s = s.slice(1, -1).trim();
  return `(${s})`;
}
