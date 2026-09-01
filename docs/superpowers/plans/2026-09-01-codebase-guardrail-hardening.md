# Codebase Guardrail Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng các gap guardrail rủi ro cao phát hiện qua phân tích toàn diện
codebase: 2 `@ts-ignore` trong đường xác thực, thiếu CI gate cho
`@ts-ignore`/`@ts-expect-error`, thiếu gate tự động cho endpoint
`expose:true && auth:false`, và 4 file strategy service còn `any` chưa nằm
trong type-safety gate.

**Tech Stack:** TypeScript, Encore.ts, Node.js scripts (theo pattern
`scripts/check_encore_handler_boundaries.mjs`), pytest cho quality gate,
Vitest cho service test, GitHub Actions.

**Spec/Context:** Không có spec riêng — plan này bắt nguồn trực tiếp từ phân
tích toàn diện codebase (3 agent Explore: ranh giới kiến trúc, refactor
strategy, ADR/spec vs code). Xem "Phần Phân tích" ở cuối file để có đầy đủ
bằng chứng.

## Global Constraints

- Không đổi method/path/DTO/semantics của bất kỳ public endpoint nào.
- Không dùng `any`, cast, hay suppression mới để "sửa nhanh" — đúng tinh thần
  CLAUDE.md rule #5 mà chính plan này đang đi enforce.
- Theo đúng pattern add-only baseline đã có (`encore-handler-boundary-baseline.json`)
  cho mọi checker mới: baseline chỉ được xóa entry (khi fix xong), không được
  thêm entry qua CLI thường — chỉ `--write-baseline` mode mới ghi, và không
  được gọi từ CI.
- Comment nghiệp vụ mới viết tiếng Việt; tên định danh, thông báo lỗi hệ thống
  giữ tiếng Anh.
- Mỗi Task kết thúc bằng một commit riêng, message theo convention repo hiện
  tại (`fix(...)`, `chore(...)`, `refactor(...)`, `docs(...)`).

---

### Task 1: Loại bỏ `@ts-ignore` trong 2 auth handler bằng ambient type declaration

**Files:**
- Create: `services/company/shared/types/encore-auth.d.ts`
- Create: `services/cosa/shared/types/encore-auth.d.ts` (hoặc vị trí tương
  đương nếu `services/cosa` không có thư mục `shared/types` — kiểm tra cấu
  trúc thật trước khi tạo, tái dùng nếu đã tồn tại type shim tương tự)
- Modify: `services/company/identity/handlers/auth.handler.ts` (dòng 40-43)
- Modify: `services/cosa/handlers/auth.handler.ts` (dòng 50-53)

**Interfaces:**
- Consumes: module ảo `~encore/auth` do Encore sinh lúc build/run (không tồn
  tại tĩnh lúc typecheck nếu chưa `encore gen` — đây là lý do `@ts-ignore`
  từng được thêm).
- Produces: ambient module declaration generic
  `declare module "~encore/auth" { export function getAuthData<T = unknown>(): T | null; }`
  để cả hai service gọi `mod.getAuthData<AuthData>()` có type an toàn mà
  không cần suppress.

- [x] **Step 1: Xác nhận cấu trúc thư mục thật của từng service trước khi đặt file `.d.ts`.**

Run: `ls services/company/shared/types 2>/dev/null; ls services/cosa/shared 2>/dev/null; find services/cosa -maxdepth 2 -type d`

Xác định vị trí phù hợp nhất theo convention hiện có của từng service (không
tạo thư mục mới nếu đã có chỗ tương đương chứa type shim).

- [x] **Step 2: Viết ambient declaration.**

```ts
// services/company/shared/types/encore-auth.d.ts
// Module ảo do Encore.ts sinh lúc build/run — không tồn tại tĩnh khi
// typecheck trước `encore gen`. Khai báo generic để mỗi call site tự định
// nghĩa AuthData của mình mà không cần @ts-ignore.
declare module "~encore/auth" {
  export function getAuthData<T = unknown>(): T | null;
}
```
Lặp lại (hoặc import chung nếu tsconfig cho phép) cho `services/cosa`.

- [x] **Step 3: Cập nhật 2 điểm dùng, bỏ `@ts-ignore`.**

```ts
// services/company/identity/handlers/auth.handler.ts
try {
  const mod = await import("~encore/auth");
  authData = mod.getAuthData<AuthData>();
} catch {
  // fallback
}
```
Áp dụng tương tự cho `services/cosa/handlers/auth.handler.ts` (hàm
`resolveAuthData`).

- [x] **Step 4: Chạy typecheck từng service để xác nhận ambient decl không bị
  Encore generated code ghi đè hoặc xung đột.**

Run: `cd services/company && pnpm typecheck && cd ../cosa && pnpm typecheck`

Expected: PASS, không còn `@ts-ignore` trong 2 file, không có lỗi type mới.

- [x] **Step 5: Chạy test auth hiện có (nếu có) để xác nhận hành vi runtime không đổi.**

Run: `rg -l "auth.handler" services/company/identity/tests services/cosa/tests 2>/dev/null` rồi
chạy vitest tương ứng nếu tìm thấy; nếu không có test trực tiếp, chạy full
test suite của 2 service để đảm bảo không regressions.

- [x] **Step 6: Commit.**

```bash
git add services/company/shared/types/encore-auth.d.ts \
  services/cosa/shared/types/encore-auth.d.ts \
  services/company/identity/handlers/auth.handler.ts \
  services/cosa/handlers/auth.handler.ts
git commit -m "fix(auth): remove @ts-ignore via typed ~encore/auth shim"
```

---

### Task 2: CI gate cấm `@ts-ignore`/`@ts-expect-error` (add-only baseline, khởi tạo rỗng)

**Files:**
- Create: `scripts/check_ts_suppressions.mjs`
- Create: `scripts/ts-suppression-baseline.json`
- Create: `tests/quality/test_ts_suppressions.py`
- Modify: `Makefile` (thêm target cạnh `encore-handler-boundary-check`)
- Modify: `.github/workflows/quality.yml` (thêm step vào job `boundaries`)
- Modify: `CLAUDE.md` (bổ sung lệnh mới vào rule #6 trong `## Encore
  Guardrails`)

**Interfaces:**
- Consumes: mọi file `.ts` trong `services/company/**` và `services/cosa/**`
  (loại `node_modules`, `*.test.ts`, `*.spec.ts`, `encore.gen`, `.encore`).
- Produces: `runCheck({ rootDir, baselinePath }): { observed: string[];
  additions: string[]; stale: string[] }`, mirror chính xác pattern của
  `scripts/check_encore_handler_boundaries.mjs`, và `make ts-suppression-check`.

- [x] **Step 1: Viết test trước (TDD), dùng fixture tạm thời.**

```python
def test_checker_rejects_new_ts_ignore(tmp_path: Path) -> None:
    f = tmp_path / "services/company/x/y.ts"
    f.parent.mkdir(parents=True)
    f.write_text("// @ts-ignore\nconst x: number = 'oops';\n")
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"version": 1, "entries": []}')
    result = subprocess.run(
        ["node", str(SCRIPT), "--root", str(tmp_path), "--baseline", str(baseline)],
        text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "TS_SUPPRESSION" in result.stderr

def test_no_ts_suppressions_in_repo_after_task1() -> None:
    result = subprocess.run(
        ["node", "scripts/check_ts_suppressions.mjs", "--root", ".",
         "--baseline", "scripts/ts-suppression-baseline.json"],
        text=True, capture_output=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
```

- [x] **Step 2: Chạy test, xác nhận FAIL vì script chưa tồn tại.**

Run: `PYTHONPATH=. pytest tests/quality/test_ts_suppressions.py -q`

Expected: FAIL (script missing).

- [x] **Step 3: Implement scanner — quét text-based cho `@ts-ignore` và
  `@ts-expect-error`, trả về `file:line:TS_SUPPRESSION:<directive>`.**

```js
const DIRECTIVES = ["@ts-ignore", "@ts-expect-error"];

function violationKey(file, line, directive) {
  return `${file}:${line}:TS_SUPPRESSION:${directive}`;
}
```
Bỏ qua dòng nằm trong block comment giải thích (không phải directive thật) —
chỉ match khi directive đứng ở đầu dòng comment `//` ngay trước một statement,
theo đúng cách TS compiler nhận diện directive thật (dòng bắt đầu bằng
`// @ts-ignore` hoặc `// @ts-expect-error`, cho phép khoảng trắng đầu dòng).

- [x] **Step 4: Generate baseline rỗng (vì Task 1 đã xóa 2 vi phạm duy nhất
  đã biết).**

Run: `node scripts/check_ts_suppressions.mjs --root . --baseline scripts/ts-suppression-baseline.json --write-baseline`

Expected: `{"version": 1, "entries": []}` — nếu không rỗng, nghĩa là còn
suppression khác chưa phát hiện trong Phần Phân tích; dừng lại và báo cáo
trước khi tiếp tục (đừng baseline hoá âm thầm).

- [x] **Step 5: Wire vào Makefile và CI.**

```make
ts-suppression-check:
	node scripts/check_ts_suppressions.mjs --root . --baseline scripts/ts-suppression-baseline.json
```
Thêm `- run: make ts-suppression-check` ngay sau step
`make encore-handler-boundary-check` trong job `boundaries` của
`.github/workflows/quality.yml`.

- [x] **Step 6: Cập nhật CLAUDE.md rule #6 để liệt kê lệnh mới.**

Sửa dòng: `... make company-boundary-check, make encore-handler-boundary-check, và migration gates ...`
→ thêm `make ts-suppression-check`.

- [x] **Step 7: Chạy toàn bộ gate để xác nhận.**

Run: `PYTHONPATH=. pytest tests/quality/test_ts_suppressions.py -q && make ts-suppression-check`

Expected: PASS, baseline rỗng.

- [x] **Step 8: Commit.**

```bash
git add scripts/check_ts_suppressions.mjs scripts/ts-suppression-baseline.json \
  tests/quality/test_ts_suppressions.py Makefile .github/workflows/quality.yml CLAUDE.md
git commit -m "chore(quality): forbid new @ts-ignore/@ts-expect-error via CI gate"
```

---

### Task 3: Codify audit "expose:true && auth:false" thành allowlist gate tự động

**Files:**
- Create: `tests/quality/test_route_auth_allowlist.py`
- Modify: `scripts/route_inventory.py` (nếu cần expose data structure cho
  test tái dùng — kiểm tra trước, ưu tiên tái dùng logic quét route đã có
  thay vì viết lại)
- Modify: `Makefile`, `.github/workflows/quality.yml`

**Interfaces:**
- Consumes: cùng nguồn route mà `scripts/route_inventory.py` đã quét
  (`expose:`/`auth:` literal trong `api({...})` calls).
- Produces: danh sách allowlist tường minh 9 endpoint đã audit + assertion
  "mọi endpoint expose:true && auth:false phải nằm trong allowlist".

- [x] **Step 1: Trích xuất danh sách 9 endpoint `auth:false` hiện tại làm
  allowlist ban đầu.**

Run: `rg -n 'auth:\s*false' services/company services/cosa --type ts -g '*.handler.ts'`

Đối chiếu với danh sách đã audit trong Phần Phân tích (login/register,
healthz, `/platform/internal/*`, `/identity/session/renew`) — xác nhận đúng
9, không thiếu/thừa so với grep thật.

- [x] **Step 2: Viết test trước.**

```python
ALLOWLIST = {
    "/identity/session/renew",
    "/platform/auth/sessions",
    "/platform/auth/register",
    # ... đủ 9 path xác nhận ở Step 1, kèm comment lý do (login/register
    # trước khi có token; healthz; platform-internal tự verify token thủ công)
}

def test_every_unauthenticated_expose_endpoint_is_allowlisted() -> None:
    routes = collect_routes()  # tái dùng parser của route_inventory.py
    danger = {r.path for r in routes if r.expose and not r.auth}
    unexpected = danger - ALLOWLIST
    assert not unexpected, f"New expose&&!auth endpoint(s) need manual audit: {unexpected}"
```

- [x] **Step 3: Chạy test, xác nhận PASS với allowlist khớp thực tế (không
  phải khớp giả để test xanh — nếu lệch, quay lại Step 1 grep lại).**

Run: `PYTHONPATH=. pytest tests/quality/test_route_auth_allowlist.py -q`

- [x] **Step 4: Thử thêm tạm 1 endpoint giả `expose:true, auth:false` ngoài
  allowlist để xác nhận gate thật sự fail, rồi revert thay đổi thử nghiệm.**

Run: thêm endpoint test vào 1 file `.handler.ts` tạm, chạy lại pytest, xác
nhận FAIL với thông báo path lạ, sau đó `git checkout -- <file>`.

- [x] **Step 5: Wire vào Makefile/CI.**

```make
route-auth-allowlist-check:
	PYTHONPATH=. pytest tests/quality/test_route_auth_allowlist.py -q
```
Thêm vào job `boundaries` cùng chỗ với 2 check trên.

- [x] **Step 6: Commit.**

```bash
git add tests/quality/test_route_auth_allowlist.py Makefile .github/workflows/quality.yml \
  scripts/route_inventory.py
git commit -m "chore(quality): gate unauthenticated expose endpoints behind explicit allowlist"
```

---

### Task 4: Mở rộng type-safety gate cho 4 service strategy còn lại

**Files:**
- Modify: `services/company/operations/strategy/services/maturity-assessment.service.ts` (dòng 134)
- Modify: `services/company/operations/strategy/services/metric-contract.service.ts` (dòng 87)
- Modify: `services/company/operations/strategy/services/next-best-action.service.ts` (dòng 29-31, 168-170, 190-245, 301-310)
- Modify: `services/company/operations/strategy/services/weekly-review.service.ts` (dòng 20, 33, 41, 59-84, 143)
- Modify: `tests/quality/test_strategy_type_safety.py` (thêm 4 file vào whitelist)
- Có thể cần: mở rộng `services/company/operations/strategy/services/strategy-json.ts`
  nếu shape dữ liệu JSON của các service này khớp `JsonValue`/`JsonObject` đã
  có sẵn — ưu tiên tái dùng thay vì định nghĩa type JSON mới.

**Interfaces:**
- Consumes: `JsonValue`/`JsonObject`/`toJsonObject`/`toJsonArray` từ
  `strategy-json.ts` (đã có, đã test) cho các chỗ `any` liên quan tới dữ liệu
  JSON động; định nghĩa interface/union type mới cho các chỗ `any` là domain
  shape rõ ràng (không phải JSON tự do).
- Produces: 4 file compile sạch không còn `any` tường minh, hành vi runtime
  không đổi.

- [x] **Step 1: Đọc từng vị trí `any` đã liệt kê, phân loại: (a) JSON tự do
  → dùng `strategy-json.ts` helper, (b) shape domain cố định → viết interface
  cụ thể, (c) kiểu chưa rõ do thiếu thông tin → hỏi lại thay vì đoán bằng
  `unknown`+cast tùy tiện.**

- [x] **Step 2: Với mỗi file, viết/chạy test hiện có trước khi sửa để có
  baseline hành vi.**

Run: `cd services/company && pnpm vitest run operations/tests -t "maturity-assessment|metric-contract|next-best-action|weekly-review"`

(điều chỉnh pattern theo tên test file thật sau khi grep `find services/company/operations/tests -iname '*maturity*' -o -iname '*metric-contract*' -o -iname '*next-best-action*' -o -iname '*weekly-review*'`)

- [x] **Step 3: Sửa từng file, thay `any` bằng type cụ thể. Ví dụ dạng
  chung (điều chỉnh theo shape thật sau khi đọc code):**

```ts
// Trước: mapping: any
// Sau, nếu là JSON tự do:
mapping: JsonObject
// Hoặc nếu shape cố định:
interface MetricMapping {
  sourceField: string;
  targetMetricId: string;
  transform?: "sum" | "avg" | "latest";
}
```

- [x] **Step 4: Chạy lại test tương ứng + typecheck sau mỗi file sửa (không
  gộp cả 4 file rồi mới test).**

Run: `cd services/company && pnpm typecheck && pnpm vitest run operations/tests`

Expected: PASS sau mỗi file, không đổi assertion nào trong test hiện có.

- [x] **Step 5: Thêm 4 file vào whitelist của `test_strategy_type_safety.py`.**

- [x] **Step 6: Chạy full gate.**

Run: `PYTHONPATH=. pytest tests/quality/test_strategy_type_safety.py -q && cd services/company && pnpm typecheck && pnpm vitest run operations/tests/strategy`

Expected: PASS với 13/13 file trong whitelist.

- [x] **Step 7: Commit (có thể tách 1 commit/file nếu diff lớn, hoặc 1 commit
  gộp nếu nhỏ — quyết định theo dung lượng diff thật khi thực thi).**

```bash
git add services/company/operations/strategy/services/maturity-assessment.service.ts \
  services/company/operations/strategy/services/metric-contract.service.ts \
  services/company/operations/strategy/services/next-best-action.service.ts \
  services/company/operations/strategy/services/weekly-review.service.ts \
  tests/quality/test_strategy_type_safety.py
git commit -m "refactor(strategy): remove remaining any usage in gate/action/review services"
```

---

### Task 5: Đính chính 2 ADR lệch thực tế (tài liệu, rủi ro thấp)

**Files:**
- Modify: `docs/architecture/adr/ADR-SLUG-001-workspace-slug-subdomain.md`
- Modify: `docs/architecture/adr/ADR-ID-MODEL-001-spine-snowflake-leaf-uuidv7.md`

**Interfaces:** không có — thay đổi tài liệu thuần túy, không chạm code.

- [x] **Step 1: Sửa `ADR-SLUG-001`.**

Thay đoạn mô tả vị trí implementation từ `services/cosa/storage/schema.ts`
sang vị trí thật: `services/company/identity/services/
slug-reservation.service.ts` + bảng `identityWorkspaceSlugs` trong schema
`services/company`. Giữ nguyên quyết định kiến trúc (Status: ACCEPTED),
thêm ghi chú cuối "Vị trí implementation đã được đính chính sau khi verify
lại bằng grep — 2026-09-01."

- [x] **Step 2: Sửa `ADR-ID-MODEL-001`.**

Thêm section rõ ràng ngay dưới Status: "LeafId/UUIDv7 chưa được triển khai
trong code (verify bằng grep toàn repo, 2026-09-01) — chỉ Snowflake spine đã
implement. Không lên kế hoạch implement UUIDv7 cho đến khi có nhu cầu nghiệp
vụ cụ thể (YAGNI)."

- [x] **Step 3: Verify bằng chính công cụ mà CLAUDE.md yêu cầu (grep, không
  tin ngày tháng).**

Run: `rg -n 'uuid.?v7|leaf.?id' services -i` (xác nhận vẫn 0 kết quả, tức ghi
chú vẫn đúng tại thời điểm commit) và
`rg -n 'workspace_slugs|identityWorkspaceSlugs' services/cosa services/company`
(xác nhận vị trí mới nêu trong ADR khớp thật).

- [x] **Step 4: Commit.**

```bash
git add docs/architecture/adr/ADR-SLUG-001-workspace-slug-subdomain.md \
  docs/architecture/adr/ADR-ID-MODEL-001-spine-snowflake-leaf-uuidv7.md
git commit -m "docs(adr): correct slug service location and flag unimplemented uuidv7 leaf id"
```

---

### Task 6: Chứng minh toàn bộ gate mới hoạt động cùng nhau

**Files:** không sửa.

- [x] **Step 1: Chạy toàn bộ quality gate liên quan.**

Run:
```bash
PYTHONPATH=. pytest tests/quality/test_ts_suppressions.py \
  tests/quality/test_route_auth_allowlist.py \
  tests/quality/test_strategy_type_safety.py \
  tests/quality/test_encore_handler_boundaries.py -q
make ts-suppression-check route-auth-allowlist-check encore-handler-boundary-check company-boundary-check
cd services/company && pnpm typecheck && cd ../cosa && pnpm typecheck
```

Expected: tất cả PASS.

- [x] **Step 2: Verify CI wiring.**

Run: `rg -n 'ts-suppression-check|route-auth-allowlist-check' Makefile .github/workflows/quality.yml`

Expected: mỗi target xuất hiện đúng 1 lần trong Makefile và 1 lần trong
workflow.

---

## Phần Phân tích (bằng chứng nguồn — tham khảo, không phải task)

### Ranh giới 4 vùng kiến trúc
`packages/agent` không import gì từ `services/company/*` (3 match grep đều
là comment/docstring) — boundary hiện sạch.

### Rủi ro guardrail phát hiện
- `@ts-ignore` trong đường xác thực: `services/company/identity/handlers/auth.handler.ts:41`,
  `services/cosa/handlers/auth.handler.ts:51` → **Task 1, 2**.
- `encore-type-safety-check` chỉ whitelist 9/13 file strategy service, 4 file
  còn `any`: `maturity-assessment.service.ts:134`,
  `metric-contract.service.ts:87`, `next-best-action.service.ts` (nhiều
  chỗ), `weekly-review.service.ts` (nhiều chỗ) → **Task 4**. Ngoài strategy,
  còn ~39 file khác dùng `any` (backlog, không nằm trong plan này).
- `route_inventory.py` tính danger list `expose&&!auth` chỉ để report, không
  phải gate cứng → **Task 3**.
- `check_company_boundaries.mjs` chỉ active cho path `/domain/`/`/application/`,
  gần như không bảo vệ cấu trúc phẳng hiện tại của phần lớn `services/company`
  — ghi nhận là backlog, không nằm trong plan này (cần quyết định mở rộng
  hay deprecate).
- `academy/handlers/*` dùng raw `throw new Error` nhưng chưa wire `api()` —
  backlog, theo dõi trước khi wire Encore thật cho module này.

### Refactor "zero-db handler boundary" cho Strategy — ~90% xong
Cấu trúc 100% (0 handler còn import DB trực tiếp, gate PASS, baseline rỗng).
Type-safety hardening 9/13 file — 4 file còn lại là **Task 4**.

### Strategy Canvas Facade (frontend) — spec duyệt, code 0%
`docs/superpowers/specs/2026-09-01-strategy-canvas-facade-design.md` +
`docs/superpowers/plans/2026-09-01-strategy-canvas-facade.md` (26 task, chưa
tick) — chưa có `CanvasFacade` nào trong `frontend/lib/features/strategy/`.
Không nằm trong scope plan này.

### ADR lệch code
- `ADR-ID-MODEL-001`: Snowflake spine khớp code (`services/cosa/services/snowflake.service.ts`,
  `services/company/shared/services/snowflake.service.ts`); LeafId/UUIDv7:
  0 kết quả grep toàn repo → **Task 5**.
- `ADR-SLUG-001`: bảng slug thật nằm ở `services/company/identity/services/
  slug-reservation.service.ts` (bảng `identityWorkspaceSlugs`), ADR ghi sai
  là `services/cosa` → **Task 5**.
- Các ADR/spec khác đã verify khớp code hoặc tự gắn nhãn trạng thái đúng,
  không cần sửa.
- Claim CLAUDE.md về RPC HTTP thật `services/company` ↔ `services/cosa` qua
  `platform.client.ts` + `cosa-delegation.service.ts`: xác nhận đúng, có
  logic thật (fail-closed, chống replay JWT).

### Backlog không nằm trong plan này (để người dùng ưu tiên sau)
1. Dọn `any` trong ~39 file ngoài strategy module.
2. Quyết định mở rộng hay deprecate `check_company_boundaries.mjs`.
3. Review `commercial/handlers/customer-engagement/desk.handler.ts` (333
   dòng) — khả năng logic nghiệp vụ nằm sai layer.
4. Chuẩn hóa `throw new Error` trong `academy/handlers/*` trước khi wire
   Encore `api()` thật.
5. Triển khai Strategy Canvas Facade (frontend) — 0% code, plan đã có.
