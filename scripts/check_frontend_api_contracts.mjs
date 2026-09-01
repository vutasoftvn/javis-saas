#!/usr/bin/env node
// Task 7 — ngăn route literal frontend drift bằng contract consumer gate.
//
// Quét literal string argument đầu tiên của ApiClient.get/post/put/patch/
// delete/sendForm trong frontend/lib/**/*.dart, đối chiếu với manifest nguồn
// shared/contracts/mvp-surface.json (KHÔNG đọc các file generated — chúng là
// generator-owned, đọc ngược sẽ tự xác nhận chính output của mình). Bất kỳ
// literal nào không khớp entry enabled nào trong manifest là vi phạm
// `unknown_literal_route`; literal khớp một entry đã bị disable (vd. 8 entry
// vault.* Task 5 tắt) là vi phạm `disabled_contract` — khác nguyên nhân, khác
// hành động sửa (route sai vs. tính năng đang tắt có chủ đích).
//
// Chuỗi có nội suy (`$var`, `${...}`) bị bỏ qua — ngoài phạm vi checker này,
// phải refactor về MvpEndpoint hoặc khai báo tường minh trong allowlist nếu
// thật sự cần một escape hatch.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const METHODS = ["get", "post", "put", "patch", "delete", "sendForm"];
const CALL_REGEX = new RegExp(`ApiClient\\.(${METHODS.join("|")})\\s*\\(`, "g");

/** ApiClient.sendForm() luôn phát HTTP POST (xem api_client.dart — dùng
 * `client.post(...)` bên trong), khác tên method Dart với verb HTTP thật; các
 * method còn lại tên Dart trùng verb HTTP (chỉ khác hoa/thường). Manifest
 * dùng verb HTTP viết hoa nên phải map trước khi so khớp. */
function toHttpMethod(dartMethodName) {
  if (dartMethodName === "sendForm") return "POST";
  return dartMethodName.toUpperCase();
}

/** Loại bỏ comment `//...` và `/* ... *\/` khỏi source Dart, giữ nguyên số
 * dòng (thay ký tự bằng khoảng trắng, không xoá newline) để offset vẫn khớp
 * `content.slice(0, idx).split("\n").length` khi tính số dòng vi phạm. Không
 * parse bên trong string literal (`'...'`/`"..."`) để tránh hiểu nhầm `//`
 * bên trong URL là comment. */
export function stripComments(content) {
  let out = "";
  let i = 0;
  let inString = null; // "'" hoặc '"' khi đang ở trong string, null nếu không.
  while (i < content.length) {
    const ch = content[i];
    if (inString) {
      out += ch;
      if (ch === "\\") {
        // Giữ nguyên ký tự escape kế tiếp (vd. \' trong string) không đóng string.
        if (i + 1 < content.length) {
          out += content[i + 1];
          i += 2;
          continue;
        }
      } else if (ch === inString) {
        inString = null;
      }
      i++;
      continue;
    }
    if (ch === "'" || ch === '"') {
      inString = ch;
      out += ch;
      i++;
      continue;
    }
    if (ch === "/" && content[i + 1] === "/") {
      while (i < content.length && content[i] !== "\n") {
        out += " ";
        i++;
      }
      continue;
    }
    if (ch === "/" && content[i + 1] === "*") {
      out += "  ";
      i += 2;
      while (i < content.length && !(content[i] === "*" && content[i + 1] === "/")) {
        out += content[i] === "\n" ? "\n" : " ";
        i++;
      }
      out += "  ";
      i += 2;
      continue;
    }
    out += ch;
    i++;
  }
  return out;
}

/** Tìm tất cả lệnh gọi ApiClient.<method>('literal') trong content đã bỏ
 * comment. Trả về null cho `literal` khi argument đầu tiên không phải string
 * literal thuần (không có quote ngay sau `(` khi bỏ qua khoảng trắng/newline,
 * hoặc string có nội suy `$`) — caller phải bỏ qua các entry này. */
export function findApiClientCalls(content) {
  const calls = [];
  let match;
  CALL_REGEX.lastIndex = 0;
  while ((match = CALL_REGEX.exec(content))) {
    const method = match[1];
    let i = match.index + match[0].length;
    while (i < content.length && /\s/.test(content[i])) i++;
    const quote = content[i];
    const line = content.slice(0, match.index).split("\n").length;
    if (quote !== "'" && quote !== '"') {
      calls.push({ method, literal: null, line });
      continue;
    }
    let j = i + 1;
    let str = "";
    let dynamic = false;
    let closed = false;
    while (j < content.length) {
      const c = content[j];
      if (c === "\\") {
        str += c + (content[j + 1] ?? "");
        j += 2;
        continue;
      }
      if (c === quote) {
        closed = true;
        j++;
        break;
      }
      if (c === "$") dynamic = true;
      str += c;
      j++;
    }
    calls.push({ method, literal: closed && !dynamic ? str : null, line });
  }
  return calls;
}

/** Bỏ query string trước khi so khớp — manifest chỉ khai báo path, không khai
 * báo query param. */
export function stripQuery(literal) {
  const idx = literal.indexOf("?");
  return idx === -1 ? literal : literal.slice(0, idx);
}

/** So khớp một path cụ thể (đã bỏ query) với path template của manifest —
 * segment `:id`/`:workspaceId`/... khớp đúng một segment URL bất kỳ (non-empty,
 * không chứa `/`). Số lượng segment phải bằng nhau. */
export function pathMatchesTemplate(literalPath, templatePath) {
  const a = literalPath.split("/");
  const b = templatePath.split("/");
  if (a.length !== b.length) return false;
  for (let k = 0; k < a.length; k++) {
    if (b[k].startsWith(":")) {
      if (a[k].length === 0) return false;
      continue;
    }
    if (a[k] !== b[k]) return false;
  }
  return true;
}

export function loadManifest(manifestPath) {
  const raw = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  return (raw.capabilities ?? []).map((c) => ({
    method: c.method,
    path: c.path,
    enabled: c.enabled !== false,
  }));
}

export function loadAllowlist(allowlistPath) {
  if (!allowlistPath || !fs.existsSync(allowlistPath)) return { entries: [] };
  const raw = JSON.parse(fs.readFileSync(allowlistPath, "utf8"));
  return { entries: raw.entries ?? [] };
}

function isAllowlisted(method, literalPath, allowlist, today) {
  return allowlist.entries.some((entry) => {
    if (entry.path !== literalPath) return false;
    if (entry.method && entry.method !== method) return false;
    if (!entry.expires_on) return false;
    return entry.expires_on > today;
  });
}

/** Phân loại một literal route đã tìm thấy: 'ok' (khớp entry enabled, hoặc
 * được allowlist còn hạn), 'disabled_contract' (khớp entry bị tắt), hoặc
 * 'unknown_literal_route' (không khớp gì, cũng không trong allowlist). */
export function classify(method, literalPath, manifestEntries, allowlist, today) {
  const normalized = stripQuery(literalPath);
  const matches = manifestEntries.filter(
    (e) => e.method === method && pathMatchesTemplate(normalized, e.path),
  );
  if (matches.some((e) => e.enabled)) return "ok";
  if (matches.length > 0) return "disabled_contract";
  if (isAllowlisted(method, normalized, allowlist, today)) return "ok";
  return "unknown_literal_route";
}

const SKIP_DIR_NAMES = new Set(["test", "tests", ".git", "build", ".dart_tool"]);

function walkDartFiles(dir, callback) {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIR_NAMES.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkDartFiles(full, callback);
    } else if (entry.isFile() && full.endsWith(".dart")) {
      callback(full);
    }
  }
}

export function scanRoot(rootDir, manifestEntries, allowlist, today = new Date().toISOString().slice(0, 10)) {
  const resolvedRoot = path.resolve(rootDir);
  const libDir = path.join(resolvedRoot, "frontend", "lib");
  const violations = [];
  walkDartFiles(libDir, (filePath) => {
    const relFile = path.relative(resolvedRoot, filePath).replace(/\\/g, "/");
    const content = stripComments(fs.readFileSync(filePath, "utf8"));
    for (const call of findApiClientCalls(content)) {
      if (call.literal === null) continue; // dynamic/non-literal — ngoài phạm vi.
      const httpMethod = toHttpMethod(call.method);
      const verdict = classify(httpMethod, call.literal, manifestEntries, allowlist, today);
      if (verdict === "ok") continue;
      violations.push({
        file: relFile,
        line: call.line,
        path: call.literal,
        reason: verdict,
      });
    }
  });
  return violations;
}

// ─── CLI entrypoint ───
const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename) {
  const args = process.argv.slice(2);
  let rootDir = ".";
  let manifestPath = "shared/contracts/mvp-surface.json";
  let allowlistPath = "scripts/frontend-api-contract-allowlist.json";

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--root" && args[i + 1]) rootDir = args[++i];
    else if (args[i] === "--manifest" && args[i + 1]) manifestPath = args[++i];
    else if (args[i] === "--allowlist" && args[i + 1]) allowlistPath = args[++i];
  }

  const manifestEntries = loadManifest(manifestPath);
  const allowlist = loadAllowlist(allowlistPath);
  const violations = scanRoot(rootDir, manifestEntries, allowlist);

  if (violations.length > 0) {
    console.error("❌ Frontend API contract violations:");
    for (const v of violations) {
      console.error(`  ${v.file}:${v.line} ${v.path} [${v.reason}]`);
    }
    process.exit(1);
  }

  console.log("✅ Frontend API contract check passed: mọi literal route khớp contract enabled hoặc allowlist còn hạn.");
  process.exit(0);
}
