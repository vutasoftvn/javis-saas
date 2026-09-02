# Frontend Trust and UX Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm frontend Flutter an toàn và đáng tin cậy trước khi mở rộng tính năng: bảo vệ token, quản lý workspace/runtime nguyên tử, hiển thị đúng trạng thái API, hoàn thiện Remote Access, và chuyển navigation/UI sang một app shell có thể bảo trì.

**Architecture:** Session là authority phía client duy nhất cho credential đã xác thực, workspace, role và runtime snapshot. `ApiClient` chịu trách nhiệm transport/routing; feature service trả `ApiResult<T>` và feature controller chuyển nó thành `AsyncFeatureState<T>` để view không bao giờ diễn giải lỗi thành empty state. Thực hiện theo lát dọc và giữ các route legacy như redirect tạm thời, không big-bang rewrite 72 service.

**Tech Stack:** Flutter/Dart, GetX, `flutter_secure_storage`, `shared_preferences`, `http`, SSE; Encore.ts/TypeScript và contracts JSON cho một platform session-context adapter; Flutter test, pytest/Node quality checks, GitHub Actions.

**Spec:** [`docs/superpowers/specs/2026-09-02-frontend-trust-and-ux-design.md`](../specs/2026-09-02-frontend-trust-and-ux-design.md)

## Global Constraints

- Không ghi, đọc, xóa hoặc migrate `local_session_token`, `platform_access_token` hay `auth_token` qua `SharedPreferences` khi native secure storage báo lỗi.
- Backend là source of truth cho membership, workspace, role, runtime mode, presence và capability. Không dùng field picker hoặc argument route như assertion bảo mật.
- `REMOTE_ACCESS` với node `OFFLINE` không được gửi business request và không được fallback cloud.
- Không tạo `catch` mới trả `[]`, `null` hoặc `false` cho lỗi network/HTTP/parse. Mọi failure phải giữ code/message đủ để UI biểu đạt đúng.
- Không sửa trực tiếp generated contract. Sửa source contract rồi chạy generator chuẩn của repo.
- Không đụng hoặc ghi đè file đang dirty: `scripts/check_frontend_api_contracts.mjs`, `tests/quality/test_frontend_api_contracts.py`, `package-lock.json`, các file dưới `docs/superpowers/` đã tồn tại. Rebase/trao đổi với owner trước nếu một task thực sự cần chúng.
- Chỉ commit khi test/gate của task đã pass; một task một commit, không bao gồm thay đổi không liên quan.

## Workstreams và thứ tự

| Thứ tự | Workstream | Deliverable độc lập |
|---:|---|---|
| 1 | Baseline và secret storage | Token fail closed, bộ test phản ánh đúng production/test boundary |
| 2 | Session + runtime authority | Login/switch/logout transaction và Remote Access được wire end-to-end |
| 3 | Truthful data + transport | Approvals/Agents không false-empty, endpoint legacy được xử lý có owner |
| 4 | Realtime + lifecycle | SSE có checkpoint/reconcile, Hub không chạy sau auth fail |
| 5 | Navigation + UX | App shell, URL canonical, responsive/i18n/a11y nhất quán |
| 6 | Release confidence | Contract, integration, golden/a11y và CI gates có bằng chứng |

## File map chính

| Vùng | File hiện có | Trách nhiệm sau thay đổi |
|---|---|---|
| Secret storage | `frontend/lib/core/services/secure_storage_service.dart` | Wrapper token fail-closed, fake injectable chỉ cho test. |
| Session | `frontend/lib/modules/auth/services/auth_service.dart`, `frontend/lib/modules/workspace_picker/controllers/workspace_picker_controller.dart` | Nạp và activate workspace có rollback. |
| Runtime | `frontend/lib/modules/remote_access/**`, `frontend/lib/core/network/api_client.dart` | Snapshot server-authoritative, relay/offline/banner/mutation gate. |
| State | `frontend/lib/features/_shared/presentation/async_feature_state.dart`, `frontend/lib/core/network/api_result.dart` | Một chuẩn biểu đạt loading/data/empty/failure. |
| Approval | `frontend/lib/modules/approvals/{services,controllers,views}` | Lát dọc đầu tiên dùng typed failure, retry và mutation gate. |
| Realtime | `frontend/lib/core/network/realtime_service.dart` | Parser SSE chuẩn, workspace checkpoint và lifecycle rõ. |
| Shell | `frontend/lib/modules/dashboard/**`, `frontend/lib/core/routing/**` | Route canonical thay switch index; UI chrome duy nhất. |

---

### Task 1: Khóa baseline, phân loại 5 test đỏ và tạo quality entry-point cho frontend

**Files:**
- Modify: `frontend/test/core/services/secure_storage_service_test.dart`
- Modify: `frontend/test/modules/workspace_picker/workspace_picker_controller_test.dart`
- Modify: `frontend/test/modules/strategy/controllers/mixins/governance_state_mixin_test.dart`
- Modify: `Makefile` — chỉ sau khi owner thay đổi dirty đã được reconcile.
- Create: `frontend/tool/run_quality.sh` nếu repo chưa có entry-point tương đương.

**Interfaces:**
- Consumes: full `flutter test` baseline hiện có.
- Produces: một lệnh chất lượng chuẩn chạy `flutter analyze`, selected security/session tests, contract script và full `flutter test`; test picker/governance phản ánh contract hiện hữu thay vì fixture mâu thuẫn.

- [ ] **Step 1: Chụp baseline không làm thay đổi source.**

Run:

```bash
cd frontend && flutter analyze && flutter test -r compact
cd .. && node scripts/check_frontend_api_contracts.mjs
```

Lưu danh sách fail có tên test, không sửa theo kiểu xóa assertion. Baseline hiện kỳ vọng: analyzer pass; ba fail secure-storage là contract security; picker có assertion tự mâu thuẫn ở early-return; governance mock trả `items` trong khi service decode `stages`.

- [ ] **Step 2: Sửa hai fixture test không đại diện production.**

Trong test picker, giữ case token rỗng là `isLoading == false`, rồi thêm fake `AuthService` injectable trả `Completer<bool>` để kiểm chứng loading chỉ chuyển `true` khi request hợp lệ đang pending. Trong test governance, đổi response mock thành:

```dart
http.Response(jsonEncode({
  'stages': [{'id': 'stage-1', 'name': 'Discovery'}],
}), 200)
```

Không sửa service để hiểu đồng thời `items` chỉ để làm xanh fixture cũ.

- [ ] **Step 3: Viết script quality không chạm Makefile dirty.**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
flutter analyze
flutter test test/core/services/secure_storage_service_test.dart -r compact
flutter test test/modules/workspace_picker/workspace_picker_controller_test.dart -r compact
flutter test -r compact
cd ..
node scripts/check_frontend_api_contracts.mjs
```

Chỉ thêm `make frontend-quality` và CI step sau khi owner của Makefile/contract checker xác nhận merge strategy; không overwrite local diff.

- [ ] **Step 4: Chạy selected tests trước, rồi full baseline.**

Run:

```bash
cd frontend && flutter test \
  test/modules/workspace_picker/workspace_picker_controller_test.dart \
  test/modules/strategy/controllers/mixins/governance_state_mixin_test.dart -r compact
```

Expected: picker và governance pass; ba test storage vẫn fail cho đến Task 2, vì chúng bảo vệ contract mong muốn.

- [ ] **Step 5: Commit baseline-only change.**

```bash
git add frontend/test/modules/workspace_picker/workspace_picker_controller_test.dart \
  frontend/test/modules/strategy/controllers/mixins/governance_state_mixin_test.dart \
  frontend/tool/run_quality.sh
git commit -m "test(frontend): align session and governance fixtures with contracts"
```

---

### Task 2: Thay plaintext fallback token bằng secret store fail-closed có test double

**Files:**
- Create: `frontend/lib/core/services/secret_store.dart`
- Modify: `frontend/lib/core/services/secure_storage_service.dart`
- Modify: `frontend/test/core/services/secure_storage_service_test.dart`
- Create: `frontend/test/core/services/fakes/fake_secret_store.dart`
- Modify: callers của `SecureStorageService.migrateFromSharedPreferences()` nếu cần phân loại key cache/secret.

**Interfaces:**

```dart
abstract interface class SecretStore {
  Future<void> write(String key, String value);
  Future<String?> read(String key);
  Future<void> delete(String key);
}

abstract interface class KeyClassifier {
  bool isSecret(String key);
}
```

`SecureStorageService.configureForTest(SecretStore store)` chỉ được annotated `@visibleForTesting`; `resetForTest()` phải khôi phục `FlutterSecureSecretStore`. Với secret key, `PlatformException` luôn propagate; không có code path sang `SharedPreferences`.

- [ ] **Step 1: Viết test đỏ cho ranh giới bảo mật.**

```dart
test('secret write propagates a Keychain failure and leaves preferences empty', () async {
  SecureStorageService.configureForTest(ThrowingSecretStore());
  await expectLater(
    SecureStorageService.write(SecureStorageService.localSessionTokenKey, 'jwt'),
    throwsA(isA<PlatformException>()),
  );
  expect((await SharedPreferences.getInstance()).containsKey(
    SecureStorageService.localSessionTokenKey,
  ), isFalse);
});
```

Thêm tương ứng cho read/delete/migrate. Thêm test fake in-memory để chứng minh widget test không cần MethodChannel hoặc `_isWidgetTest` heuristic.

- [ ] **Step 2: Chạy test xác nhận implementation hiện tại không an toàn.**

Run:

```bash
cd frontend && flutter test test/core/services/secure_storage_service_test.dart -r compact
```

Expected: fail ở code hiện tại vì mọi `PlatformException` bị coi recoverable hoặc widget test đi thẳng SharedPreferences.

- [ ] **Step 3: Implement secure adapter và key classification tối thiểu.**

```dart
const secretKeys = <String>{
  'auth_token',
  'local_session_token',
  'platform_access_token',
};

static Future<void> write(String key, String value) async {
  if (_classifier.isSecret(key)) return _secretStore.write(key, value);
  return _cacheStore.write(key, value);
}
```

Không catch `PlatformException` cho `secretKeys`. `workspace_id` và `role` chuyển sang named session-cache key; quyết định storage của chúng phải được ghi comment/document theo threat model. Migration đọc legacy plaintext **chỉ** để thử secure write; chỉ xóa legacy sau write success.

- [ ] **Step 4: Chạy security suite và auth boundary suite.**

Run:

```bash
cd frontend && flutter test \
  test/core/services/secure_storage_service_test.dart \
  test/auth_flow_test.dart \
  test/core/network/api_client_token_boundary_test.dart -r compact
```

Expected: pass. Kiểm tra log không in token hoặc exception chứa token.

- [ ] **Step 5: Commit.**

```bash
git add frontend/lib/core/services/secret_store.dart \
  frontend/lib/core/services/secure_storage_service.dart \
  frontend/test/core/services
git commit -m "fix(frontend): fail closed when secure token storage is unavailable"
```

---

### Task 3: Cung cấp platform session-context server-authoritative cho workspace/runtime

**Files:**
- Modify: `services/cosa/handlers/workspace-settings.handler.ts`
- Modify: `services/cosa/services/workspace-settings.service.ts`
- Modify: `shared/contracts/mvp-surface.json`
- Regenerate: `apps/cosa/api/mvp_contracts_generated.py`, `frontend/lib/core/network/mvp_endpoints.g.dart`
- Create: test gần handler hiện có, ví dụ `services/cosa/handlers/workspace-settings.handler.test.ts`
- Create: `tests/integration/test_platform_workspace_session_context.py` nếu integration harness hiện dùng Python.

**Interfaces:**

```ts
interface WorkspaceSessionContextView {
  workspaceId: string;
  role: string;
  runtimeMode: 'LOCAL_ONLY' | 'REMOTE_ACCESS' | 'CLOUD_CONTINUITY';
  presenceStatus: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  lastHeartbeatAt: string | null;
  asOf: string;
  capabilities: readonly string[];
}
// GET /platform/workspaces/:workspaceId/session-context
```

Handler lấy identity từ auth context, kiểm tra membership và đọc runtime mode từ canonical workspace record; presence được recompute từ heartbeat/lease server-side. Không nhận `runtimeMode`, `role`, `presence` trong request body/query.

- [ ] **Step 1: Viết backend tests trước.**

```ts
it('returns only the authenticated member workspace session context', async () => {
  const response = await callAs(memberA, '/platform/workspaces/ws-a/session-context');
  expect(response.workspaceId).toBe('ws-a');
  expect(response.role).toBe('MEMBER');
  expect(response.asOf).toMatch(/Z$/);
});

it('denies a member of another workspace', async () => {
  await expect(callAs(memberA, '/platform/workspaces/ws-b/session-context'))
    .rejects.toMatchObject({ code: 'permission-denied' });
});
```

Thêm case runtime offline: response `REMOTE_ACCESS/OFFLINE`, không cloud target ngầm.

- [ ] **Step 2: Chạy test để xác nhận endpoint chưa tồn tại.**

Run: `cd services/cosa && pnpm test workspace-settings.handler.test.ts`

Expected: fail do route/service chưa export.

- [ ] **Step 3: Implement DTO, service và contract.**

Đặt endpoint cạnh runtime-nodes/settings platform endpoints. `asOf` lấy clock server. Dùng cùng membership resolver đang dùng cho entitlement/settings; không tự parse Authorization khác chuẩn. Thêm endpoint vào `mvp-surface.json`, chạy generator chuẩn:

```bash
node scripts/gen-mvp-contracts.mjs
```

- [ ] **Step 4: Chạy service, integration và contract gate.**

Run:

```bash
cd services/cosa && pnpm test workspace-settings.handler.test.ts
cd ../.. && pytest tests/integration/test_platform_workspace_session_context.py -q
node scripts/check_frontend_api_contracts.mjs
```

Expected: pass, generated output chỉ chứa endpoint/schema mới.

- [ ] **Step 5: Commit.**

```bash
git add services/cosa/handlers/workspace-settings.handler.ts \
  services/cosa/services/workspace-settings.service.ts shared/contracts/mvp-surface.json \
  apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart \
  services/cosa tests/integration
git commit -m "feat(platform): expose verified workspace session context"
```

---

### Task 4: Đưa login, switch workspace và logout vào một SessionController transaction

**Files:**
- Create: `frontend/lib/core/session/session_snapshot.dart`
- Create: `frontend/lib/core/session/session_controller.dart`
- Create: `frontend/lib/core/session/session_binding.dart`
- Create: `frontend/lib/core/session/session_context_service.dart`
- Modify: `frontend/lib/modules/auth/services/auth_service.dart`
- Modify: `frontend/lib/modules/auth/controllers/auth_controller.dart`
- Modify: `frontend/lib/modules/workspace_picker/controllers/workspace_picker_controller.dart`
- Modify: `frontend/lib/core/routing/auth_middleware.dart`, `frontend/lib/core/routing/app_pages.dart`, `frontend/lib/main.dart`
- Create: `frontend/test/core/session/session_controller_test.dart`
- Modify: `frontend/test/modules/workspace_picker/workspace_picker_controller_test.dart`, `frontend/test/auth_flow_test.dart`

**Interfaces:**

```dart
final class SessionSnapshot {
  const SessionSnapshot({
    required this.userId,
    required this.workspaceId,
    required this.role,
    required this.runtime,
    required this.capabilities,
  });
}

abstract interface class SessionContextService {
  Future<SessionSnapshot> fetch(String workspaceId);
}

class SessionController extends GetxController {
  final Rxn<SessionSnapshot> active = Rxn<SessionSnapshot>();
  Future<SessionActivationResult> activateWorkspace(String workspaceId);
  Future<void> logout();
}
```

`AuthService.finishAuthenticationForWorkspace` không được tự trả `true` khi `getMe()` null. Nó trả typed `AuthResult`; `SessionController` mới commit state/cache/navigation after all network checks pass.

- [ ] **Step 1: Viết tests transaction và rollback.**

```dart
test('does not replace the active workspace when verified context fails', () async {
  final session = SessionController(contextService: FailingContextService());
  session.seedForTest(snapshotFor('workspace-a'));
  final result = await session.activateWorkspace('workspace-b');
  expect(result.isSuccess, isFalse);
  expect(session.active.value!.workspaceId, 'workspace-a');
});

test('logout clears tokens, runtime and realtime before routing to login', () async {
  await session.logout();
  expect(session.active.value, isNull);
  expect(ApiClient.runtimeMode, isNull);
  expect(fakeRealtime.stopCalls, 1);
});
```

Thêm test `finishAuthenticationForWorkspace` trả false khi `/identity/me` là 401/500 hoặc không trả workspace đúng target.

- [ ] **Step 2: Chạy test và xác nhận lỗi hiện tại.**

Run:

```bash
cd frontend && flutter test \
  test/core/session/session_controller_test.dart \
  test/auth_flow_test.dart \
  test/modules/workspace_picker/workspace_picker_controller_test.dart -r compact
```

Expected: fail trước khi SessionController và typed AuthResult tồn tại.

- [ ] **Step 3: Implement activation theo thứ tự không thể đảo.**

```dart
final me = await _authService.getMeForWorkspace(workspaceId);
if (me == null || me.workspaceId != workspaceId) return SessionActivationResult.failure(...);
final snapshot = await _sessionContext.fetch(workspaceId);
if (snapshot.workspaceId != workspaceId) return SessionActivationResult.failure(...);
await _commit(snapshot); // cache non-secret metadata only after both checks
_realtime.restartFor(snapshot.workspaceId);
return SessionActivationResult.success(snapshot);
```

`_commit` cập nhật SessionController, RemoteAccess context, cached workspace/role và `ApiClient` cùng một critical section. `logout` gọi theo thứ tự: stop realtime → clear ApiClient runtime → clear memory → delete secret keys → remove cache keys → route login.

- [ ] **Step 4: Wire picker và middleware.**

Picker inject `SessionController`, set loading chỉ sau token valid, gọi `activateWorkspace`, và chỉ `Get.offAllNamed(AppRoutes.hub)` khi success. `workspacePicker` có AuthMiddleware; khi route argument thiếu/stale thì quay login hoặc session workspace list, không render picker chết. `main.dart` bootstrap SessionController rồi chọn Hub/Login dựa `active`, không chỉ `AuthService.isAuthenticated` cache.

- [ ] **Step 5: Chạy session regression.**

Run:

```bash
cd frontend && flutter test \
  test/core/session/session_controller_test.dart \
  test/auth_flow_test.dart \
  test/modules/workspace_picker/workspace_picker_controller_test.dart \
  test/core/network/api_client_token_boundary_test.dart -r compact
flutter analyze
```

Expected: pass; không warning GetX lifecycle mới.

- [ ] **Step 6: Commit.**

```bash
git add frontend/lib/core/session frontend/lib/modules/auth frontend/lib/modules/workspace_picker \
  frontend/lib/core/routing frontend/lib/main.dart frontend/test/core/session \
  frontend/test/auth_flow_test.dart frontend/test/modules/workspace_picker
git commit -m "fix(frontend): activate workspace through verified session transaction"
```

---

### Task 5: Wire Remote Access vào session, app shell và mutation gate

**Files:**
- Modify: `frontend/lib/modules/remote_access/controllers/remote_access_controller.dart`
- Create: `frontend/lib/core/runtime/mutation_gate.dart`
- Create: `frontend/lib/core/widgets/runtime_app_chrome.dart`
- Modify: `frontend/lib/core/network/api_client.dart`
- Modify: `frontend/lib/modules/dashboard/views/dashboard_view.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Modify: representative mutation surfaces under Approvals, Tasks and Workflows.
- Create/modify: `frontend/test/core/runtime/mutation_gate_test.dart`, `frontend/test/core/network/api_client_runtime_route_test.dart`, `frontend/test/core/widgets/runtime_app_chrome_test.dart`

**Interfaces:**

```dart
enum MutationPermission { allowed, confirmDegraded, blockedOffline, blockedReadOnly }

abstract interface class MutationGate {
  MutationPermission check({required bool isMutation});
}
```

The gate reads `SessionController.active.runtime`; it does not read individual UI toggles. `RemoteAccessBanner` appears once in `RuntimeAppChrome`, above all shell body content.

- [ ] **Step 1: Write failing UI/routing tests.**

```dart
test('remote offline blocks a business POST before HTTP', () async {
  seedSession(mode: RuntimeMode.remoteAccess, presence: NodePresence.offline);
  final result = gate.check(isMutation: true);
  expect(result, MutationPermission.blockedOffline);
  expect(recordingClient.requests, isEmpty);
});

testWidgets('shell displays stale read-only banner for remote offline workspace', (tester) async {
  await tester.pumpWidget(appWithRuntime(remoteOfflineStatus));
  expect(find.textContaining('chỉ đọc'), findsOneWidget);
  expect(find.textContaining('Dữ liệu tính đến'), findsOneWidget);
});
```

- [ ] **Step 2: Implement one runtime authority.**

`RemoteAccessController` receives snapshot only from `SessionController`; remove calls that apply picker JSON directly. `ApiClient.setRuntimeContext` executes only during session commit and clears in logout/rollback. Keep `/platform`, `/agent`, `/local-worker` routing behavior explicitly covered by tests; business endpoint in remote/offline returns synthetic 503 without calling `http.Client`.

- [ ] **Step 3: Install shell banner and reusable action guard.**

Wrap Dashboard and standalone Hub with `RuntimeAppChrome`. Use `MutationGate` in Approval decision, task status mutation and workflow execution before service call. For `confirmDegraded`, dialog names the runtime condition and requires user confirmation; for offline/read-only, disable control and render explanatory tooltip, not an error toast after click.

- [ ] **Step 4: Run remote matrix tests.**

Run:

```bash
cd frontend && flutter test \
  test/core/runtime/mutation_gate_test.dart \
  test/core/network/api_client_runtime_route_test.dart \
  test/core/widgets/runtime_app_chrome_test.dart -r compact
```

Expected: local online, remote online, remote degraded and remote offline all have deterministic route/UI/mutation behavior.

- [ ] **Step 5: Commit.**

```bash
git add frontend/lib/modules/remote_access frontend/lib/core/runtime frontend/lib/core/widgets \
  frontend/lib/core/network/api_client.dart frontend/lib/modules/dashboard \
  frontend/lib/modules/hologram_hub frontend/lib/modules/approvals frontend/lib/modules/tasks \
  frontend/lib/modules/workflows frontend/test/core
git commit -m "feat(frontend): enforce runtime context in shell and mutations"
```

---

### Task 6: Chuẩn hóa truthful async state qua Approvals làm lát dọc đầu tiên

**Files:**
- Modify: `frontend/lib/features/_shared/presentation/async_feature_state.dart`
- Create: `frontend/lib/features/_shared/presentation/feature_state_view.dart`
- Modify: `frontend/lib/modules/approvals/services/approvals_service.dart`
- Modify: `frontend/lib/modules/approvals/controllers/approvals_controller.dart`
- Modify: `frontend/lib/modules/approvals/views/approvals_view.dart`
- Modify/Create: `frontend/test/modules/approvals/{approvals_service_test.dart,approvals_controller_test.dart,approvals_view_test.dart}`

**Interfaces:**

```dart
typedef ApprovalListState = AsyncFeatureState<List<ApprovalItemModel>>;

class ApprovalsService {
  Future<ApiResult<List<ApprovalItemModel>>> list({String? status});
  Future<ApiResult<ApprovalItemModel>> decide(
    String approvalId, {required bool approved, String? reason},
  );
}
```

Reuse `FeatureInitial`, `FeatureLoading`, `FeatureData`, `FeatureFailure`, `FeatureNotObserved` already in the repository; add a `FeatureEmpty` only if a successful empty collection cannot be represented without ambiguity. Do not introduce a second parallel async model.

- [ ] **Step 1: Write service and view tests for false-empty prevention.**

```dart
test('maps HTTP 503 to ApiFailure instead of an empty approval list', () async {
  final result = await service.list();
  expect(result, isA<ApiFailure<List<ApprovalItemModel>>>());
});

testWidgets('renders retryable unavailable state instead of success empty copy', (tester) async {
  await tester.pumpWidget(viewFor(FeatureFailure(unavailableFailure)));
  expect(find.textContaining('Không thể tải'), findsOneWidget);
  expect(find.text('Thử lại'), findsOneWidget);
  expect(find.textContaining('Tuyệt vời!'), findsNothing);
});
```

Cover 401/403, network timeout, malformed body, success empty, success list, decision failure and stale data while refresh fails.

- [ ] **Step 2: Run test and verify current false-empty failure.**

Run: `cd frontend && flutter test test/modules/approvals -r compact`

Expected: new 503 UI test fails because `ApprovalsService` returns `[]`.

- [ ] **Step 3: Implement typed decode and state transitions.**

`ApprovalsService` checks status code, validates `items` schema, maps transport/parse failures into existing `ApiFailureDetail`. Controller owns `Rx<ApprovalListState>`, preserves prior `FeatureData` while a refresh is in flight, and calls retry through the state view. `approve/reject` receives `ApiResult`, only shows success after a successful response and refreshes authoritative list.

- [ ] **Step 4: Run approval suite and nearby realtime behavior.**

Run:

```bash
cd frontend && flutter test test/modules/approvals test/features/shared/async_feature_state_test.dart -r compact
flutter analyze
```

Expected: pass; 200 empty is the only path that shows the celebratory empty UI.

- [ ] **Step 5: Commit.**

```bash
git add frontend/lib/features/_shared/presentation frontend/lib/modules/approvals \
  frontend/test/modules/approvals frontend/test/features/shared
git commit -m "fix(approvals): distinguish unavailable data from an empty queue"
```

---

### Task 7: Reconcile legacy API consumers and make contract drift visible

**Files:**
- Modify: `frontend/lib/modules/agents/services/agent_platform_service.dart`
- Modify: `frontend/lib/modules/agents/services/agents_service.dart`
- Modify: `frontend/lib/modules/marketing/services/marketing_service.dart` only for endpoints selected from inventory with verified replacements.
- Modify: `shared/contracts/mvp-surface.json` when canonical frontend endpoint lacks an inventory record.
- Modify: `scripts/frontend-api-contract-allowlist.json` only after owner approval.
- Create: `docs/architecture/frontend-api-migration-register.md`
- Modify/Create: `frontend/test/modules/agents/*_service_test.dart`, `tests/quality/test_frontend_api_contracts.py` only after reconciling dirty owner changes.

**Interfaces:**
- Consumes: generated route inventory and contract checker.
- Produces: an owned migration register with endpoint, consumer, canonical replacement, rollout status and expiry; no active Agents approval request remains on raw `/workforce/approvals` when canonical `/agent/approvals` is available.

- [ ] **Step 1: Generate and triage route inventory instead of bulk-rewriting.**

Run:

```bash
python scripts/route_inventory.py
rg -n "✗ GHOST" docs/architecture/generated/route-inventory.md
```

Create a register row for every active route visible from Dashboard, not every historical unused file. Classify each as `canonical`, `migration-needed`, `intentionally-unsupported`, or `unknown`. `unknown` blocks release for a user-visible mutation.

- [ ] **Step 2: Write the first Agent contract tests.**

```dart
test('lists approvals through the canonical Agent endpoint', () async {
  final result = await service.listApprovals();
  expect(recordedRequest.url.path, '/agent/approvals');
  expect(result, isA<ApiSuccess<List<WorkforceApproval>>>());
});

test('does not turn a 404 legacy workforce response into an empty list', () async {
  expect(await service.listApprovals(), isA<ApiFailure<List<WorkforceApproval>>>());
});
```

- [ ] **Step 3: Migrate one domain at a time.**

Move Agent approvals/runs/composition consumers to `WorkforceMvpService` or one typed service, delete only dead raw methods proven unused by `rg` plus tests. Repeat for Marketing only after its backend contract is verified. Do not map arbitrary `/marketing/*` in `ApiClient.normalizeEndpoint` as a shortcut.

- [ ] **Step 4: Add allowlist expiry discipline.**

Every remaining allowlist entry contains owner, reason, canonical target, expiry date and a test reference. Checker fails expired entries and reports count. This change waits until the currently dirty checker files are reconciled with their owner.

- [ ] **Step 5: Verify active-dashboard routes and commit domain slices.**

Run per domain:

```bash
cd frontend && flutter test test/modules/agents -r compact
cd .. && node scripts/check_frontend_api_contracts.mjs
```

Commit one domain at a time, e.g. `refactor(agents): use canonical workforce contracts`; do not combine route inventory regeneration with unrelated endpoint change.

---

### Task 8: Làm SSE parser/lifecycle recoverable theo workspace

**Files:**
- Modify: `frontend/lib/core/network/realtime_service.dart`
- Modify: `frontend/lib/core/network/api_client.dart` nếu `openSse` cần `Last-Event-ID` headers.
- Modify: `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart`
- Modify: `frontend/lib/modules/approvals/controllers/approvals_controller.dart`
- Create: `frontend/test/core/network/realtime_service_test.dart`
- Modify: Hologram/Approvals controller tests.

**Interfaces:**

```dart
final class RealtimeEnvelope {
  const RealtimeEnvelope({required this.event, required this.data, this.id});
  final String event;
  final Map<String, dynamic> data;
  final String? id;
}

abstract interface class RealtimeService {
  Future<void> connectForWorkspace(String workspaceId);
  void stop({bool clearCheckpoint = false});
  void addListener(void Function(RealtimeEnvelope event) listener);
}
```

- [ ] **Step 1: Write parser tests from raw SSE frames.**

```dart
test('joins multiline data and dispatches only on a blank line', () {
  final events = parseSse('id: 42\nevent: approval.updated\ndata: {"id":\ndata: "a1"}\n\n');
  expect(events.single.id, '42');
  expect(events.single.event, 'approval.updated');
  expect(events.single.data['id'], 'a1');
});

test('reconnect sends the last event id only for the same workspace', () async {
  await service.connectForWorkspace('a');
  service.acceptForTest(envelope(id: '42'));
  await service.reconnectForTest();
  expect(client.lastEventId, '42');
  await service.connectForWorkspace('b');
  expect(client.lastEventId, isNull);
});
```

- [ ] **Step 2: Run test and confirm old parser dispatches every `data:` line.**

Run: `cd frontend && flutter test test/core/network/realtime_service_test.dart -r compact`

Expected: fail before parser state machine exists.

- [ ] **Step 3: Implement frame state machine and reconnect policy.**

Accumulate `event`, `id` and `List<String> dataLines`; on blank line join data with `\n`, JSON decode once and dispatch. Send `Last-Event-ID` only for active workspace. Use exponential backoff plus jitter bounded 2–30 seconds. A 401/403 ends reconnect and asks SessionController to refresh/logout; a 5xx/network reconnects.

- [ ] **Step 4: Wire session lifecycle and feature reconciliation.**

Session commit calls `connectForWorkspace`; rollback/logout calls `stop(clearCheckpoint: true)`. `HologramHubController` first checks an active SessionSnapshot before loading/timers/stream. Events trigger debounced authoritative reload for their feature; they do not assume event payload is full state.

- [ ] **Step 5: Run transport and controller tests; commit.**

```bash
cd frontend && flutter test \
  test/core/network/realtime_service_test.dart \
  test/modules/approvals \
  test/modules/hologram_hub -r compact
git add frontend/lib/core/network frontend/lib/modules/hologram_hub frontend/lib/modules/approvals frontend/test
git commit -m "fix(frontend): scope realtime recovery to the active workspace"
```

---

### Task 9: Thay dashboard index authority bằng AppShell route canonical

**Files:**
- Create: `frontend/lib/core/shell/app_shell.dart`
- Create: `frontend/lib/core/shell/app_shell_controller.dart`
- Create: `frontend/lib/core/routing/module_routes.dart`
- Modify: `frontend/lib/core/routing/app_routes.dart`, `frontend/lib/core/routing/app_pages.dart`
- Modify: `frontend/lib/modules/dashboard/views/dashboard_view.dart`
- Modify: `frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart`
- Modify: `frontend/lib/modules/dashboard/views/widgets/dashboard_content_body.dart`
- Modify: `frontend/lib/modules/dashboard/bindings/dashboard_binding.dart`
- Create: `frontend/test/core/routing/module_routes_test.dart`, `frontend/test/core/shell/app_shell_test.dart`

**Interfaces:**

```dart
enum WorkspaceModule { hub, tasks, approvals, strategy, agents, vault, sales, marketing, finance, legal, workflows, settings }

extension WorkspaceModuleRoute on WorkspaceModule {
  String get path; // e.g. /work/tasks
}
```

`AppShell` owns chrome only; each module route owns its page/binding. Sidebar calls `Get.toNamed(module.path)` rather than `changePage(index)`. `/dashboard` redirects to `/hub`; legacy direct routes redirect to canonical paths until references are removed.

- [ ] **Step 1: Write routing and back-stack widget tests.**

```dart
test('every sidebar module has one canonical guarded path', () {
  expect(WorkspaceModule.tasks.path, '/work/tasks');
  expect(routesFor('/work/tasks').single.middlewares, contains(isA<AuthMiddleware>()));
});

testWidgets('back from approvals returns to tasks instead of resetting dashboard index', (tester) async {
  await pumpShellAt(tester, '/work/tasks');
  await tester.tap(find.text('Phê duyệt'));
  await tester.pageBack();
  expect(find.byType(TasksView), findsOneWidget);
});
```

- [ ] **Step 2: Split only the navigation responsibility.**

Move sidebar/topbar/floating voice/banner into `AppShell`; retain feature pages initially. Replace the large switch in `DashboardContentBody` with a temporary redirect adapter, then delete it only after all sidebar entries have exact routes. Do not rewrite visual widgets in this task.

- [ ] **Step 3: Reduce eager controller registration.**

`DashboardBinding` retains only shell/session dependencies. Feature bindings instantiate their own controller on route entry and dispose it on route exit. Remove `Get.put` calls from views only where a binding now owns the same controller; assert existing `onClose` tests still run.

- [ ] **Step 4: Run route, shell and representative module tests.**

```bash
cd frontend && flutter test \
  test/core/routing/module_routes_test.dart \
  test/core/shell/app_shell_test.dart \
  test/modules/tasks test/modules/approvals test/modules/agents -r compact
flutter analyze
```

- [ ] **Step 5: Commit.**

```bash
git add frontend/lib/core/shell frontend/lib/core/routing frontend/lib/modules/dashboard frontend/test/core
git commit -m "refactor(frontend): navigate workspace modules through canonical shell routes"
```

---

### Task 10: Hợp nhất ownership Hub/Chat và tạo responsive, i18n, accessibility foundation

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Modify: `frontend/lib/modules/chat/**` according to the approved chat decision.
- Create: `frontend/lib/core/ui/layout_breakpoints.dart`
- Create: `frontend/lib/core/ui/app_copy.dart`
- Create: `frontend/lib/core/widgets/feature_state_view.dart` if Task 6 did not place it under shared feature presentation.
- Modify: screens selected from Hub, Agents, Skill Registry and Approvals.
- Create: golden and semantics tests under `frontend/test/golden/` and `frontend/test/accessibility/`.

**Decision gate before code:** confirm one direction with product owner:

1. **Recommended:** Hub owns a dockable chat panel and shared conversation session; `/chat` redirects to `/hub?panel=chat`.
2. Dedicated `/chat` remains, but it must consume the same session/realtime model and has no duplicate service/controller state.

Do not start service merging until this decision is approved.

**Interfaces:**

```dart
enum AppLayout { compact, medium, expanded }
AppLayout layoutForWidth(double width) => switch (width) {
  < 600 => AppLayout.compact,
  < 1024 => AppLayout.medium,
  _ => AppLayout.expanded,
};
```

- [ ] **Step 1: Create snapshot tests for the chosen chat surface and responsive thresholds.**

```dart
testWidgets('skill registry uses a vertical filter sheet on compact layout', (tester) async {
  await pumpAtWidth(tester, const SkillRegistryView(), 390);
  expect(find.byType(OverflowBar), findsNothing);
  expect(find.byTooltip('Bộ lọc'), findsOneWidget);
});

testWidgets('offline runtime banner is announced to assistive technology', (tester) async {
  await tester.pumpWidget(appWithRuntime(remoteOfflineStatus));
  expect(tester.getSemantics(find.byType(RemoteAccessBanner)), includesNodeWith(label: contains('offline')));
});
```

- [ ] **Step 2: Establish shared tokens before touching pages.**

Replace ad-hoc desktop checks with `layoutForWidth`; only migrate pages changed by this plan. Put Vietnamese user-facing copy in `AppCopy`/localization keys. Keep backend/system error codes out of user text but log a correlation id for support.

- [ ] **Step 3: Remove duplicate Hub controller ownership after decision gate.**

`HologramHubBinding` owns exactly one hub presentation controller; view does not call `Get.put`. Move the other controller's data responsibilities into focused collaborators or the chosen chat controller. On exit, timers, voice handlers and realtime listeners all cancel and test their counters.

- [ ] **Step 4: Run golden/semantics tests on three widths.**

```bash
cd frontend && flutter test test/golden test/accessibility \
  test/modules/hologram_hub test/modules/chat -r compact
```

Expected: compact 390, medium 834 and expanded 1440 snapshots render without overflow; no English fallback in selected user-facing screens.

- [ ] **Step 5: Commit separately by decision boundary.**

```bash
git add frontend/lib/core/ui frontend/lib/core/widgets frontend/test/golden frontend/test/accessibility
git commit -m "feat(frontend): standardize responsive and accessible workspace UI"
# Only after the chat decision is approved:
git add frontend/lib/modules/hologram_hub frontend/lib/modules/chat
git commit -m "refactor(frontend): unify assistant session ownership"
```

---

### Task 11: Thiết lập release gate có integration evidence thay vì chỉ mock unit tests

**Files:**
- Create: `frontend/integration_test/session_workspace_flow_test.dart`
- Create: `frontend/integration_test/remote_access_flow_test.dart`
- Create: `frontend/integration_test/approvals_truthfulness_test.dart`
- Create or modify: test fixture/harness documented in `docs/testing/frontend-integration.md`
- Modify: `.github/workflows/quality.yml` only after reconciling current working-tree changes.
- Modify: `frontend/tool/run_quality.sh`

**Interfaces:**
- Consumes: disposable backend fixture with at least user A, workspaces A/B, member/non-member relationship, remote online/offline runtime and one approval.
- Produces: deterministic CI evidence for login→switch→logout, relay/offline behavior and truthful approval error state.

- [ ] **Step 1: Define fixture data and failure injection in documentation.**

Document exact IDs, seed mechanism, base URLs, cleanup and three faults: identity 401, runtime offline, Agent approval 503. Tests must never use developer’s local database or credentials.

- [ ] **Step 2: Write end-to-end tests.**

```dart
testWidgets('switch workspace never leaves data from the previous tenant', (tester) async {
  await loginAs('member-a');
  await selectWorkspace('workspace-a');
  await selectWorkspace('workspace-b');
  expect(find.text('Workspace B'), findsOneWidget);
  expect(apiRecorder.workspaceHeaders, everyElement('workspace-b'));
});

testWidgets('remote offline shows read-only and sends no approval mutation', (tester) async {
  await enterRemoteOfflineWorkspace(tester);
  await tester.tap(find.text('Phê duyệt'));
  expect(find.textContaining('chỉ đọc'), findsOneWidget);
  expect(apiRecorder.businessPosts, isEmpty);
});
```

- [ ] **Step 3: Run in isolated environment and make test artifact available.**

Run the documented stack startup, then:

```bash
cd frontend && flutter test integration_test -d macos -r compact
```

Save JUnit/log/screenshot artifacts without credentials. A skipped test is not a green release gate; CI must mark unavailable fixture as infrastructure failure.

- [ ] **Step 4: Wire staged CI.**

PR: analyzer, unit, contracts, selected goldens. Nightly/release candidate: full integration fixture + macOS UI tests. Publish GHOST count, allowlist expiry and integration summary in job output.

- [ ] **Step 5: Run final release checklist and commit.**

```bash
cd frontend && ./tool/run_quality.sh
flutter test integration_test -d macos -r compact
```

Expected: no security test skipped; full test summary pass; contract checker pass without expired allowlist entries. Commit `test(frontend): add session and remote release coverage`.

## Milestones, acceptance and rollout

| Milestone | Tasks | Exit criterion | Rollout |
|---|---|---|---|
| M0 — Stop unsafe release | 1–2 | Token tests pass; no plaintext secret fallback | Release block until complete |
| M1 — Correct scope | 3–5 | Workspace/session/runtime state is atomic; remote offline is visibly and technically blocked | Internal dogfood with two test workspaces |
| M2 — Truthful operations | 6–8 | Approvals + Agents migrated; SSE reconnect is scoped/reconciled | Feature flag by module if API migration incomplete |
| M3 — Coherent workspace UX | 9–10 | Canonical route shell, one assistant ownership decision, responsive/a11y checks | Gradual route redirects, retain legacy URLs one release |
| M4 — Release proof | 11 | CI has isolated end-to-end evidence | Release candidate gate |

## Plan self-review

- **Spec coverage:** session/token (Tasks 2, 4), Remote Access (Tasks 3–5), truthful data/API drift (Tasks 6–7), realtime (Task 8), navigation/UI (Tasks 9–10), release verification (Task 11).
- **No broad rewrite:** every service migration is limited to active user-visible surfaces, begins with a failing test and preserves a route redirect during transition.
- **Risk containment:** M0 and M1 are release blockers; M2 can ship per domain only if inactive/unsupported mutations are gated; M3 requires explicit product decision for chat.
- **External dependency:** Task 3 requires backend ownership of one authenticated context endpoint. Do not fake it in Flutter; if backend cannot deliver it, Remote Access remains disabled/hidden for release.
