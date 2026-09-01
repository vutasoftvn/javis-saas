#!/usr/bin/env node
// Task 7 — ngăn route literal frontend drift bằng contract consumer gate.
//
// Quét argument đầu tiên của ApiClient.get/post/put/patch/delete/sendForm
// trong frontend/lib/**/*.dart, đối chiếu với manifest nguồn
// shared/contracts/mvp-surface.json (KHÔNG đọc các file generated — chúng là
// generator-owned, đọc ngược sẽ tự xác nhận chính output của mình).
//
// Fix-round 1 (review "Needs fixes"): ban đầu bất kỳ chuỗi nào chứa `$` (nội
// suy) — kể cả nội suy nằm trong QUERY STRING, vd. `?workspace_id=$id` — bị
// coi là "dynamic" và bỏ qua HOÀN TOÀN, khiến checker chỉ thấy 64/494 lệnh gọi
// thật (13%). Brief Step 2 yêu cầu: (1) bỏ query string TRƯỚC khi quyết định
// có phải dynamic hay không — một path như `/vault/documents?workspace_id=$id`
// sau khi bỏ query là literal thuần, hoàn toàn kiểm tra được; (2) nội suy nằm
// trong PATH (vd. `/vault/documents/$id`) phải được quy về template
// (`/vault/documents/:id`) rồi so khớp với path template của manifest, giống
// hệt cách `:id`/`:workspaceId` của manifest được so khớp; (3) template không
// khớp entry enabled nào — kể cả khi nó tới từ một call site dynamic — vẫn là
// vi phạm `unknown_literal_route`/`disabled_contract` như bình thường, phải
// xuất hiện trong allowlist (theo đúng dạng template) nếu muốn được miễn.
//
// Literal nào không khớp entry enabled nào trong manifest là vi phạm
// `unknown_literal_route`; literal khớp một entry đã bị disable (vd. 8 entry
// vault.* Task 5 tắt) là vi phạm `disabled_contract` — khác nguyên nhân, khác
// hành động sửa (route sai vs. tính năng đang tắt có chủ đích).
//
// Fix-round 2 (review "Needs fixes"): allowlist entry template "toàn
// wildcard" (vd. `:path`, không segment literal nào) so khớp THUẦN CẤU TRÚC
// qua `pathMatchesTemplate`, nên vô tình miễn trừ MỌI lệnh gọi
// `ApiClient.<method>('$bienBatKy')` fully-dynamic một-segment ở BẤT KỲ file
// nào, không chỉ file dự định (`workspace_service.dart`). Fix: allowlist
// entry có thể mang thêm field `file` (path tương đối, đúng định dạng report
// vi phạm) để giới hạn phạm vi miễn trừ; entry có template toàn wildcard BẮT
// BUỘC phải có `file`, thiếu thì bị bỏ qua hoàn toàn (fail-closed) — xem
// `isFullyWildcardTemplate`/`isAllowlisted`.
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

/** Tìm tất cả lệnh gọi ApiClient.<method>(<arg>) trong content đã bỏ comment.
 * Trả về `raw` = toàn bộ nội dung string argument (đã giải escape `\\X`
 * thành chính ký tự bị escape kế tiếp, GIỮ NGUYÊN — không unescape — để bước
 * sau tự quyết định `\$` là dollar literal hay `$` trần là nội suy) khi
 * argument đầu tiên là string literal (`'...'`/`"..."`, dù bên trong có nội
 * suy hay không). Trả về `raw: null` khi argument đầu tiên không phải string
 * literal (vd. biến, gọi hàm khác) — trường hợp này ngoài phạm vi checker. */
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
      calls.push({ method, raw: null, line });
      continue;
    }
    let j = i + 1;
    let str = "";
    let closed = false;
    while (j < content.length) {
      const c = content[j];
      if (c === "\\") {
        // Giữ nguyên cặp escape (vd. `\$`, `\'`) — quyết định ý nghĩa của nó
        // (dollar literal hay không) thuộc về bước build-template phía sau,
        // không phải bước tách token này.
        str += c + (content[j + 1] ?? "");
        j += 2;
        continue;
      }
      if (c === quote) {
        closed = true;
        j++;
        break;
      }
      str += c;
      j++;
    }
    // Chuỗi đóng quote xong phải được theo sau ngay (bỏ qua khoảng trắng) bởi
    // `)` hoặc `,` — tức đúng là TOÀN BỘ argument, không phải một vế của biểu
    // thức nối chuỗi (`'/foo/' + id`). Nếu không, đây là expression phức tạp
    // hơn một string literal thuần — ngoài phạm vi checker (raw: null), tránh
    // hiểu nhầm thành literal cụt bị cắt mất phần còn lại.
    if (closed) {
      let k = j;
      while (k < content.length && /\s/.test(content[k])) k++;
      if (content[k] !== ")" && content[k] !== ",") closed = false;
    }
    calls.push({ method, raw: closed ? str : null, line });
  }
  return calls;
}

/** Regex khớp một cụm nội suy Dart trần (không phải `\$` đã escape) —
 * `(?<!\\)\$` — theo sau là `{...}` (nội suy biểu thức) hoặc một identifier
 * đơn giản (`$id`, `$workspaceId`). Dùng để (a) phát hiện segment có nội suy,
 * (b) rút tên tham số để đặt tên template cho dễ đọc trong report/allowlist. */
const INTERPOLATION_RE = /(?<!\\)\$(?:\{([^}]*)\}|([A-Za-z_][A-Za-z0-9_]*))/;

function hasUnescapedInterpolation(segment) {
  return INTERPOLATION_RE.test(segment);
}

/** Đặt tên tham số cho một segment có nội suy, ưu tiên identifier đơn giản
 * (`$workspaceId` → `workspaceId`) hoặc token đầu tiên trong biểu thức
 * (`${a.b}` → `a`); fallback `param` khi không rút được gì hữu ích. */
function paramNameFor(segment) {
  const m = segment.match(INTERPOLATION_RE);
  if (!m) return "param";
  const inner = m[1] ?? m[2] ?? "";
  const ident = inner.match(/[A-Za-z_][A-Za-z0-9_]*/);
  return ident ? ident[0] : "param";
}

/** Từ raw string argument (chưa unescape), tách QUERY STRING trước (brief:
 * "query string bị bỏ trước match") rồi mới xét từng path segment có nội suy
 * hay không. Segment có nội suy trần → thay bằng placeholder `:<paramName>`
 * (quy về path template, giống hệt cú pháp `:id` của manifest). Trả về
 * `{ template, isDynamic }` — `template` luôn là một chuỗi path đã unescape
 * (`\$` → `$`) sẵn sàng so khớp bằng `pathMatchesTemplate`. */
export function buildPathTemplate(raw) {
  // Bỏ mọi thứ từ dấu `?` TRẦN đầu tiên trở đi — kể cả khi query chứa nội
  // suy (`?workspace_id=$id`) — vì manifest không khai báo query param, và
  // brief yêu cầu bỏ query TRƯỚC khi quyết định dynamic hay không.
  let queryIdx = -1;
  for (let k = 0; k < raw.length; k++) {
    if (raw[k] === "\\") {
      k++;
      continue;
    }
    if (raw[k] === "?") {
      queryIdx = k;
      break;
    }
  }
  const pathOnly = queryIdx === -1 ? raw : raw.slice(0, queryIdx);

  const segments = pathOnly.split("/");
  let isDynamic = false;
  const templateSegments = segments.map((seg) => {
    if (hasUnescapedInterpolation(seg)) {
      isDynamic = true;
      return `:${paramNameFor(seg)}`;
    }
    // Không có nội suy trong segment này — unescape `\$` (dollar literal Dart)
    // và các cặp escape khác về ký tự gốc để so khớp đúng chuỗi thật.
    return seg.replace(/\\(.)/g, "$1");
  });
  return { template: templateSegments.join("/"), isDynamic };
}

/** So khớp hai path đã tách segment — cho phép wildcard ở CẢ HAI phía: một
 * segment bắt đầu bằng `:` (từ manifest, từ allowlist, hoặc từ một call site
 * dynamic đã quy về template) khớp bất kỳ segment non-empty nào ở phía kia,
 * kể cả khi phía kia cũng là `:something` hoặc là literal cụ thể. Số lượng
 * segment phải bằng nhau. */
export function pathMatchesTemplate(pathA, pathB) {
  const a = pathA.split("/");
  const b = pathB.split("/");
  if (a.length !== b.length) return false;
  for (let k = 0; k < a.length; k++) {
    const aWild = a[k].startsWith(":");
    const bWild = b[k].startsWith(":");
    if (aWild || bWild) {
      if (a[k].length === 0 || b[k].length === 0) return false;
      continue;
    }
    if (a[k] !== b[k]) return false;
  }
  return true;
}

/** Bỏ query string trước khi so khớp một path ĐÃ CHẮC CHẮN không có nội suy
 * (dùng cho test/tiện ích bên ngoài — pipeline chính dùng `buildPathTemplate`
 * để xử lý đồng thời query-strip lẫn dynamic-segment). */
export function stripQuery(literal) {
  const idx = literal.indexOf("?");
  return idx === -1 ? literal : literal.slice(0, idx);
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

/** Một template "toàn wildcard" (mọi segment đều bắt đầu bằng `:`, vd.
 * `:path` — không segment literal nào neo path lại) không mang thông tin gì
 * để phân biệt call site này với BẤT KỲ call site fully-dynamic single-segment
 * nào khác trong toàn bộ codebase. Review round 2 phát hiện: allowlist entry
 * dạng này (thêm ở round 1 cho `WorkspaceService.getJson/postJson/putJson`)
 * vô tình miễn trừ MỌI lệnh gọi `ApiClient.<method>('$bienBatKy')` ở bất kỳ
 * file nào khác, vì `pathMatchesTemplate` chỉ so khớp cấu trúc (số segment +
 * wildcard-hay-không), không biết gì về danh tính call site thật. */
function isFullyWildcardTemplate(templatePath) {
  const segs = templatePath.split("/");
  return segs.every((s) => s.startsWith(":"));
}

/** Allowlist so khớp bằng cùng `pathMatchesTemplate` (không phải so bằng
 * chuỗi tuyệt đối) — một entry allowlist dạng template (vd.
 * `/vault/documents/:id`) sẽ miễn được đúng nhóm call site dynamic tương ứng,
 * đúng yêu cầu brief "dynamic endpoint ... explicitly listed trong
 * allowlist" (theo dạng template, không phải theo từng giá trị runtime cụ
 * thể không thể biết trước). Entry literal thuần (không `:`) vẫn hoạt động
 * như cũ vì `pathMatchesTemplate` coi non-`:` segment phải khớp tuyệt đối.
 *
 * Fix round 2: một entry có `file` sẽ CHỈ miễn vi phạm phát sinh từ đúng file
 * đó (so khớp path tương đối, đúng định dạng `relFile` trong `scanRoot`) —
 * đóng lỗ hổng generic-wildcard-đi-đâu-cũng-lọt. Entry có template toàn
 * wildcard (`isFullyWildcardTemplate`) BẮT BUỘC phải có `file`; nếu thiếu,
 * entry đó bị bỏ qua hoàn toàn (fail-closed) thay vì âm thầm miễn trừ mọi
 * call site cùng shape — ngăn ai đó vô tình tái tạo đúng lỗ hổng này bằng một
 * entry `:something` mới không giới hạn file. */
function isAllowlisted(method, templatePath, file, allowlist, today) {
  return allowlist.entries.some((entry) => {
    if (!pathMatchesTemplate(templatePath, entry.path)) return false;
    if (entry.method && entry.method !== method) return false;
    if (!entry.expires_on) return false;
    if (entry.expires_on <= today) return false;
    if (isFullyWildcardTemplate(entry.path)) {
      // Toàn wildcard, không neo path — bắt buộc scope theo file, không thì
      // fail-closed (không miễn trừ được gì).
      return !!entry.file && entry.file === file;
    }
    if (entry.file && entry.file !== file) return false;
    return true;
  });
}

/** Phân loại một path/template đã tìm thấy: 'ok' (khớp entry enabled, hoặc
 * được allowlist còn hạn), 'disabled_contract' (khớp entry bị tắt), hoặc
 * 'unknown_literal_route' (không khớp gì, cũng không trong allowlist). Dùng
 * chung cho cả literal thuần lẫn template quy về từ call site dynamic — cùng
 * một cây quyết định, cùng yêu cầu allowlist tường minh nếu muốn miễn. */
export function classify(method, templatePath, manifestEntries, allowlist, today, file = null) {
  const matches = manifestEntries.filter(
    (e) => e.method === method && pathMatchesTemplate(templatePath, e.path),
  );
  if (matches.some((e) => e.enabled)) return "ok";
  if (matches.length > 0) return "disabled_contract";
  if (isAllowlisted(method, templatePath, file, allowlist, today)) return "ok";
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
      if (call.raw === null) continue; // argument đầu tiên không phải string literal — ngoài phạm vi.
      const httpMethod = toHttpMethod(call.method);
      const { template } = buildPathTemplate(call.raw);
      const verdict = classify(httpMethod, template, manifestEntries, allowlist, today, relFile);
      if (verdict === "ok") continue;
      violations.push({
        file: relFile,
        line: call.line,
        path: template,
        reason: verdict,
      });
    }
  });
  return violations;
}

/** Thống kê coverage thật cho báo cáo/CLI: tổng số lệnh gọi ApiClient tìm
 * thấy, bao nhiêu có argument là string literal (dù có nội suy hay không —
 * KHÁC với bản trước đó coi nội suy = bị loại hoàn toàn), và bao nhiêu argument
 * đầu tiên không phải string literal (biến/method call khác — thật sự ngoài
 * phạm vi static-analysis). */
export function computeCoverageStats(rootDir) {
  const resolvedRoot = path.resolve(rootDir);
  const libDir = path.join(resolvedRoot, "frontend", "lib");
  let total = 0;
  let stringArgCount = 0;
  let nonStringArgCount = 0;
  walkDartFiles(libDir, (filePath) => {
    const content = stripComments(fs.readFileSync(filePath, "utf8"));
    for (const call of findApiClientCalls(content)) {
      total++;
      if (call.raw === null) nonStringArgCount++;
      else stringArgCount++;
    }
  });
  return { total, stringArgCount, nonStringArgCount };
}

// ─── CLI entrypoint ───
const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename) {
  const args = process.argv.slice(2);
  let rootDir = ".";
  let manifestPath = "shared/contracts/mvp-surface.json";
  let allowlistPath = "scripts/frontend-api-contract-allowlist.json";
  let showStats = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--root" && args[i + 1]) rootDir = args[++i];
    else if (args[i] === "--manifest" && args[i + 1]) manifestPath = args[++i];
    else if (args[i] === "--allowlist" && args[i + 1]) allowlistPath = args[++i];
    else if (args[i] === "--stats") showStats = true;
  }

  if (showStats) {
    console.log(JSON.stringify(computeCoverageStats(rootDir), null, 2));
    process.exit(0);
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

  console.log("✅ Frontend API contract check passed: mọi literal/template route khớp contract enabled hoặc allowlist còn hạn.");
  process.exit(0);
}
