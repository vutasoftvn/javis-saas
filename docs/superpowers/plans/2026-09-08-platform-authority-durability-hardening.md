# Platform Authority and Durability Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng các lỗ hổng authority, tenancy, approval, tính bền vững của run và Snowflake transport đã được xác minh trong COSA, đồng thời đưa các gate tích hợp về trạng thái tái lập được.

**Architecture:** `services/cosa` tiếp tục là nguồn sự thật cho Platform workspace/membership; `services/company` quyết định quyền nghiệp vụ; `apps/cosa` chỉ điều phối Agent và luôn xác minh authority ở server. Membership mới chỉ được tạo qua invitation một lần có hạn; các thay đổi run dùng transition bền vững trong Agent PostgreSQL, không dùng state trong memory của kernel làm authority.

**Tech Stack:** Encore.ts, Drizzle/PostgreSQL, FastAPI/Pydantic, Python 3.11, SQLAlchemy/asyncpg, Flutter/Dart, pytest, Vitest và Flutter test.

**Spec:** [README hardening constraints](../../../README.md#điều-kiện-bắt-buộc-trước-khi-mở-workspace-ra-bên-ngoài) và các phát hiện có tái hiện trong đợt audit ngày 2026-09-08.

## Global Constraints

- Làm trực tiếp tại root trên `main`; không tạo git worktree.
- Business truth thuộc `services/*`; Agent Platform không ghi trực tiếp Business database.
- Dùng Snowflake ID dưới dạng `string` xuyên HTTP/JSON/Flutter; không ép qua `number`, `int` hoặc `double`.
- Mọi migration là expand-only; xác minh số migration cao nhất ngay trước khi thêm file.
- Public endpoint phải có bearer auth + membership guard, hoặc có webhook verification được test; internal RPC dùng `expose: false`.
- Không dùng role/hay workspace ID do client gửi làm authority. Quyền approval và finance phải được resolver server-side xác minh.
- Cancellation phải là state database có điều kiện chuyển trạng thái; terminal `CANCELLED` không được worker ghi đè.
- Không commit `.env`, DSN thật, password hay token. Test tích hợp dùng disposable Postgres/port riêng, không dùng service local đang chạy.
- Mỗi task phải bắt đầu bằng test đỏ, kết thúc bằng test xanh và một commit tách biệt. Không gộp migration với feature không liên quan.

---

## File structure

| Path | Responsibility |
|---|---|
| `docs/architecture/adr/ADR-WORKSPACE-INVITATION-001.md` | Quyết định immutable về invite, role cấp được, expiry/revoke và rollout. |
| `services/cosa/storage/schema.ts` | Drizzle table `workspace_invitations` và status/unique index. |
| `services/cosa/migrations/34_workspace_invitations.up.sql` | Schema invitation expand-only; số `34` phải đổi nếu sequence đã tăng. |
| `services/cosa/services/workspace-invitation.service.ts` | Issue, list, revoke, accept invitation trong transaction. |
| `services/cosa/handlers/company.handler.ts` | Thay `companies/join` bằng invitation endpoints có auth. |
| `services/cosa/services/company.service.ts` | Xóa membership creation theo `company_id` biết được. |
| `services/company/identity/handlers/workspace.handler.ts` | Bảo vệ hoặc internalize workspace read endpoint. |
| `services/company/identity/services/command-authority.service.ts` | Authority action dành cho financial write. |
| `services/company/finance-legal/services/financial-transaction.service.ts` | Require business command authority trước khi ghi transaction. |
| `apps/cosa/api/approval_authority.py` | Resolve role server-side để áp dụng `approval.requirement`. |
| `apps/cosa/api/workforce_routes.py` | Chặn quyết định approval sai role trước `submit_decision`. |
| `packages/agent/runs/repository.py` | Conditional durable transitions, gồm `cancel_run`. |
| `packages/agent/kernel/openai_agents_kernel.py` | Dừng dựa trên persisted status và không complete run đã cancel. |
| `apps/cosa/api/routes.py` | Cancel route gọi durable transition, chỉ emit event nếu transition thành công. |
| `frontend/lib/modules/auth/services/auth_service.dart` | Gửi invitation token và Snowflake ID dạng string. |
| `frontend/test/auth_flow_test.dart` | Transport contract không mất precision. |
| `tests/e2e/stack/subprocess_stack.py` | Chuẩn hoá DSN riêng cho asyncpg và fixture disposable. |
| `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py` | Lease race chạy trên DSN test có chủ sở hữu rõ ràng. |
| `README.md` | Cập nhật route/authority contract và trạng thái release gate sau khi mỗi wave đạt evidence. |

## Task 1: Chốt authority contract trước khi đổi schema

**Files:**
- Create: `docs/architecture/adr/ADR-WORKSPACE-INVITATION-001.md`
- Modify: `README.md:236-255`
- Test: `services/cosa/tests/control-plane.test.ts`

**Interfaces:**

```ts
type InvitationRole = "member" | "admin";
type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

interface CreateWorkspaceInvitationParams {
  workspace_id: string;
  email: string;
  role_id: InvitationRole;
  expires_in_hours?: number;
}

interface AcceptWorkspaceInvitationParams {
  token: string;
}
```

- [ ] **Step 1: Ghi ADR với các quyết định không được suy diễn.** Chọn contract mặc định: token ngẫu nhiên 32 byte chỉ trả một lần, database chỉ lưu SHA-256 hash; invitation chỉ cấp `member` hoặc `admin`; founder/co-founder/admin có thể issue/revoke; email phải khớp principal lúc accept; expiry mặc định 168 giờ; token single-use; retry sau accept trả membership hiện có mà không tạo bản ghi thứ hai.
- [ ] **Step 2: Thêm test contract hiện tại để chỉ ra lỗ hổng.** Trong `services/cosa/tests/control-plane.test.ts`, tạo user B và gọi `joinCompanyFor(userB, { company_id: workspaceId })`; assertion mong muốn sau migration là `APIError.permissionDenied`, trong khi implementation hiện tại tạo membership.
- [ ] **Step 3: Xác nhận test đỏ.** Chạy `cd services/cosa && npx vitest run tests/control-plane.test.ts`; expected: case mới fail vì join bằng ID đang thành công.
- [ ] **Step 4: Cập nhật README.** Thay mọi mô tả "join by company ID" bằng invitation flow; ghi rõ không có compatibility fallback cho client cũ khi endpoint bị đóng.
- [ ] **Step 5: Commit.** `git add docs/architecture/adr/ADR-WORKSPACE-INVITATION-001.md README.md services/cosa/tests/control-plane.test.ts && git commit -m "docs: define workspace invitation authority"`.

### Task 2: Thay public self-join bằng invitation có hạn và audit được

**Files:**
- Create: `services/cosa/migrations/34_workspace_invitations.up.sql`
- Create: `services/cosa/migrations/34_workspace_invitations.down.sql`
- Modify: `services/cosa/storage/schema.ts:1-110`
- Create: `services/cosa/services/workspace-invitation.service.ts`
- Modify: `services/cosa/services/company.service.ts:121-176`
- Modify: `services/cosa/handlers/company.handler.ts:1-65`
- Modify: `services/cosa/tests/control-plane.test.ts`
- Create: `services/cosa/tests/workspace-invitation.test.ts`

**Interfaces:**

```ts
export async function createWorkspaceInvitation(
  actorId: string,
  params: CreateWorkspaceInvitationParams,
): Promise<{ invitation_id: string; token: string; expires_at: string }>;

export async function acceptWorkspaceInvitation(
  actorId: string,
  params: AcceptWorkspaceInvitationParams,
): Promise<CompanyActionResponse>;
```

- [ ] **Step 1: Viết test đỏ ở service layer.** Bao phủ: user biết workspace ID không thể tạo membership; founder issue token cho đúng email; token sai principal bị `permissionDenied`; accept lần đầu tạo đúng một membership; accept song song chỉ có một insert; revoke/expiry từ chối; admin không issue founder role.
- [ ] **Step 2: Chạy test đỏ.** `cd services/cosa && npx vitest run tests/workspace-invitation.test.ts tests/control-plane.test.ts`; expected: self-join và invitation API chưa tồn tại.
- [ ] **Step 3: Thêm migration và schema.** Tạo `cosa.workspace_invitations` gồm Snowflake `id`, `workspace_id`, `email_normalized`, `role_id`, `token_hash`, `status`, `invited_by_user_id`, `expires_at`, `accepted_at`, `revoked_at`, `created_at`; unique index `(workspace_id, email_normalized)` chỉ khi `status='pending'`; không lưu raw token. Down migration chỉ drop table/index này.
- [ ] **Step 4: Implement transaction-safe service.** Sinh raw token qua `crypto.randomBytes(32).toString("base64url")`; hash bằng SHA-256; authorize issuer bằng membership role; accept dùng transaction `SELECT ... FOR UPDATE`, verify hash/expiry/email/status, insert membership với conflict-safe unique `(workspace_id,user_id)`, mark accepted và ghi audit event. Xóa `joinExistingCompany` hoặc đổi nó thành reject `APIError.permissionDenied("Workspace membership requires an invitation")`.
- [ ] **Step 5: Expose endpoint tối thiểu.** Giữ `POST /platform/auth/companies/invitations` và `POST /platform/auth/companies/invitations/accept` đều `auth: true`; bỏ `POST /platform/auth/companies/join` khỏi contract/frontend. Không trả invitation token khi list invitation.
- [ ] **Step 6: Chạy test xanh và gate Encore.** `cd services/cosa && npx vitest run tests/workspace-invitation.test.ts tests/control-plane.test.ts && npm run typecheck`; sau đó chạy `make encore-handler-boundary-check ts-suppression-check contract-freeze-check`.
- [ ] **Step 7: Commit.** `git add services/cosa && git commit -m "feat: require workspace invitations for membership"`.

### Task 3: Khóa workspace reads và command tài chính theo server authority

**Files:**
- Modify: `services/company/identity/handlers/workspace.handler.ts:18-27`
- Modify: `services/company/identity/services/command-authority.service.ts:1-34`
- Modify: `services/company/finance-legal/services/financial-transaction.service.ts:91-98`
- Modify: `services/company/finance-legal/handlers/financial-transaction.handler.ts:20-32`
- Modify: `services/company/identity/services/tenant-context.service.ts`
- Test: `services/company/identity/tests/workspace*.test.ts`
- Test: `services/company/finance-legal/tests/financial-transaction.test.ts`
- Test: `services/company/finance-legal/tests/tenant-isolation.test.ts`

**Interfaces:**

```ts
export async function requireFinancialTransactionWrite(
  authorization: string | undefined,
  workspaceId: string,
): Promise<TenantContext>;
```

- [ ] **Step 1: Viết test đỏ.** Gọi `GET /identity/workspaces/:id` bằng unauthenticated caller và member của workspace B; cả hai phải bị từ chối. Gọi record transaction bằng `auditor`/read-only member phải `permissionDenied`; founder hoặc role có explicit `finance.transaction.record` mới thành công.
- [ ] **Step 2: Chạy test đỏ.** `cd services/company && npx vitest run identity/tests finance-legal/tests/financial-transaction.test.ts finance-legal/tests/tenant-isolation.test.ts`; expected: public read và read-only financial write còn thành công.
- [ ] **Step 3: Chọn endpoint ownership qua caller inventory.** Nếu không có public client hợp lệ cho `getWorkspace`, chuyển route sang `expose: false`; nếu có, thêm `Authorization` header và `requireWorkspaceAccess` trước `getWorkspaceRecord`. Không giữ endpoint public chỉ vì frontend đang dùng direct URL string.
- [ ] **Step 4: Add explicit finance command.** Dùng `requireCommandAuthority(ctx, "finance.transaction.record", { workspaceId })` trong một helper `requireFinancialTransactionWrite`; gọi helper trước `getWorkspace` và transaction. Giữ approval threshold hiện hữu sau quyền command, không thay nó bằng role check ad-hoc.
- [ ] **Step 5: Chạy xanh và boundary gates.** Chạy lại test trên, `npm run typecheck`, `make company-boundary-check encore-handler-boundary-check ts-suppression-check frontend-api-contract-check`.
- [ ] **Step 6: Commit.** `git add services/company && git commit -m "fix: enforce workspace and financial write authority"`.

### Task 4: Áp requirement role khi quyết định agent approval

**Files:**
- Create: `apps/cosa/api/approval_authority.py`
- Modify: `apps/cosa/api/workforce_routes.py:879-925`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `packages/agent/capabilities/approval_service.py:170-229`
- Test: `tests/apps/cosa/test_workforce_routes.py`
- Test: `tests/apps/cosa/test_tenant_isolation.py`

**Interfaces:**

```python
class ApprovalAuthority(Protocol):
    async def allows(
        self, *, workspace_id: str, principal_id: str, requirement: dict[str, object]
    ) -> bool: ...

async def require_approval_authority(
    authority: ApprovalAuthority, identity: AuthenticatedIdentity, requirement: dict[str, object]
) -> None: ...
```

- [ ] **Step 1: Viết test đỏ.** Tạo approval scoped đúng workspace nhưng `requirement={"role": "founder"}`; member/admin không đủ role nhận 403 và approval vẫn `PENDING`; founder được approve; malformed/unknown role fail closed; concurrent legitimate decisions vẫn trả 409 cho request thứ hai.
- [ ] **Step 2: Chạy test đỏ.** `.venv/bin/python -m pytest tests/apps/cosa/test_workforce_routes.py tests/apps/cosa/test_tenant_isolation.py -q`; expected: member cùng workspace hiện có thể quyết định founder approval.
- [ ] **Step 3: Implement authority adapter.** Adapter gọi Company Identity tenant-context bằng delegation đúng chiều, nhận membership role server-signed; không đọc role từ body/header hoặc `approval.evidence`. Map `requirement.role` duy nhất với normalized membership role; requirement thiếu role dùng policy default documented trong ADR governance hiện hữu, không implicit allow.
- [ ] **Step 4: Guard trước side effect.** Trong `decide_approval`, gọi `require_approval_authority` ngay sau `get_scoped_approval` và trước `submit_decision`, emit runtime signal/SSE/metric. `ApprovalService` vẫn chỉ làm CAS persistence, không trở thành identity authority.
- [ ] **Step 5: Chạy test xanh và typecheck.** Chạy lại hai test, `make lint typecheck-py`, và test negative cross-workspace đã tồn tại.
- [ ] **Step 6: Commit.** `git add apps/cosa packages/agent tests/apps/cosa && git commit -m "fix: enforce approval reviewer requirements"`.

### Task 5: Biến cancel run thành durable state machine

**Files:**
- Modify: `packages/agent/runs/repository.py:25-95, 135-175, 447-485`
- Modify: `packages/agent/kernel/openai_agents_kernel.py:394-530, 690-710`
- Modify: `apps/cosa/api/routes.py:25-58`
- Test: `tests/agent/runs/test_run_repository.py`
- Test: `tests/apps/cosa/test_tenant_isolation.py`
- Create: `tests/agent/runs/test_cancel_complete_race_postgres.py`

**Interfaces:**

```python
async def cancel_run(self, run_id: str, *, reason: str) -> RunRecord | None: ...

async def transition_run_status(
    self, run_id: str, *, from_statuses: set[RunStatus], to_status: RunStatus,
    final_output: Any | None = None, error_details: dict[str, Any] | None = None,
) -> RunRecord | None: ...
```

- [ ] **Step 1: Viết test đỏ ở cả InMemory và Postgres repository.** `RUNNING → CANCELLED` thành công; cancel idempotent trả record `CANCELLED`; `CANCELLED → COMPLETED/FAILED/WAITING_APPROVAL` không đổi row; worker đọc cancel trước finalize trả `RunStatus.CANCELLED`; cross-process race cancel vs complete luôn kết thúc `CANCELLED`.
- [ ] **Step 2: Chạy test đỏ.** `.venv/bin/python -m pytest tests/agent/runs/test_run_repository.py tests/agent/runs/test_cancel_complete_race_postgres.py -q`; expected: generic `update_run_status` có thể ghi đè terminal cancel.
- [ ] **Step 3: Implement conditional transitions.** Postgres dùng một `UPDATE agent.runs ... WHERE run_id=:run_id AND status = ANY(:from_statuses) RETURNING ...`; `cancel_run` chỉ transition `PENDING/RUNNING/WAITING_APPROVAL` sang `CANCELLED`. InMemory áp dụng cùng table transition và lock. Không cần migration vì `status`, `error_details`, `completed_at` đã tồn tại.
- [ ] **Step 4: Replace kernel memory authority.** `_cancelled_runs` chỉ là fast-path local. Trước model/tool/final output, đọc persisted run hoặc gọi transition; mọi complete/fail/waiting transition chỉ chấp nhận trạng thái active. Nếu conditional update trả `None`, reload run và trả terminal status thực tế, không emit `run.completed`.
- [ ] **Step 5: Make HTTP cancel truthful.** Route chỉ emit `run.cancelled` khi `cancel_run` transition thành công; cancel đã terminal trả record/status hiện tại idempotently. Không gọi `plane.kernel.cancel` như authority duy nhất.
- [ ] **Step 6: Chạy test xanh.** Chạy ba test trên, `.venv/bin/python -m pytest tests/apps/cosa/test_tenant_isolation.py -q`, `make lint typecheck-py`.
- [ ] **Step 7: Commit.** `git add packages/agent apps/cosa tests && git commit -m "fix: persist terminal run cancellation"`.

### Task 6: Giữ Snowflake IDs là string từ UI đến Control Plane

**Files:**
- Modify: `frontend/lib/modules/auth/services/auth_service.dart:175-195, 310-335`
- Modify: `frontend/lib/modules/auth/controllers/auth_controller.dart:240-270`
- Modify: `services/cosa/services/company.service.ts`
- Modify: `services/cosa/handlers/company.handler.ts`
- Modify: `frontend/test/auth_flow_test.dart:200-230`
- Modify: `services/cosa/tests/control-plane.test.ts`

**Interfaces:**

```dart
Future<AuthResult> acceptWorkspaceInvitation({
  required String platformToken,
  required String invitationToken,
});
```

- [ ] **Step 1: Viết test đỏ transport.** Dùng ID `9223372036854775807`; test Flutter decode JSON request và assert `company_id` không xuất hiện như number; test Control Plane parse `company_id`/workspace ID qua `BigInt` only. Thêm test UI flow chỉ nhận invitation token, không render field "company ID".
- [ ] **Step 2: Chạy test đỏ.** `cd frontend && flutter test test/auth_flow_test.dart`; `cd services/cosa && npx vitest run tests/control-plane.test.ts`; expected: `int.tryParse` và payload number còn tồn tại.
- [ ] **Step 3: Implement string-only contract.** Bỏ `int.tryParse(companyId)` và payload `company_id`; accept endpoint nhận `token` opaque. Các response ID dùng `.toString()`; TypeScript DTO ID là `string`; parse DB boundary bằng `BigInt` với validation, không `Number`.
- [ ] **Step 4: Chạy xanh.** Chạy test trên, `flutter analyze --no-pub`, `make frontend-api-contract-check` và service typecheck.
- [ ] **Step 5: Commit.** `git add frontend services/cosa shared/contracts && git commit -m "fix: preserve Snowflake IDs in auth transport"`.

### Task 7: Làm gate lease tích hợp tái lập và độc lập máy dev

**Files:**
- Modify: `tests/e2e/stack/subprocess_stack.py:68-95`
- Modify: `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py:60-125`
- Modify: `tests/apps/cosa/worker/test_crash_recovery_subprocess.py:60-140`
- Create: `tests/apps/cosa/worker/conftest.py`
- Modify: `Makefile`

**Interfaces:**

```python
def asyncpg_test_url(url: str) -> str:
    """Change scheme to postgresql+asyncpg and remove libpq-only sslmode."""
```

- [ ] **Step 1: Viết test đỏ URL normalizer.** Input `postgresql://u:p@host/db?sslmode=disable&application_name=cosa` phải thành `postgresql+asyncpg://u:p@host/db?application_name=cosa`; credential/host/database giữ nguyên.
- [ ] **Step 2: Viết test red integration isolation.** Fixture phải spawn Control Plane trên port đã reserve, dùng `COSA_TEST_DATABASE_URL` của disposable cluster, health endpoint có run-id marker; test phải fail nếu một service cũ ở `:4000` trả health.
- [ ] **Step 3: Chạy test đỏ.** `.venv/bin/python -m pytest tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py -q`; expected: local port/credential mismatch hoặc asyncpg `sslmode` đang quyết định kết quả.
- [ ] **Step 4: Implement fixture ownership.** Di chuyển normalizer chung vào `tests/e2e/stack/subprocess_stack.py`; fixture tạo database/credential riêng, truyền đúng DSN cho Encore và SQLAlchemy, kiểm tra child PID + marker trước yield, terminate chỉ child process ở teardown. Không fallback sang `DATABASE_URL`, `.env` hoặc port cố định.
- [ ] **Step 5: Thêm Make target.** `make lease-integration-test` khởi tạo disposable dependencies, chạy three lease tests và in command chuẩn để CI dùng; không đưa test này vào unit target không có database.
- [ ] **Step 6: Chạy xanh.** `make lease-integration-test`; sau đó `make apps-cosa-test`. Mọi skip chỉ được chấp nhận khi target unit không yêu cầu PostgreSQL; lease target không được silently skip.
- [ ] **Step 7: Commit.** `git add tests/e2e tests/apps/cosa/worker Makefile && git commit -m "test: isolate durable lease integration"`.

### Task 8: Hoàn tất UX và kiểm thử Frontend còn rỗng

**Files:**
- Modify: `frontend/test/modules/workflows/inspector_test.dart`
- Modify: `frontend/test/modules/workflows/workflow_builder_test.dart`
- Modify: `frontend/test/modules/settings/workforce/profile_composition_test.dart`
- Modify: `frontend/test/modules/hologram_hub/provider_ui_test.dart`
- Modify: `frontend/test/modules/hologram_hub/hologram_projection_test.dart`
- Modify: `frontend/test/local_cache_test.dart`
- Modify: `frontend/lib/modules/chat/views/chat_view.dart`
- Modify: `frontend/lib/modules/chat/views/widgets/chat_composer.dart`

- [ ] **Step 1: Thay toàn bộ test body chỉ có comment placeholder bằng expectation có hành vi.** Với mỗi file, dùng tìm kiếm comment placeholder hoặc `expect(true` trong `frontend/test/modules` và `frontend/test/local_cache_test.dart` làm inventory; mỗi test phải assert state, render hoặc request observable. Xóa test name nếu feature chưa tồn tại thay vì giữ test xanh rỗng.
- [ ] **Step 2: Viết widget test chat red.** Mock `AgentChatApiException(503)` và assert composer hiển thị retry copy, message optimistic đã biến mất, spinner tắt và bấm retry gọi đúng content duy nhất một lần.
- [ ] **Step 3: Implement minimal retry UI.** Bind `sendBlockedReason` vào localized error surface; retain text in controller; retry gọi `sendMessage()` sau khi user chủ động bấm. Không auto-resubmit, không gửi attachment/retrieval.
- [ ] **Step 4: Chạy frontend tests.** `cd frontend && flutter test test/modules/chat/chat_module_test.dart test/auth_flow_test.dart`; sau đó `make frontend-test` và `make frontend-analyze`.
- [ ] **Step 5: Commit.** `git add frontend && git commit -m "test: replace no-op frontend coverage"`.

### Task 9: Release evidence, documentation, và cutover an toàn

**Files:**
- Modify: `README.md:172-255`
- Create: `docs/architecture/CODEBASE_HARDENING_2026-09-08.md`
- Modify: `.github/workflows/*` nếu CI chưa chạy gate mới

- [ ] **Step 1: Lập release evidence matrix.** Document phải có cột finding, commit, test negative, test integration, migration, rollback và trạng thái `IMPLEMENTED`/`WIRED`/`VERIFIED`; không dùng một nhãn "done" chung.
- [ ] **Step 2: Chạy migration preflight.** Xác minh số migration trước deploy; chạy `make dev-preflight`, migration lên disposable database, và ghi explicit rollback limitation: release rollback không drop invitation table khi dữ liệu đã được dùng.
- [ ] **Step 3: Chạy full targeted verification.** `make boundary-check company-boundary-check encore-handler-boundary-check ts-suppression-check frontend-api-contract-check route-auth-allowlist-check skillpacks-validate contract-freeze-check`; `make services-test`; `make agent-test`; `make apps-cosa-test`; `make frontend-test`; `make frontend-analyze`; `make lease-integration-test`; `make e2e-cross-plane-smoke`.
- [ ] **Step 4: Review diff và public route inventory.** Rà từng `expose: true`, confirm join endpoint removed from `shared/contracts/mvp-surface.json`, verify no frontend string route references endpoint cũ và run `git diff --check`.
- [ ] **Step 5: Update README only with proven state.** Mark invitation, role enforcement, cancellation and Snowflake contract as implemented chỉ sau các test trên; nếu bất kỳ integration gate fail, ghi exact dependency/môi trường và giữ release blocked.
- [ ] **Step 6: Commit.** `git add README.md docs/architecture .github && git commit -m "docs: record platform hardening evidence"`.

## Dependency order

`Task 1 → Task 2 → Task 6` đóng membership authority và frontend contract. `Task 3`, `Task 4`, và `Task 5` độc lập sau Task 1; chúng có thể review song song nhưng không merge song song vào cùng working tree. `Task 7` chạy sau Task 5 để chứng minh durability. `Task 8` có thể làm sau Task 6. `Task 9` chỉ bắt đầu khi mọi task trước có commit và test xanh.

## Self-review

- **Coverage:** Plan bao phủ membership takeover, workspace read, finance write, approval role, cancellation durability, Snowflake precision, no-op frontend tests, và lease integration DSN/credential isolation.
- **Authority:** Không có task nào dựa trên client-provided role/workspace như nguồn truth; invitation, financial write và approval đều có server-side guard.
- **Durability:** Cancellation được kiểm chứng trên Postgres/process thật, không chỉ kernel instance hoặc mock.
- **Migration safety:** Invitation là migration expand-only; không có destructive contract migration trong release này.
- **Known prerequisite:** Task 1 cần product owner xác nhận các default được ghi trong ADR. Nếu muốn allow domain-wide invitation, multi-use link hoặc founder delegation, phải sửa ADR và các test của Task 2 trước khi implementation.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-08-platform-authority-durability-hardening.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.
