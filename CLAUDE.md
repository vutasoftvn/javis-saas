# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

COSA là **Founder / Company Operating System với Agent Platform composable**. Không coi COSA là tập hợp các AI agent độc lập.

## Lệnh thường dùng (Commands)

### Cài đặt & dev stack

```bash
cp .env.example .env && ./install.sh   # lần đầu (macOS/Linux/WSL); Windows: .\install.ps1
make dev-stack             # docker infra + migrate (Agent→COSA→Company) + Company:4000 + COSA:4001 + FastAPI:8000 + Worker, foreground, Ctrl+C dọn sạch cả 4 tiến trình
make dev-stack-no-infra    # bỏ qua docker+migrate nếu Postgres/MinIO/LiveKit đã chạy sẵn
make dev-status            # kiểm tra port/tiến trình đang chạy
make dev-preflight         # kiểm tra config/migration/health trước khi chạy
```

Encore.ts **không tự nạp** `.env` — dùng direnv (xem README.md) hoặc chạy
`source scripts/load-dev-env.sh` ở mỗi terminal mới trước khi gọi `make`.

### Lint & type-check

```bash
make lint                                    # ruff check + format check (packages/agent, apps/cosa, packages/agent_integrations)
make lint-fix                                # tự sửa
make typecheck-py                            # mypy
cd services/company && npm run typecheck     # tsc --noEmit (tương tự cho services/cosa)
```

### Test theo từng vùng

```bash
# Python — packages/agent (coverage gate 80%)
make agent-test
# 1 test riêng lẻ (kích hoạt venv trước — repo dùng .venv/bin/python, không phải python hệ thống):
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/kernel/test_openai_agents_kernel.py::test_name -q

# Python — apps/cosa (coverage gate 78%; target tự set AGENT_DATABASE_URL/
# COSA_DATABASE_URL/DATABASE_URL="" để cô lập khỏi Postgres dev thật — test
# dùng InMemory*/fixture riêng)
make apps-cosa-test

# Encore.ts — services/company và services/cosa là 2 Encore app độc lập,
# mỗi app "encore test" riêng (`encore test` không gộp được cả 2 app)
make services-test            # cả 2, tuần tự
make services-test-company    # = cd services/company && encore test
make services-test-cosa       # = cd services/cosa && encore test
# 1 file/test riêng (vitest chạy dưới encore test):
cd services/cosa && npx vitest run tests/agent-policy.test.ts

# Flutter frontend
make frontend-test                                    # toàn bộ
cd frontend && flutter test test/path/to/test.dart     # 1 file riêng
make frontend-analyze                                  # flutter analyze

# E2E
make e2e-test               # golden path, không cần Encore CLI/Postgres disposable
make e2e-cross-plane-smoke  # 4 plane thật + Postgres disposable — cần `encore` CLI cài
                             # sẵn và PGPASSWORD khớp POSTGRES_PASSWORD thật trong .env
                             # (KHÔNG phải mặc định "postgres" của thư viện test)
```

### Gate tổng hợp trước khi báo cáo "xong"

```bash
make verify         # gate CI đầy đủ: lint + typecheck + boundary + skillpacks + tenancy
                     # + contract-freeze + agent-test + apps-cosa-test + services-test
                     # + frontend-test/analyze
make verify-local    # biến thể máy dev: thêm e2e-test + e2e-cross-plane-smoke
```

Còn nhiều gate hẹp hơn theo đúng vùng vừa sửa — chạy gate tương ứng thay vì luôn
chạy `make verify` đầy đủ: `make boundary-check`, `make company-boundary-check`,
`make encore-handler-boundary-check`, `make ts-suppression-check`,
`make frontend-api-contract-check`, `make route-auth-allowlist-check`,
`make skillpacks-validate`, `make contract-freeze-check`. Xem đầu file
`Makefile` (dòng `.PHONY`) để biết toàn bộ target sẵn có.

### Migration

```bash
make dev-migrate               # dev: Agent Core → COSA → Company (thứ tự bắt buộc)
make migrate-all                # production/VPS: tương tự, dùng *_MIGRATOR_DATABASE_URL
make services-migrate-company   # chỉ 1 service (node scripts/migrate.mjs)
make services-migrate-cosa
make migrate-agent-platform     # chỉ packages/agent (Python, schema Postgres riêng)
```

### Deploy (VPS)

```bash
make deploy-preflight   # kiểm tra env/health/backup policy trước
make deploy              # preflight → migrate-all → deploy-app (tuần tự bắt buộc)
```

## Quy tắc Git & Workspace (BẮT BUỘC)

- **Tuyệt đối KHÔNG tạo git worktree:** Không bao giờ chạy `git worktree add` hoặc tạo / chuyển ngữ cảnh làm việc sang worktree tách biệt.
- **Code trực tiếp trong `main`:** Mọi thao tác đọc, sửa code, chạy lệnh, refactor và commit phải được thực hiện trực tiếp trên nhánh `main` tại thư mục gốc của repository này.

## Nguồn sự thật kiến trúc

**Quyết định 2026-08-31 — Option 1 "keep deleted":** 5 tài liệu source-of-truth cũ
(`COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`,
`COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md`,
`COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`,
`COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`,
`DB_FINAL_CUTOVER.md`) cùng nhiều ADR cũ đã bị xóa trong commit `34507dd9`
(2026-08-27). Giữ nguyên trạng thái đã xóa, không khôi phục. Các file tên tương
tự trong `docs/archive/` chỉ là lưu trữ lịch sử, KHÔNG phải nguồn sự thật.

**Document index hiện tại** (chỉ đọc các file TỒN TẠI trong cây):

- `docs/architecture/adr/` — ADR đang hoạt động: `ADR-AGENT-REG-001`,
  `ADR-AI-COMPLIANCE-RUNTIME-001`, `ADR-CONV-001`, `ADR-COSA-DELEGATION-002`,
  `ADR-CUTOVER-001`, `ADR-DEPLOY-001`, `ADR-ID-MODEL-001`,
  `ADR-LOCAL-EVENT-BACKBONE-001`, `ADR-LOCAL-FIRST-001`, `ADR-SLUG-001`. Trước
  khi hành động, kiểm tra ADR liên quan tại đây. Danh sách này tự nó có thể lỗi
  thời — `ls docs/architecture/adr/` để chắc chắn không bỏ sót ADR mới hơn.
- `docs/superpowers/specs/` — design đã duyệt (vd.
  `2026-08-31-maintainable-modular-truthful-mvp-design.md`).
- `docs/superpowers/plans/` — plan triển khai đã duyệt.
- `docs/architecture/generated/` — snapshot sinh tự động (contracts, route
  inventory, company usage inventory) — generator-owned, không hand-edit.

**Runtime:** OpenAI Agents SDK là primary execution runtime, DeepSeek là primary
model provider (qua LiteLLM), LangChain là optional adapter.

**Control Plane:** vị trí tại `services/cosa` (Encore/TS). Schema + service code
TypeScript đã tồn tại; claim "zero production consumer" (tính đến 2026-08-25)
đã lỗi thời — kể từ 2026-08-31, `services/company` gọi RPC HTTP thật sang
`services/cosa` (`identity/services/platform.client.ts` xác thực workspace
membership; `shared/auth/cosa-delegation.service.ts` bridge token cho
`apps/cosa`). Luôn kiểm tra lại bằng grep thay vì tin ngày trong ghi chú này.

**3 secret cross-plane, mỗi secret đúng 1 chiều ký→verify — không tái dùng
chéo** (xem `ADR-COSA-DELEGATION-002` cho bối cảnh đầy đủ):
`PLATFORM_JWT_SECRET` (`services/cosa` ký, `services/cosa` gateway + `apps/cosa`
verify — danh tính platform), `JWT_SECRET` (`services/company` ký, `apps/cosa`
verify — local business session), `COSA_COMPANY_DELEGATION_SECRET`
(`apps/cosa` ký → `services/company` verify, scoped `{workspace_id, run_id,
capability_ids}`), `COSA_CONTROL_DELEGATION_SECRET` (`apps/cosa` ký →
`services/cosa` verify, scoped `{workspace_id, role}` — dùng cho
`agent-policy-snapshot` + `/cosa/schedules*`). Không dùng đè secret này cho
secret khác dù "có vẻ tiện" — đúng thứ từng gây bug B5 (agent run thật fail
`policy_snapshot_unavailable` vì forward nhầm token platform sang endpoint chỉ
hiểu local-session, đã vá).

Trạng thái ACCEPTED chỉ xác nhận quyết định kiến trúc; không mặc định có
nghĩa implementation, migration cutover, runtime wiring hoặc production
verification đã hoàn tất. Luôn kiểm tra trạng thái triển khai thực tế
(ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION là 5 trục khác nhau)
trước khi sửa code hoặc báo cáo tiến độ.

## Bốn vùng kiến trúc

```text
Experience Plane      Flutter (text chat, voice, API)
COSA Control Plane    services/cosa      (Encore/TS — global identity, license, plan)
Company Business      services/company   (Encore/TS — identity, operations/strategy, commercial, finance-legal)
Agent Platform        packages/agent (Python, reusable) + apps/cosa (Python, composition)
```

- `packages/agent/` **không được import** bất cứ gì từ `services/company/*`. Chỉ `apps/cosa/` được compose cả hai phía.
- `legacy/` đã xoá hẳn 2026-08-25 (bao gồm `agentos/` archive cũ, `legacy/backend`, `legacy/agent_runtime`, và các thư mục split-out khác). Mọi tính năng runtime hiện hoạt đều nằm tại `packages/agent/` và `apps/cosa/`.

**AgentSpec — authoring hard-code, resolution qua registry (hybrid, có chủ
đích):** agent hiện có (`operations`, `finance`, `marketing`,
`customer_support`, `customer_support_autopilot`) khai báo dạng Python
constant trong `apps/cosa/agents/specs.py` (đổi = sửa code + redeploy — theo
`ADR-AGENT-REG-001`, registration API runtime là post-launch). Nhưng lúc chạy,
`apps/cosa/worker/handlers.py` **không tin object Python đang import** — luôn
`SpecResolver(repository=plane.spec_registry).resolve_agent_spec_dependencies()`
theo exact-hash (chống drift khi rolling-deploy nhiều worker chạy code khác
nhau cùng lúc). Chọn spec nào cho 1 `agent_profile` là bảng ánh xạ tường minh
(`_AGENT_PROFILE_SPECS`) — thêm agent_profile mới PHẢI thêm vào bảng này,
không dựa vào so khớp chuỗi/fallback ngầm (bug thật đã xảy ra: agent
`marketing` từng luôn âm thầm chạy nhầm bằng spec `operations`).

**Skill (`skillpacks/`) tách khỏi Agent (`AgentSpec`):** `skillpacks/<domain>/<name>/`
(`manifest.yaml` + `SKILL.md`) là nội dung khai báo tĩnh, có API lifecycle
runtime riêng (`pending → adapted → published → pinned`/`retired`, xem
`apps/cosa/api/skill_registry_routes.py`) — trưởng thành hơn Agent registry.
`packages/agent/skills/` là hạ tầng generic validate/publish/registry (không
biết gì về COSA); `apps/cosa/agents/skillpack_seed.py` là composition layer
seed built-in skillpack vào registry lúc khởi động. Mỗi `AgentSpec` pin skill
qua `PinnedSkillRef{skill_id, version, definition_hash}` — resolve sai hash
raise lỗi, không tự dùng version mới hơn.


## Quy tắc bắt buộc

1. **Business truth thuộc `services/*` (TypeScript/Encore), không thuộc LLM runtime.** Agent Platform không tự quyết định authorization hay ghi business DB trực tiếp — mọi side effect qua Capability Layer + Governance + Audit.
2. **Một danh tính workforce duy nhất: `WorkforceMember`.** Không tạo bảng nhân sự riêng cho AI vs người.
3. **Không tạo Agent mới khi chưa cần.** Trước tiên hỏi: đây là Skill / Tool / Workflow / Knowledge / Executor / Integration? Chỉ tạo Agent Profile khi có vai trò nghiệp vụ thật mới.
4. **Không nhân bản kiến trúc.** Trước khi thêm prompt/skill/tool/workflow/agent/service mới, tìm trong repo xem đã có chưa — ưu tiên compose/reuse.
5. **Governance là code xác định, không phải LLM tự quyết.** Approval phải bind đúng `run_id + tool_call_id + checkpoint_ref`, không lookup theo tên action. Constraint lịch sử (đã REQUIRE_APPROVAL) không tự mất khi policy sau nới lỏng.
6. **Test durability phải qua process thật.** Một test "resume sau restart" chỉ tạo instance thứ hai trong cùng process không được coi là chứng minh — đây là gap đã phát hiện trong audit, đừng lặp lại.
7. **Trạng thái ứng dụng phải structured, không suy diễn từ văn bản tự nhiên.** Không dùng kiểu `if "blocked" in model_text`.
8. **Hành động rủi ro cao (deploy, xóa dữ liệu, gửi tin nhắn ra ngoài, đổi quyền, hành động tài chính) cần approval qua code, không qua prompt.**
9. **Trước khi coi một API/service là "không ai dùng":** kiểm tra cả phía client (frontend có gọi không) lẫn phía deploy (có server nào start không) — đừng chỉ nhìn một phía. Absence of reported traffic không đồng nghĩa absence of attempted traffic.
10. **An toàn khi sửa code:** chạy `git status` trước thao tác có thể mất dữ liệu; không dùng `--force`/`--no-verify` trừ khi được yêu cầu rõ; không tự ý xóa/archive file — xác nhận với người dùng trước hành động phá hủy.
11. **Không tuyên bố "xong" khi chưa test.** Mỗi thay đổi hành vi cần test tương ứng; chạy test trước khi báo cáo hoàn thành.
12. **Không bao giờ tạo git worktree — Code trực tiếp trong `main`:** Tuyệt đối KHÔNG tạo worktrees (`git worktree add`, v.v.). Luôn luôn chỉnh sửa code, chạy lệnh và commit trực tiếp trên nhánh `main` tại root workspace.

## Encore.ts (services/company, services/cosa)

Mỗi service theo layout: `encore.service.ts`, `api.ts` (barrel export), `db.ts`, `handlers/` (parse input → gọi service → trả response, không query DB trực tiếp), `services/` (business logic, Drizzle ORM, transaction), `models/` (re-export DB), `migrations/`, `tests/`.

- Lỗi trả về qua `APIError` (`invalidArgument`, `unauthenticated`, `permissionDenied`, `notFound`, `alreadyExists`, `internal`) — không throw `Error` trần.
- Endpoint nội bộ giữa service: `expose: false`. Chỉ endpoint cho client ngoài mới `expose: true`.
- Schema Drizzle tập trung ở `<app>/shared/db/schema/<service>.ts` (không rải trong `models/` của từng service) — tránh circular import khi service cần join bảng chéo.
- Đổi schema DB phải có migration; sau khi thêm migration mới chạy `node scripts/migrate.mjs` (hoặc `make services-migrate-company` / `make services-migrate-cosa`).

## Encore Guardrails (BẮT BUỘC)

1. Handler chỉ khai báo endpoint, xác thực/tenant guard, validate-normalize input,
   gọi service và map response/error. Không import `drizzle-orm`, `models/db`,
   `db.ts` hoặc DB schema trong handler (handler không truy cập DB/Drizzle/schema trực tiếp).
2. `expose: true` phải có auth/tenant guard hoặc webhook verification được test;
   endpoint nội bộ dùng `expose: false`.
3. Lỗi từ public request dùng `APIError` tại boundary; không để `Error` trần tới client.
4. Migration release chỉ Expand (migration release chỉ Expand). Contract destructive cần release riêng, ADR, backup
   và evidence rollback N-1.
5. Không dùng `any`, `@ts-ignore`, `@ts-expect-error` hay cast để che typecheck.
6. Thay đổi Encore phải chạy typecheck service, relevant test, `make company-boundary-check`,
   `make encore-handler-boundary-check`, `make ts-suppression-check`, và migration gates nếu có SQL thay đổi.
7. Thay đổi route/endpoint gọi từ frontend (`frontend/lib/**`) phải chạy
   `make frontend-api-contract-check` — chặn literal route lệch khỏi
   `shared/contracts/mvp-surface.json` (route đã xoá quay lại lặng lẽ, hoặc
   route unknown gọi thẳng bằng string tay thay vì qua contract/`MvpEndpoint`).


## Ngôn ngữ phản hồi

Mọi agent phản hồi bằng **tiếng Việt** cho phần hội thoại, phân tích, plan và
`docs/**/*.md`. Định danh, route, log/error message, biến môi trường và trích dẫn
nguyên văn tiếng Anh giữ nguyên. Nguồn chuẩn:
`.kilocode/rules/00-language-vietnamese.md` (mirror tại
`.agents/rules/language_vietnamese.md`). Canonical prompt của agent runtime trong
`skillpacks/` và `packages/agent/` vẫn là tiếng Anh — rule này không áp dụng ở đó.

## Comment code

Viết bằng tiếng Việt cho phần giải thích ý nghĩa/lý do (why). Tên định danh, thông báo lỗi hệ thống/log, và trích dẫn nguyên văn tài liệu tiếng Anh vẫn giữ tiếng Anh. Không bắt buộc viết lại comment cũ ngay — áp dụng cho comment mới, chuyển dần khi sửa file.

## Trước khi làm việc lớn

1. Đọc code hiện có, tìm component/pattern có thể tái dùng trước khi viết mới.
2. Xác định đúng layer kiến trúc (4 vùng ở trên).
3. Làm thay đổi nhỏ nhất an toàn, giữ hành vi đang chạy đúng.
4. Với việc nhiều bước: viết plan trước khi sửa code (không có plan → không thực thi).
5. Chạy test/verify sau mỗi thay đổi có ý nghĩa.
