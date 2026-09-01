# Truthful MVP Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa các luồng MVP về trạng thái đáng tin cậy: request đi đúng execution plane, UI không biến lỗi/route không tồn tại thành dữ liệu hoặc thành công, các mutation có persistence/audit thật, và CI phản ánh đúng chất lượng bản phát hành.

**Architecture:** Dùng `ApiClient` làm authority duy nhất cho remote relay, offline guard và timeout; `MvpRequestClient` chỉ chịu trách nhiệm contract/envelope. Business policy được lưu trong COSA Control Plane, còn `apps/cosa` chỉ composition registry + policy. Với capability chưa có backend thật (Vault editor, finance activation, workforce pack toggle), release này dừng/ẩn thao tác và trả trạng thái không khả dụng thay vì mô phỏng thành công.

**Tech Stack:** Flutter/Dart + GetX, FastAPI/Pydantic/Python 3.11, Encore.ts/TypeScript/Drizzle/PostgreSQL, Next.js/TypeScript, Vitest, pytest, Flutter test, GitHub Actions.

**Spec/Context:** Kế hoạch này triển khai các phát hiện audit 2026-09-01 trong cuộc trao đổi hiện tại; tuân theo [M3 Vault](../../architecture/plans/2026-08-29-cosa-workspace-canonical/M3-workspace-vault.md), [M5 Remote Access](../../architecture/plans/2026-08-29-cosa-workspace-canonical/M5-remote-access.md), [M7 Workforce UI](../../architecture/plans/2026-08-29-cosa-workspace-canonical/M7-workforce-ui.md), và [ADR-CUTOVER-001](../../architecture/adr/ADR-CUTOVER-001-rollback-strategy.md).

## Global Constraints

- Không tạo worktree; làm trực tiếp trên nhánh `main` theo `CLAUDE.md`.
- Không thêm `any`, `@ts-ignore`, `@ts-expect-error`, fallback dữ liệu giả, hoặc `catch` nuốt lỗi để trả collection rỗng.
- Mọi public mutation phải xác thực, bind workspace, có test phân quyền và có persistence/audit; nếu chưa đáp ứng đủ, UI phải vô hiệu hóa thao tác và backend trả lỗi rõ ràng.
- Không sửa trực tiếp file generated. Sửa `shared/contracts/mvp-surface.json` rồi chạy `node scripts/gen-mvp-contracts.mjs`.
- Migration release chỉ được **expand**. Không dùng migration 29 như một rollback thông thường; mọi destructive cutover phải có artifact phê duyệt, backup checksum, restore rehearsal và cửa sổ triển khai riêng.
- Mọi comment mới giải thích lý do bằng tiếng Việt. Tên định danh và thông báo lỗi máy giữ tiếng Anh.
- Không thay đổi ba file đang có chỉnh sửa cục bộ của người dùng: `frontend/lib/main.dart`, `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`, `frontend/web/index.html`.
- Mỗi task kết thúc bằng một commit độc lập, chỉ khi toàn bộ test/gate của task pass.

## Scope và thứ tự phụ thuộc

1. **Khôi phục tín hiệu CI** trước để mọi bước sau có baseline đáng tin cậy.
2. **Chuẩn hóa transport** trước khi sửa consumer, để mọi typed MVP client có cùng remote/offline semantics.
3. **Dọn consumer và endpoint canonical**: workforce, approval, finance và founder UI không còn gọi path cũ hoặc trả state giả.
4. **Đưa skill policy vào control plane**, có persistence và audit.
5. **Contain Vault**: không phát hành editor/retrieval giả; full Vault chỉ mở lại sau milestone M3 có storage + ingestion + citation thật.
6. **Gia cố release/security**: route consumer gate, migration evidence, early-access abuse control, dependency/type hygiene.
7. **Chạy E2E độc lập và release gate** trên database tạm, không dùng database local đang chạy của developer.

## File map chính

| Vùng | File hiện có | Trách nhiệm sau thay đổi |
|---|---|---|
| Transport | `frontend/lib/core/network/api_client.dart`, `frontend/lib/core/network/mvp_request_client.dart` | Một resolver cho relay/offline/timeout; MVP client decode contract. |
| MVP contracts | `shared/contracts/mvp-surface.json` | Chỉ inventory endpoint đang hoạt động và có contract thật. |
| Workforce UI | `apps/cosa/api/workforce_routes.py`, `frontend/lib/modules/mission_control/services/control_plane_service.dart`, `frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart` | Dùng `/agent/workforce/*`, trả typed failure thay vì data giả. |
| Skill policy | `services/cosa/services/workspace-settings.service.ts`, `services/cosa/handlers/workspace-settings.handler.ts`, `apps/cosa/api/settings_routes.py` | Control Plane là source of truth; Agent app merge registry với policy. |
| Vault | `frontend/lib/modules/vault/{controllers,views,services}`, `apps/cosa/api/vault_routes.py` | Chỉ hiển thị trạng thái feature unavailable cho đến khi M3 hoàn chỉnh. |
| Finance | `services/company/finance-legal/{handlers,services}/accounting-profile.*`, `frontend/lib/modules/finance` | Không giả update/activate; chỉ expose mutation được persistence. |
| Release | `scripts/`, `.github/workflows/quality.yml`, `services/cosa/migrations/`, `landing/src/app/api/early-access/` | Gating route drift, migration, abuse và reproducibility. |

---

### Task 1: Khôi phục CI xanh mà không hạ chuẩn kiểm tra

**Files:**
- Modify generated: `docs/architecture/generated/company-usage-inventory.md` (chỉ qua generator).
- Modify test files báo lỗi bởi analyzer trong `frontend/test/**`.
- Modify if needed: `frontend/analysis_options.yaml` chỉ để cấu hình hợp lệ, **không** exclude toàn bộ `test/**`.
- Test: `tests/quality/` và toàn bộ `flutter analyze`.

**Interfaces:**
- Consumes: `scripts/company_usage_inventory.py`, migration 29 và source tree hiện tại.
- Produces: `make contract-freeze-check` và `cd frontend && flutter analyze` exit code 0; không có suppression lint mới.

- [ ] **Step 1: Chụp baseline từng gate để tránh gộp lỗi mới vào lỗi cũ.**

Run:

```bash
make contract-freeze-check
cd frontend && flutter analyze
```

Expected: inventory check fail vì snapshot cũ; analyzer báo 50 diagnostics hiện hữu trong test.

- [ ] **Step 2: Sinh lại company usage inventory bằng generator, không hand-edit Markdown.**

Run:

```bash
python scripts/company_usage_inventory.py
git diff -- docs/architecture/generated/company-usage-inventory.md
```

Xác nhận diff chỉ phản ánh source hiện tại, gồm migration `29_cleanup_legacy_companies_and_rename_workspaces` và các usage mới. Review phân loại `LEGACY`/`VALID`/`REVIEW` trước khi giữ file generated.

- [ ] **Step 3: Sửa từng Flutter diagnostic trong test tại nguồn.**

Loại unused import/local; thay việc gọi protected `ValueNotifier.value` trực tiếp bằng helper test/public notifier API; đặt lại biến test không dùng. Không thêm `ignore_for_file`, không hạ lint rule và không exclude `test/**`.

- [ ] **Step 4: Chạy lại analyzer và contract gate.**

Run:

```bash
cd frontend && flutter analyze
cd .. && make contract-freeze-check
```

Expected: cả hai PASS, analyzer không còn warning/info actionable.

- [ ] **Step 5: Chạy regression gần nhất của các test vừa sửa.**

Run:

```bash
cd frontend && flutter test -r compact
```

Expected: PASS; nếu môi trường không trả được full summary, lưu output machine/JUnit rồi chỉ rerun từng file fail đến khi có summary pass rõ ràng.

- [ ] **Step 6: Commit.**

```bash
git add docs/architecture/generated/company-usage-inventory.md frontend/test frontend/analysis_options.yaml
git commit -m "chore(quality): restore contract and Flutter analyzer gates"
```

---

### Task 2: Hợp nhất transport MVP với remote relay, offline guard và timeout

**Files:**
- Modify: `frontend/lib/core/network/api_client.dart:187-330`.
- Modify: `frontend/lib/core/network/mvp_request_client.dart:11-143`.
- Modify: `frontend/test/core/network/mvp_request_client_test.dart`.
- Test: `frontend/test/core/network/api_client_test.dart` (tạo nếu chưa có test cho resolver public).

**Interfaces:**
- Consumes: `ApiClient.resolveUri`, business endpoint classifier, `runtimeMode`, `nodePresence`, `ApiClient.defaultTimeout`.
- Produces:

```dart
class ApiRequestTarget {
  const ApiRequestTarget({this.uri, this.blockedResponse});
  final Uri? uri;
  final http.Response? blockedResponse;
}

static ApiRequestTarget ApiClient.resolveRequestTarget(String endpoint);
```

`uri` và `blockedResponse` là exclusive: request business trong `REMOTE_ACCESS + OFFLINE` không có URI và trả synthetic 503; mọi target còn lại có URI đã resolve đúng plane/relay.

- [ ] **Step 1: Viết failing tests cho ba invariant transport.**

```dart
test('company MVP request uses relay in REMOTE_ACCESS', () async {
  ApiClient.runtimeMode = 'REMOTE_ACCESS';
  final request = await captureRequest(MvpEndpoint.strategyCanvasList);
  expect(request.url.path, startsWith('/relay/commercial/'));
});

test('offline remote business request does not call HTTP client', () async {
  ApiClient.runtimeMode = 'REMOTE_ACCESS';
  ApiClient.nodePresence = 'OFFLINE';
  final calls = <http.Request>[];
  final result = await requestWithRecordingClient(calls, MvpEndpoint.strategyCanvasList);
  expect(result, isA<ApiFailure<Object>>());
  expect(calls, isEmpty);
});

test('MVP request maps elapsed timeout to unavailable', () async {
  final result = await requestWithDelayedClient(timeout: const Duration(milliseconds: 1));
  expect((result as ApiFailure).failure.code, ApiFailureCode.unavailable);
});
```

- [ ] **Step 2: Chạy test để xác nhận lỗi hiện tại.**

Run:

```bash
cd frontend && flutter test test/core/network/mvp_request_client_test.dart -r compact
```

Expected: relay/offline/timeout assertions fail vì client hiện tự ghép base URL và không đặt timeout.

- [ ] **Step 3: Expose một transport target thuần từ `ApiClient`.**

Tách logic private `_offlineGuard` thành `resolveRequestTarget(endpoint)`. Hàm này phải gọi `normalizeEndpoint`, quyết định `/relay` cho business endpoint, giữ agent/platform/local-worker đi đúng origin, và trả response 503 của offline guard mà không gửi traffic. Giữ API `get/post/...` hiện tại bằng cách cho chúng gọi target mới; không nhân bản logic.

- [ ] **Step 4: Đổi `MvpRequestClient` sang target chung và timeout injectable.**

```dart
MvpRequestClient({
  http.Client? httpClient,
  ApiAuthResolver? authResolver,
  Duration requestTimeout = ApiClient.defaultTimeout,
}) : _requestTimeout = requestTimeout;

final routedPath = switch (endpoint.plane) {
  ApiPlane.localWorker => '/local-worker$effectivePath',
  _ => effectivePath,
};
final target = ApiClient.resolveRequestTarget(routedPath);
if (target.blockedResponse case final response?) {
  return _decodeResponse(response, endpoint, decode);
}
final response = await _httpClient.get(target.uri!, headers: headers)
    .timeout(_requestTimeout);
```

Áp dụng cùng timeout cho POST/PUT/PATCH/DELETE. Token vẫn lấy qua `ApiAuthResolver` để giữ khả năng inject test và đúng trust boundary hiện có.

- [ ] **Step 5: Chạy test transport và toàn bộ consumer MVP trọng yếu.**

Run:

```bash
cd frontend && flutter test \
  test/core/network/mvp_request_client_test.dart \
  test/settings_mvp_service_test.dart \
  test/vault_mvp_service_test.dart -r compact
```

Expected: PASS; test mới chứng minh không có business traffic trực tiếp tới local origin khi remote node offline.

- [ ] **Step 6: Commit.**

```bash
git add frontend/lib/core/network/api_client.dart frontend/lib/core/network/mvp_request_client.dart \
  frontend/test/core/network/mvp_request_client_test.dart frontend/test/core/network/api_client_test.dart
git commit -m "fix(frontend): route MVP traffic through canonical transport"
```

---

### Task 3: Chuyển Mission Control và Workforce UI sang endpoint canonical

**Files:**
- Modify: `apps/cosa/api/workforce_routes.py:546-638`.
- Modify: `frontend/lib/modules/mission_control/services/control_plane_service.dart:4-117`.
- Modify: `frontend/lib/modules/mission_control/controllers/mission_control_controller.dart:20-94`.
- Modify: `frontend/lib/modules/hologram_hub/controllers/mixins/hub_control_plane_mixin.dart:28-72`.
- Modify: `frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:132-216`.
- Create: `frontend/lib/modules/workforce/models/workforce_mvp_models.dart`.
- Create: `frontend/lib/modules/workforce/services/workforce_mvp_service.dart`.
- Modify: `shared/contracts/mvp-surface.json` only if an existing workforce response/schema needs correction; regenerate `apps/cosa/api/mvp_contracts_generated.py` and `frontend/lib/core/network/mvp_endpoints.g.dart`.
- Test: `tests/apps/cosa/test_workforce_routes.py`, `tests/integration/test_mvp_workforce_in_process.py`, `frontend/test/modules/mission_control/control_plane_service_test.dart`, new `frontend/test/modules/workforce/workforce_mvp_service_test.dart`.

**Interfaces:**

```dart
sealed class WorkforceResult<T> {
  const WorkforceResult();
}

class WorkforceMvpService {
  Future<ApiResult<List<WorkforceRun>>> listRuns({int limit = 50});
  Future<ApiResult<List<WorkforceRunEvent>>> listRunEvents(String runId);
  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status});
  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {required bool approved, String? reason});
  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition();
}
```

`/agent/workforce/approvals` phải trả `mvp_list(items, ...)`, không trả raw `{items,total}` trái contract.

- [ ] **Step 1: Viết backend tests cho approval envelope và tenant isolation.**

```python
async def test_workforce_approvals_use_mvp_envelope(client, workspace_a):
    response = await client.get('/agent/workforce/approvals')
    assert response.status_code == 200
    assert set(response.json()) == {'data', 'meta'}

async def test_workspace_b_cannot_decide_workspace_a_approval(client_a, client_b):
    approval_id = await create_pending_approval(client_a)
    response = await client_b.post(
        f'/agent/workforce/approvals/{approval_id}/decision',
        json={'approved': True, 'reason': 'not allowed'},
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Làm cho workforce route đúng contract trước khi đổi UI.**

Thay raw object ở `workforce_routes.py:585` bằng `mvp_list`; giữ field `total` trong payload `data` chỉ khi schema đã định nghĩa nó, nếu không list là `data` duy nhất. Update contract/schema và regenerate nếu shape thay đổi.

- [ ] **Step 3: Viết typed Dart models/service trên MvpRequestClient.**

`WorkforceRun`, `WorkforceRunEvent`, `WorkforceApproval`, `WorkforceCompositionEntry` chỉ decode field do backend contract trả. `ApiFailure` được trả nguyên vẹn cho controller; không đổi thành `[]`, `null` hoặc `false`.

- [ ] **Step 4: Migrate consumer đang gọi route cũ.**

Đổi `listRuns`, `getRunEvents`, pending approval và quyết định approval sang `WorkforceMvpService`. Xóa các call `/agent/goals`, `/agent/plans/*`, `/agents/approvals`, `/workforce/packs*` vì không có canonical route. UI hiển thị trạng thái `unavailable` cho Goal/Plan/Pack toggle; workforce composition chỉ hiển thị dữ liệu `/agent/workforce/composition`, không dựng danh sách 5/12 agent mặc định.

- [ ] **Step 5: Viết Flutter tests chứng minh không còn false-empty/fallback.**

```dart
test('404 workforce response is shown as failure, not an empty list', () async {
  final result = await service.listRuns();
  expect(result, isA<ApiFailure<List<WorkforceRun>>>());
});

test('founder workforce composition never creates packs after a failed request', () async {
  await controller.loadDashboard();
  expect(controller.workforcePacks, isEmpty);
  expect(controller.workforceState.value, WorkforceLoadState.unavailable);
});
```

- [ ] **Step 6: Chạy contracts, backend và Flutter tests.**

Run:

```bash
node scripts/gen-mvp-contracts.mjs --check
PYTHONPATH=. pytest tests/apps/cosa/test_workforce_routes.py tests/integration/test_mvp_workforce_in_process.py -q
cd frontend && flutter test test/modules/mission_control/control_plane_service_test.dart \
  test/modules/workforce/workforce_mvp_service_test.dart -r compact
```

- [ ] **Step 7: Commit.**

```bash
git add apps/cosa/api/workforce_routes.py apps/cosa/api/mvp_contracts_generated.py \
  shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart \
  frontend/lib/modules/{mission_control,hologram_hub,workforce} tests/apps/cosa/test_workforce_routes.py \
  tests/integration/test_mvp_workforce_in_process.py frontend/test/modules
git commit -m "fix(workforce): replace stale control-plane routes with canonical contracts"
```

---

### Task 4: Persist Workspace Skill Policy tại COSA Control Plane

**Files:**
- Create: `services/cosa/migrations/30_workspace_skill_policies.up.sql` and `.down.sql`.
- Modify: `services/cosa/storage/schema.ts`.
- Modify: `services/cosa/services/workspace-settings.service.ts`.
- Modify: `services/cosa/handlers/workspace-settings.handler.ts`.
- Modify: `services/cosa/tests/workspace-settings.test.ts`.
- Create: `apps/cosa/capabilities/workspace_settings_client.py`.
- Modify: `apps/cosa/composition/agent_plane.py`, `apps/cosa/api/app.py`, `apps/cosa/api/settings_routes.py:55-127`.
- Modify: `shared/contracts/mvp-surface.json:215-242`, then regenerate contracts.
- Test: `tests/apps/cosa/test_settings_routes.py`, `tests/e2e/test_mvp_settings_http.py`, `frontend/test/settings_mvp_service_test.dart`.

**Interfaces:**

```ts
export interface WorkspaceSkillPolicyView {
  readonly workspaceId: string;
  readonly skillKey: string;
  readonly enabled: boolean;
  readonly config: Record<string, unknown>;
  readonly revision: number;
  readonly updatedBy: string;
  readonly updatedAt: string;
}

GET /platform/workspaces/:workspaceId/skill-policies
PUT /platform/workspaces/:workspaceId/skill-policies/:skillKey
```

Table key là `(workspace_id, skill_key)`. Upsert tăng `revision`, luôn ghi `workspace_settings_audit_events`, và chỉ workspace operator được mutate. `apps/cosa` validate `skillKey` với registry rồi gọi control plane; không tự lưu policy.

- [ ] **Step 1: Viết tests cho persistence, authorization và unavailable registry.**

```ts
it('persists a skill policy and increments revision', async () => {
  const first = await putWorkspaceSkillPolicy({ workspaceId, skillKey: 'lead_enricher', enabled: true, config: {} });
  const second = await putWorkspaceSkillPolicy({ workspaceId, skillKey: 'lead_enricher', enabled: false, config: {} });
  expect(second.data.revision).toBe(first.data.revision + 1);
});

it('rejects a non-member mutation', async () => {
  await expect(putWorkspaceSkillPolicy({ workspaceId, authorization: outsiderToken, skillKey: 'lead_enricher', enabled: true, config: {} }))
    .rejects.toThrow(/permission/i);
});
```

Python route tests phải chứng minh registry lỗi trả 503 `unavailable`, không trả `data: []` với source `agent_db`.

- [ ] **Step 2: Tạo migration expand-only và Drizzle schema.**

`workspace_skill_policies` có `workspace_id BIGINT NOT NULL`, `skill_key TEXT NOT NULL`, `enabled BOOLEAN NOT NULL DEFAULT true`, `config JSONB NOT NULL DEFAULT '{}'`, `revision INTEGER NOT NULL DEFAULT 1`, `updated_by TEXT NOT NULL`, timestamps và `PRIMARY KEY (workspace_id, skill_key)`. Thêm index `(workspace_id, updated_at DESC)`. Down migration chỉ drop bảng trên database disposable; không dùng để xử lý production rollback image.

- [ ] **Step 3: Bổ sung service/handler Control Plane theo pattern workspace settings.**

Reuse `verifyWorkspaceMembership`; dùng role guard operator trước upsert; transaction gồm upsert policy và insert audit event (`event_type='skill_policy.updated'`, `target_kind='skill_policy'`). Response dùng `mvpList`/`mvpItem` với source `control_plane`.

- [ ] **Step 4: Wire Agent settings route như composition layer.**

`WorkspaceSettingsClient` gửi bearer token và workspace ID đến service COSA. `GET /agent/settings/skills` merge published registry metadata với policy đã persist; `PUT` gọi `require_workspace_operator`, validate registry skill/config rồi upsert qua client và read-after-write. Nếu client/control plane unavailable, trả 503; tuyệt đối không echo body thành success.

- [ ] **Step 5: Cập nhật MVP contract và Flutter UI.**

Giữ endpoint agent-facing để UI không cần biết topology, nhưng đặt `source_kind` authoritative là `control_plane`. `SettingsMvpService.updateSkill` chỉ cập nhật state cục bộ sau `ApiSuccess` có `revision` lớn hơn revision hiện tại.

- [ ] **Step 6: Chạy migration trên PostgreSQL disposable và full test theo boundary.**

Run:

```bash
PGPORT=5433 scripts/bootstrap-postgres-cluster.sh
cd services/cosa && node scripts/migrate.mjs
cd ../.. && make encore-handler-boundary-check && make ts-suppression-check
PYTHONPATH=. pytest tests/apps/cosa/test_settings_routes.py tests/e2e/test_mvp_settings_http.py -q
cd frontend && flutter test test/settings_mvp_service_test.dart -r compact
```

Expected: state còn sau app/client instance mới, non-operator bị từ chối, event audit có actor/revision.

- [ ] **Step 7: Commit.**

```bash
git add services/cosa/migrations/30_workspace_skill_policies.* services/cosa/{storage,services,handlers,tests} \
  apps/cosa/{capabilities,composition,api} shared/contracts/mvp-surface.json \
  apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart \
  frontend/lib/modules/settings frontend/test/settings_mvp_service_test.dart tests/apps/cosa/test_settings_routes.py tests/e2e/test_mvp_settings_http.py
git commit -m "feat(settings): persist workspace skill policies with audit"
```

---

### Task 5: Contain Vault để không hiển thị file, index hoặc retrieval giả

**Files:**
- Modify: `frontend/lib/modules/vault/services/vault_service.dart:7-140`.
- Modify: `frontend/lib/modules/vault/controllers/vault_controller.dart:28-176`.
- Modify: `frontend/lib/modules/vault/views/vault_view.dart:10-35` and related vault widgets.
- Modify: `frontend/lib/modules/hologram_hub/controllers/mixins/hub_voice_mixin.dart` for Vault navigation feedback.
- Modify: `frontend/lib/modules/vault/services/vault_mvp_service.dart` and `frontend/test/vault_mvp_service_test.dart`.
- Modify: `apps/cosa/api/vault_routes.py:93-241` and `shared/contracts/mvp-surface.json:515-632`.
- Test: `tests/apps/cosa/test_vault_routes.py`, `tests/integration/test_mvp_vault_in_process.py`, focused Vault widget/controller tests.

**Interfaces:**

```dart
enum VaultAvailability { unavailable, available }

class VaultFeatureState {
  const VaultFeatureState.unavailable(this.message);
  final String message;
}
```

Trong release này `VaultAvailability.unavailable` là giá trị duy nhất phát hành. Không có `documents=[]` hay fake `INDEXED` như một biểu diễn cho feature chưa triển khai. Canonical ingestion tạm thời vẫn là `/agent/knowledge/uploads` theo M3; nó không được gắn nhãn là semantic Vault/retrieval đến khi có evidence end-to-end.

- [ ] **Step 1: Viết tests cho containment.**

```dart
testWidgets('Vault screen explains unavailable capability without requesting legacy /vault routes', (tester) async {
  await tester.pumpWidget(const VaultView());
  expect(find.textContaining('chưa khả dụng'), findsOneWidget);
  expect(recordedRequests.where((r) => r.url.path.startsWith('/vault/')), isEmpty);
});

test('legacy vault upload endpoint returns explicit unavailable response', () async {
  final response = await client.post('/agent/vault/documents/upload-ticket', json: validPayload);
  assert response.status_code == 501
  assert response.json()['detail'] == 'Vault document ingestion is not released'
});
```

- [ ] **Step 2: Thay Vault legacy client/UI bằng unavailable state.**

Không gọi `/vault/*`, không dùng `sendForm`, không bắt lỗi thành `[]`. `VaultView` hiển thị lý do, liên kết tài liệu/khả năng knowledge ingestion nếu feature flag đã bật, và bỏ mọi nút edit/save/promote/retrieval. Voice command `vault` báo feature chưa phát hành thay vì điều hướng vào editor hỏng.

- [ ] **Step 3: Retire contract công khai không có implementation.**

Đánh dấu bảy `vault.*` entries trong `mvp-surface.json` là disabled theo schema generator; regenerate và xóa `VaultMvpService`/test contract cũ nếu không còn consumer. Các route FastAPI legacy trả `501 Not Implemented` với message không tiết lộ storage topology; không tạo draft/version/index giả, không tin checksum/size do client khai báo.

- [ ] **Step 4: Chuyển test hiện tại khỏi false lifecycle.**

Xóa assertion "ticket → confirm → INDEXED → retrieval hit" vì đó không chứng minh upload. Thay bằng 501 assertion, và giữ/viết test riêng cho `/agent/knowledge/uploads` chỉ khi object store, service token, feature flag và worker thật đều được wire trong fixture production.

- [ ] **Step 5: Chạy Vault/knowledge boundary tests.**

Run:

```bash
PYTHONPATH=. pytest tests/apps/cosa/test_vault_routes.py tests/apps/cosa/test_knowledge_production_wiring.py -q
cd frontend && flutter test test/vault_mvp_service_test.dart test/modules/vault -r compact
node scripts/gen-mvp-contracts.mjs --check
```

Expected: không còn route/UI public nào báo upload, indexing hoặc retrieval thành công khi không có file/object/embedding/citation thật.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/api/vault_routes.py shared/contracts/mvp-surface.json \
  apps/cosa/api/mvp_contracts_generated.py frontend/lib/modules/vault \
  frontend/lib/modules/hologram_hub/controllers/mixins/hub_voice_mixin.dart \
  frontend/lib/core/network/mvp_endpoints.g.dart tests/apps/cosa/test_vault_routes.py \
  tests/integration/test_mvp_vault_in_process.py frontend/test/vault_mvp_service_test.dart frontend/test/modules/vault
git commit -m "fix(vault): stop exposing unimplemented document lifecycle"
```

**Exit decision for reopening Vault:** Execute the remaining M3 storage/RLS work in a separate approved plan. Re-enable UI only after an isolated E2E test uploads bytes, server verifies MIME/size/SHA-256, scan/ingestion progresses through structured states, retrieval returns persisted chunk text plus source/version citation, and workspace B cannot read/search/delete workspace A data.

---

### Task 6: Loại bỏ false success trong Finance và Founder UI

**Files:**
- Modify: `frontend/lib/modules/finance/services/finance_service.dart:78-107`.
- Modify: `frontend/lib/modules/finance/controllers/finance_controller.dart:219-242`.
- Modify: `frontend/lib/modules/finance/views/tabs/profile_settings_tab.dart`.
- Modify: `frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart:132-216`.
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart:102-245`.
- Test: create `frontend/test/modules/finance/finance_service_test.dart`; create/update founder command center tests.

**Interfaces:**

```dart
sealed class ActionResult<T> {
  const ActionResult();
}
final class ActionUnavailable<T> extends ActionResult<T> {
  const ActionUnavailable(this.message);
  final String message;
}
```

Accounting profile create/get continue dùng endpoint thật. `updateProfileMode` và `activateProfile` chỉ enabled sau khi có public Encore handler/service mutation transaction; trước đó trả `ActionUnavailable`, không gọi create route và không mutate local state.

- [ ] **Step 1: Viết regression tests cho các false success hiện tại.**

```dart
test('activate profile never reports active without an HTTP mutation', () async {
  final result = await service.activateProfile('profile-1');
  expect(result, isA<ActionUnavailable<Map<String, dynamic>>>());
  expect(mockClient.requests, isEmpty);
});

test('failed workforce pack request does not synthesize active packs', () async {
  final result = await service.listWorkforcePacks();
  expect(result, isA<ApiFailure<List<WorkforcePackModel>>>());
});
```

- [ ] **Step 2: Make Finance UI truthful in this release.**

`updateProfile` không còn gọi `createProfile`; `activateProfile` không trả map hard-code. Disable affordance cho đổi mode/activate và hiển thị "Chưa có API nghiệp vụ được phát hành". Giữ create profile, get profile và các flow TT58 thực sự có response backend tách biệt.

- [ ] **Step 3: Make Founder Workforce truthful.**

Thay `listWorkforcePacks` bằng data từ `WorkforceMvpService.getComposition`; map từ composition thật sang UI read-only. Xóa fallback 5 pack và disable `toggleOptionalPack` đến khi M7 có create/retire assignment contract và UI chọn đúng functional key.

- [ ] **Step 4: Chạy test controller/widget theo failure và success thật.**

Run:

```bash
cd frontend && flutter test test/modules/finance test/modules/hologram_hub -r compact
```

Expected: lỗi network/404 được render unavailable; không toast "Đã chuyển"/"Đã kích hoạt" nếu không có persisted response.

- [ ] **Step 5: Commit.**

```bash
git add frontend/lib/modules/finance frontend/lib/modules/hologram_hub frontend/test/modules/finance frontend/test/modules/hologram_hub
git commit -m "fix(frontend): remove finance and workforce success fallbacks"
```

---

### Task 7: Ngăn route literal frontend drift bằng contract consumer gate

**Files:**
- Create: `scripts/check_frontend_api_contracts.mjs`.
- Create: `scripts/frontend-api-contract-allowlist.json`.
- Create: `tests/quality/test_frontend_api_contracts.py`.
- Modify: `Makefile`, `.github/workflows/quality.yml`, `CLAUDE.md`.

**Interfaces:**

```ts
type ApiConsumerViolation =
  | { readonly file: string; readonly line: number; readonly path: string; readonly reason: 'unknown_literal_route' }
  | { readonly file: string; readonly line: number; readonly path: string; readonly reason: 'disabled_contract' };
```

Checker quét literal first argument của `ApiClient.get/post/put/patch/delete/sendForm`, normalize query/path params, đối chiếu `shared/contracts/mvp-surface.json`. Allowlist chỉ chứa endpoint foundation được chứng minh không thuộc MVP manifest (auth bootstrap, realtime stream) và có `owner`, `reason`, `expires_on`.

- [ ] **Step 1: Viết fixture tests trước.**

```python
def test_checker_rejects_unknown_api_client_literal(tmp_path: Path) -> None:
    source = tmp_path / 'frontend/lib/x.dart'
    source.parent.mkdir(parents=True)
    source.write_text("await ApiClient.get('/agent/not-a-contract');")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert 'unknown_literal_route' in result.stderr

def test_all_allowlist_entries_have_expiry_and_owner() -> None:
    entries = json.loads(ALLOWLIST.read_text())['entries']
    assert all({'path', 'owner', 'reason', 'expires_on'} <= entry.keys() for entry in entries)
```

- [ ] **Step 2: Build matcher từ manifest.**

Path template `:id`/`:workspaceId` match một segment URL đã encode; query string bị bỏ trước match. Generated contract không phải input vì generator-owned. Scanner bỏ `test/**`, comments và dynamic string; các dynamic endpoint phải được refactor về `MvpEndpoint` hoặc explicitly listed trong allowlist.

- [ ] **Step 3: Baseline allowlist theo evidence, không baseline hoá route cũ.**

Run:

```bash
node scripts/check_frontend_api_contracts.mjs --root . --manifest shared/contracts/mvp-surface.json \
  --allowlist scripts/frontend-api-contract-allowlist.json
```

Mọi `/vault/*`, `/agent/goals`, `/agent/plans`, `/agents/approvals`, `/workforce/packs*` phải được sửa/xóa ở Task 3/5/6, không được đưa allowlist.

- [ ] **Step 4: Wire Makefile/CI/docs.**

```make
frontend-api-contract-check:
	node scripts/check_frontend_api_contracts.mjs --root . --manifest shared/contracts/mvp-surface.json --allowlist scripts/frontend-api-contract-allowlist.json
```

Thêm target vào job boundary/contract của `quality.yml` và liệt kê trong `CLAUDE.md` Encore/frontend guardrails.

- [ ] **Step 5: Chạy checker và test quality.**

Run:

```bash
PYTHONPATH=. pytest tests/quality/test_frontend_api_contracts.py -q
make frontend-api-contract-check
```

- [ ] **Step 6: Commit.**

```bash
git add scripts/check_frontend_api_contracts.mjs scripts/frontend-api-contract-allowlist.json \
  tests/quality/test_frontend_api_contracts.py Makefile .github/workflows/quality.yml CLAUDE.md
git commit -m "chore(quality): gate frontend routes against API contracts"
```

---

### Task 8: Đưa migration destructive vào release gate có evidence thật

**Files:**
- Modify: `services/cosa/migrations/29_cleanup_legacy_companies_and_rename_workspaces.up.sql:1-18` only if migration 29 has not reached an immutable deployed release; otherwise leave immutable.
- Modify/Create: `docs/architecture/adr/ADR-CUTOVER-001-rollback-strategy.md`, `docs/runbooks/prod-cutover.md`, `docs/runbooks/evidence/m2-destructive-cutover-29.md`.
- Modify: `scripts/check-migration-backward-compat.mjs` and tests under `tests/quality/` if the script currently accepts free-form `allow-destructive` comments.
- Modify generated docs via their generators: `docs/architecture/generated/company-usage-inventory.md`, route inventory if applicable.

**Interfaces:**

```yaml
cutover:
  migration: 29_cleanup_legacy_companies_and_rename_workspaces
  environment: prelaunch-only
  approved_adr: ADR-CUTOVER-001
  backup_sha256: '<recorded before execution>'
  restore_rehearsal: passed
  n_minus_1_schema_compatibility: not-applicable-prelaunch
```

The evidence file contains exact timestamp, operator, database snapshot identifier/hash, restore command result and approval reference. A comment in SQL is never sufficient authorization.

- [ ] **Step 1: Decide whether 29 is already immutable on an environment containing real data.**

Read deployment history and database migration ledger without modifying it. If any production-like environment has applied it, do **not** rewrite migration file; write compensating migration/runbook only. If it is pre-launch and not released, replace its free-form exemption with a checked evidence reference before first deploy.

- [ ] **Step 2: Write failing quality test for destructive exemption format.**

```python
def test_destructive_migration_requires_evidence_file(tmp_path: Path) -> None:
    migration = tmp_path / '29_bad.up.sql'
    migration.write_text('-- migration-compat: allow-destructive\nDROP TABLE x;')
    result = run_migration_checker(tmp_path)
    assert result.returncode == 1
    assert 'missing cutover evidence' in result.stderr
```

- [ ] **Step 3: Implement strict checker rule.**

Accept destructive DDL only when a colocated/declared evidence file has valid migration identity, explicit `prelaunch-only`, ADR, backup checksum and successful restore rehearsal. CI validates metadata syntax and doc path; release operator fills immutable actual snapshot values before deploy.

- [ ] **Step 4: Reconcile docs and external route surface.**

Update M2 status to actual state. Inventory `/platform/auth/me/companies`, `/create`, `/join` as compatibility semantics; either migrate consumers in a named release or return explicit deprecation response. Do not claim the aggregate removal is complete while these paths remain exposed.

- [ ] **Step 5: Verify with disposable DB and boundary gates.**

Run:

```bash
PYTHONPATH=. pytest tests/quality -k migration -q
make migration-compat-check
make contract-freeze-check
```

Then run forward migration and documented restore rehearsal against a fresh CI PostgreSQL instance, capturing schema fingerprint before/after/restore.

- [ ] **Step 6: Commit.**

```bash
git add services/cosa/migrations docs/architecture/adr/ADR-CUTOVER-001-rollback-strategy.md \
  docs/runbooks scripts/check-migration-backward-compat.mjs tests/quality docs/architecture/generated
git commit -m "chore(migrations): require evidence for destructive cutovers"
```

---

### Task 9: Bảo vệ Early Access khỏi abuse và lưu đăng ký bền vững

**Files:**
- Create: `landing/src/lib/early-access-store.ts` and `landing/src/lib/early-access-rate-limit.ts`.
- Modify: `landing/src/app/api/early-access/route.ts:1-126`.
- Modify: `landing/src/lib/early-access.ts` and `landing/src/lib/resend.ts` only for the new durable registration shape.
- Modify: `landing/src/app/api/early-access/route.test.ts`.
- Modify: `landing/.env.example` or documented environment template with `TURNSTILE_SECRET_KEY`, rate-limit/store configuration and retention setting.

**Interfaces:**

```ts
export interface EarlyAccessStore {
  findByEmail(email: string): Promise<EarlyAccessRegistration | null>;
  create(input: NewEarlyAccessRegistration): Promise<EarlyAccessRegistration>;
  markEmailQueued(id: string, providerMessageId: string): Promise<void>;
}

export interface RateLimiter {
  consume(key: string, limit: number, windowSeconds: number): Promise<{ allowed: boolean; retryAfterSeconds: number }>;
}
```

Production adapter must be durable/shared (database or managed KV). An in-memory adapter is test/development-only and must not silently become production rate limiting.

- [ ] **Step 1: Write failing route tests.**

```ts
it('returns 429 before email when IP quota is exhausted', async () => {
  limiter.consume.mockResolvedValueOnce({ allowed: false, retryAfterSeconds: 3600 });
  const response = await post(validBody, { 'x-forwarded-for': '203.0.113.10' });
  expect(response.status).toBe(429);
  expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
});

it('is idempotent for an email already queued', async () => {
  store.findByEmail.mockResolvedValue(existingRegistration);
  const response = await post(validBody);
  expect(response.status).toBe(200);
  expect(sendEarlyAccessEmails).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Validate bot defense before persistence/email.**

Use Turnstile server verification in production, a hidden honeypot input, and trusted platform-provided client IP. Enforce: 3 accepted attempts/IP/hour, 1 new registration/email/day. Return 429 with `Retry-After`; do not disclose whether an address is registered.

- [ ] **Step 3: Persist first, then queue/send idempotently.**

Generate `accessCode` with `crypto.randomUUID()` and label it registration reference, not authorization credential. Create/upsert durable record keyed by normalized email; send confirmation only after queue provider returns a message ID; record delivery status. In simulated development, persist status `simulated` and return `success: false` exactly as current truth contract requires.

- [ ] **Step 4: Add privacy operations.**

Document retention duration, erasure process and required env variables. Store only form fields needed for early access; never log raw body, email, phone or access code in error logs.

- [ ] **Step 5: Run landing quality gates.**

Run:

```bash
cd landing && npm test -- --run && npm run lint && npm run build
```

Expected: PASS; simulated, quota, invalid CAPTCHA, duplicate and provider failure all have deterministic tests.

- [ ] **Step 6: Commit.**

```bash
git add landing/src landing/.env.example
git commit -m "feat(landing): rate limit and persist early access registrations"
```

---

### Task 10: Dependency/type hardening and final release evidence

**Files:**
- Modify: `pyproject.toml`, `apps/cosa/requirements.txt`, `packages/agent/requirements.txt` and chosen lock files.
- Modify: `frontend/pubspec.yaml` and `frontend/pubspec.lock` for maintained Markdown package/update policy.
- Modify: `landing/vitest.config.ts` or rename to `landing/vitest.config.mts` after verifying Node/Next resolution.
- Modify: `.github/workflows/quality.yml` to run locks/vulnerability checks and the final matrix.
- Create: `docs/runbooks/truthful-mvp-release-checklist.md`.

**Interfaces:**
- Python dependency resolution is repeatable from a committed lock with hashes.
- Mypy checks bodies of modified app/agent modules; new changed boundary functions carry concrete signatures.
- Flutter dependency update preserves Dart/Flutter version constraints and a green analyzer/test suite.

- [ ] **Step 1: Create a reproducible dependency baseline.**

Choose one resolver already acceptable to the team (`uv` or `pip-tools`) and commit generated lock with hashes. Pin direct versions for `apps/cosa` and `packages/agent`; CI installs from lock. Do not mix two resolvers for the same environment.

- [ ] **Step 2: Increase type coverage without a global breaking flip.**

Enable `check_untyped_defs = true`; annotate currently reported untyped object-store methods. For `disallow_untyped_defs`, start with modified modules via per-module override, then record count/owner in release checklist. No type suppression baseline is allowed.

- [ ] **Step 3: Modernize bounded dependency risks.**

Replace discontinued `flutter_markdown` with `flutter_markdown_plus` behind existing renderer abstraction and test markdown rendering behavior. Resolve the Vitest CJS/ESM warning by using an ESM config file only after `npm test`, lint and build pass.

- [ ] **Step 4: Execute release matrix on isolated infrastructure.**

Run:

```bash
make lint
make typecheck-py
cd services/company && pnpm typecheck
cd ../cosa && pnpm typecheck
cd ../.. && make boundary-check && make contract-freeze-check && make frontend-api-contract-check
cd frontend && flutter analyze && flutter test -r compact
cd ../landing && npm ci && npm test -- --run && npm run lint && npm run build
```

Run database migration/Encore HTTP E2E only against disposable CI PostgreSQL with unique ports and a fresh database. Do not use the developer's running local containers.

- [ ] **Step 5: Perform manual truthful-MVP acceptance.**

Validate with a test workspace in LOCAL and REMOTE_ACCESS/OFFLINE: company request relay behavior; missing token; control-plane unavailable; operator/non-operator skill edit; Vault unavailable message; Finance update/activate unavailable message; no synthetic workforce packs; early-access rate/duplicate behavior. Capture request/response IDs and screenshots without sensitive data.

- [ ] **Step 6: Publish release checklist result and commit.**

```bash
git add pyproject.toml apps/cosa/requirements.txt packages/agent/requirements.txt frontend/pubspec.* landing .github/workflows/quality.yml docs/runbooks/truthful-mvp-release-checklist.md
git commit -m "chore(release): make MVP verification reproducible"
```

## Definition of Done

- CI frontend and contract-freeze jobs are green without analyzer suppression or generated-file hand edits.
- Every Mvp request uses canonical relay/offline/timeout behavior.
- No rendered frontend success state can originate from a 4xx/5xx, catch block, static fallback, nonexistent route or local mutation without server persistence.
- Skill policy survives process restart, is workspace-scoped, operator-gated and audited.
- Vault editor/retrieval is absent or visibly unavailable until M3 end-to-end storage/ingestion/citation gate is met.
- Migration 29 is explicitly treated as a prelaunch destructive cutover with evidence, or is protected by compensating release procedure if immutable.
- Early-access endpoint is rate-limited, bot-checked, idempotent, durable and privacy-documented.
- Full release matrix passes on disposable infrastructure with recorded evidence.

## Self-review

- **Coverage:** Tasks 1–10 cover every P1/P2 finding from the audit: CI drift, transport, false fallback, Vault, settings persistence, migration, landing abuse, typing/dependencies.
- **Scope:** Full S3/RLS/vector Vault implementation, remote tunnel transport and full workforce/finance feature build remain in their existing M3/M5/M7 milestones; this plan only prevents their incomplete state from being misrepresented to users.
- **Consistency:** Control Plane owns mutable workspace policy; agent app composes registry data; frontend handles `ApiFailure`/unavailable structurally; generated contracts remain generator-owned.
- **Placeholder scan:** Không có bước để trống, mốc trì hoãn không có owner, hoặc yêu cầu xử lý chung chung.
