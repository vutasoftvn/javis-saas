# Workspace Vision / Mission / Core Values Implementation Plan (Superseded)

> Superseded by `docs/superpowers/plans/2026-08-31-workspace-orientation-optional.md`. Do not execute this plan: its required-onboarding and blocking-Hub behavior conflicts with the current product decision.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Founder phải thiết lập Vision/Mission/Core Values cho workspace — bắt buộc ngay sau khi workspace được tạo, và chặn cứng Hub cho mọi workspace cũ đăng nhập vào mà chưa có đủ 3 trường.

**Architecture:** Thêm 3 cột nullable vào bảng `core.workspaces` (services/company/identity). Một endpoint `PATCH /identity/workspaces/:id/company-identity` để lưu, endpoint `GET /identity/workspaces/:id` có sẵn được mở rộng để đọc. Frontend có 1 modal dùng chung (`CompanyIdentityModal`, non-dismissible) với nút "Nhờ AI soạn" tái dùng `AgentChatService` (đã sửa ở phiên trước) để tạo draft qua AgentOS conversation/message/SSE. Một điểm gắn gate duy nhất trong `HubAuthMixin.ensureAuthenticated()` bắt cả 2 tình huống (workspace mới tạo / workspace cũ thiếu dữ liệu).

**Tech Stack:** Encore.ts + Drizzle ORM (backend), Flutter + GetX (frontend), Vitest (backend test), flutter_test (frontend test).

## Global Constraints

- Data model: 1 bộ Vision/Mission/Core Values **per workspace** (không phải per project).
- Core Values là **một ô text tự do nhiều dòng**, không phải danh sách chips/tags.
- Modal chặn cứng: `barrierDismissible: false`, không có nút đóng/back — áp dụng cho cả luồng tạo workspace mới lẫn đăng nhập vào workspace cũ thiếu dữ liệu, qua **một điểm gắn duy nhất** (`HubAuthMixin.ensureAuthenticated()`).
- Backend field/JSON key convention trong repo này là **camelCase** (khớp thẳng tên field TS, không tự convert snake_case) — request/response đều dùng `vision`, `mission`, `coreValues`.
- Auth cho endpoint mới dùng `resolveTenantContext` (pattern có sẵn trong `services/company/identity`, xem `getWorkspacePlatformCompany`), không dùng `requireWorkspaceAccess` (đó là pattern của domain `operations`, khác domain).
- Không sửa luồng tạo workspace ở `VentureOnboardingScreen` / `/platform/auth/register` — gate xử lý ở Hub.
- Không cho sửa lại Vision/Mission/Values sau khi lưu lần đầu trong scope này (không có UI "Chỉnh sửa").

---

### Task 1: Migration + Drizzle schema — thêm cột vision/mission/core_values

**Files:**
- Create: `services/company/identity/migrations/7_workspace_company_identity.up.sql`
- Create: `services/company/identity/migrations/7_workspace_company_identity.down.sql`
- Modify: `services/company/shared/db/schema/identity.ts:5-26` (bảng `identityWorkspaces`)

**Interfaces:**
- Produces: cột DB `core.workspaces.vision`, `.mission`, `.core_values` (nullable text) + field Drizzle tương ứng `identityWorkspaces.vision` / `.mission` / `.coreValues`, dùng bởi Task 2.

- [ ] **Step 1: Viết migration up**

```sql
-- services/company/identity/migrations/7_workspace_company_identity.up.sql
-- Founder phải thiết lập Vision/Mission/Core Values cho workspace — chặn
-- cứng Hub tới khi điền (frontend gate, xem HubAuthMixin.ensureAuthenticated).
-- Quan hệ 1-1 với workspace, không cần bảng con.
ALTER TABLE core.workspaces
  ADD COLUMN vision TEXT,
  ADD COLUMN mission TEXT,
  ADD COLUMN core_values TEXT;
```

- [ ] **Step 2: Viết migration down**

```sql
-- services/company/identity/migrations/7_workspace_company_identity.down.sql
ALTER TABLE core.workspaces
  DROP COLUMN vision,
  DROP COLUMN mission,
  DROP COLUMN core_values;
```

- [ ] **Step 3: Thêm field vào Drizzle schema**

Trong `services/company/shared/db/schema/identity.ts`, sửa `identityWorkspaces` — thêm 3 dòng ngay trước `createdAt`:

```ts
export const identityWorkspaces = coreSchema.table("workspaces", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  name: text("name").notNull(),
  slug: text("slug"),
  status: text("status").default("ACTIVE").notNull(),
  runtimeMode: text("runtime_mode").default("LOCAL_ONLY").notNull(),
  syncPolicy: text("sync_policy").default("CONTROL_METADATA_ONLY").notNull(),
  syncStatus: text("sync_status").default("LOCAL_ONLY").notNull(),
  stageVersion: integer("stage_version").default(0).notNull(),
  primaryLegalEntityId: bigint("primary_legal_entity_id", { mode: "bigint" }),
  lifecycleStage: text("lifecycle_stage").default("W0_IDEA").notNull(),
  platformCompanyId: text("platform_company_id").unique(),
  platformWorkspaceId: text("platform_workspace_id").unique(),
  stageEnteredAt: timestamp("stage_entered_at", { withTimezone: true }),
  // Task 1 (Vision/Mission/Core Values) — 1 bộ per workspace, nullable tới
  // khi founder điền qua CompanyIdentityModal.
  vision: text("vision"),
  mission: text("mission"),
  coreValues: text("core_values"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  archivedAt: timestamp("archived_at", { withTimezone: true }),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```

- [ ] **Step 4: Chạy migration**

Run: `cd /Volumes/SSD/javis-saas && make services-migrate-company`
Expected: log xác nhận migration `7_workspace_company_identity` đã áp dụng, không lỗi.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/identity/migrations/7_workspace_company_identity.up.sql \
        services/company/identity/migrations/7_workspace_company_identity.down.sql \
        services/company/shared/db/schema/identity.ts
git commit -m "feat(company/identity): add vision/mission/core_values columns to workspaces"
```

---

### Task 2: Service layer — mở rộng Workspace + hàm update

**Files:**
- Modify: `services/company/identity/services/workspace.service.ts`
- Test: `services/company/identity/tests/workspace.test.ts`

**Interfaces:**
- Consumes: `identityWorkspaces.vision/.mission/.coreValues` (Task 1), `resolveTenantContext` từ `./tenant-context.service` (đã có).
- Produces: `Workspace.vision: string | null`, `.mission: string | null`, `.coreValues: string | null`; hàm mới `updateWorkspaceCompanyIdentityRecord(params: UpdateWorkspaceCompanyIdentityParams): Promise<Workspace>` — dùng bởi Task 3.

- [ ] **Step 1: Viết test thất bại cho hàm update mới**

Thêm vào cuối `services/company/identity/tests/workspace.test.ts`:

Đặt các import cần thiết ở đầu file theo hướng dẫn ngay dưới code block này trước, rồi thêm block `describe` sau:

```ts
describe("updateWorkspaceCompanyIdentityRecord", () => {
  it("persists vision/mission/coreValues when all three are non-empty", async () => {
    const session = await createTestSession({ displayName: "Identity Save Test" });

    const updated = await updateWorkspaceCompanyIdentityRecord({
      workspaceId: session.workspaceId,
      authorization: `Bearer ${session.accessToken}`,
      vision: "Trở thành nền tảng số 1 cho founder Việt Nam",
      mission: "Trao quyền cho founder ra quyết định bằng dữ liệu thật",
      coreValues: "Minh bạch, Tốc độ, Lấy khách hàng làm trung tâm",
    });

    expect(updated.vision).toBe("Trở thành nền tảng số 1 cho founder Việt Nam");
    expect(updated.mission).toBe("Trao quyền cho founder ra quyết định bằng dữ liệu thật");
    expect(updated.coreValues).toBe("Minh bạch, Tốc độ, Lấy khách hàng làm trung tâm");

    const refetched = await getWorkspaceRecord(session.workspaceId);
    expect(refetched.vision).toBe(updated.vision);
  });

  it("rejects when any of the three fields is empty after trim", async () => {
    const session = await createTestSession({ displayName: "Identity Reject Test" });

    await expect(
      updateWorkspaceCompanyIdentityRecord({
        workspaceId: session.workspaceId,
        authorization: `Bearer ${session.accessToken}`,
        vision: "  ",
        mission: "Mission hợp lệ",
        coreValues: "Values hợp lệ",
      })
    ).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const session = await createTestSession({ displayName: "Identity Non Member Test" });
    const otherWorkspace = await createWorkspaceRecord({ name: "Other Workspace" });

    await expect(
      updateWorkspaceCompanyIdentityRecord({
        workspaceId: otherWorkspace.id,
        authorization: `Bearer ${session.accessToken}`,
        vision: "Vision",
        mission: "Mission",
        coreValues: "Values",
      })
    ).rejects.toThrow();
  });
});
```

File test hiện tại chỉ import từ handler (`import { createWorkspace, getWorkspace } from "../handlers/workspace.handler";`), CHƯA import gì từ service — thêm 2 dòng import mới ở đầu file (không xoá dòng import handler đã có):

```ts
import { createTestSession } from "./helpers/test-session";
import {
  createWorkspaceRecord,
  getWorkspaceRecord,
  updateWorkspaceCompanyIdentityRecord,
} from "../services/workspace.service";
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd services/company && WORKSPACE_DATABASE_URL="postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable" npx vitest run identity/tests/workspace.test.ts`
Expected: FAIL — `updateWorkspaceCompanyIdentityRecord is not a function` (chưa export).

- [ ] **Step 3: Cài đặt hàm trong service**

Trong `services/company/identity/services/workspace.service.ts`:

1) Thêm 3 field vào interface `Workspace` (sau `platformWorkspaceId`):

```ts
export interface Workspace {
  id: string;
  name: string;
  slug: string | null;
  status: string;
  runtimeMode: string;
  syncPolicy: string;
  syncStatus: string;
  stageVersion: number;
  primaryLegalEntityId: string | null;
  lifecycleStage: string;
  stageEnteredAt: string | null;
  platformWorkspaceId: string | null;
  vision: string | null;
  mission: string | null;
  coreValues: string | null;
  archivedAt: string | null;
  createdAt: string;
}
```

2) Thêm cột vào `WORKSPACE_VIEW_COLUMNS` (sau `platformWorkspaceId`):

```ts
const WORKSPACE_VIEW_COLUMNS = {
  id: identityWorkspaces.id,
  name: identityWorkspaces.name,
  slug: identityWorkspaces.slug,
  status: identityWorkspaces.status,
  runtimeMode: identityWorkspaces.runtimeMode,
  syncPolicy: identityWorkspaces.syncPolicy,
  syncStatus: identityWorkspaces.syncStatus,
  stageVersion: identityWorkspaces.stageVersion,
  primaryLegalEntityId: identityWorkspaces.primaryLegalEntityId,
  lifecycleStage: identityWorkspaces.lifecycleStage,
  stageEnteredAt: identityWorkspaces.stageEnteredAt,
  platformWorkspaceId: identityWorkspaces.platformWorkspaceId,
  vision: identityWorkspaces.vision,
  mission: identityWorkspaces.mission,
  coreValues: identityWorkspaces.coreValues,
  archivedAt: identityWorkspaces.archivedAt,
  createdAt: identityWorkspaces.createdAt,
} as const;
```

3) Cập nhật `mapWorkspaceRow` (thêm sau dòng `platformWorkspaceId: row.platformWorkspaceId ?? null,`):

```ts
    vision: row.vision ?? null,
    mission: row.mission ?? null,
    coreValues: row.coreValues ?? null,
```

4) Thêm import `resolveTenantContext` (đầu file, cạnh import hiện có):

```ts
import { resolveTenantContext } from "./tenant-context.service";
```

5) Thêm interface + hàm mới ở cuối file:

```ts
export interface UpdateWorkspaceCompanyIdentityParams {
  workspaceId: string | number;
  authorization?: string;
  vision: string;
  mission: string;
  coreValues: string;
}

export async function updateWorkspaceCompanyIdentityRecord(
  params: UpdateWorkspaceCompanyIdentityParams
): Promise<Workspace> {
  // Xác minh caller là member của đúng workspace này trước khi ghi.
  await resolveTenantContext({
    authorization: params.authorization,
    workspaceId: params.workspaceId,
  });

  const vision = params.vision.trim();
  const mission = params.mission.trim();
  const coreValues = params.coreValues.trim();
  if (!vision || !mission || !coreValues) {
    throw APIError.invalidArgument(
      "vision, mission, and coreValues must all be non-empty"
    );
  }

  const [row] = await db
    .update(identityWorkspaces)
    .set({ vision, mission, coreValues, updatedAt: new Date() })
    .where(eq(identityWorkspaces.id, BigInt(params.workspaceId)))
    .returning(WORKSPACE_VIEW_COLUMNS);

  if (!row) throw APIError.notFound(`workspace ${params.workspaceId} not found`);
  return mapWorkspaceRow(row);
}
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd services/company && WORKSPACE_DATABASE_URL="postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable" npx vitest run identity/tests/workspace.test.ts`
Expected: PASS toàn bộ, bao gồm 2 test cũ (`createWorkspace`, `getWorkspace`) và 3 test mới.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/identity/services/workspace.service.ts services/company/identity/tests/workspace.test.ts
git commit -m "feat(company/identity): add updateWorkspaceCompanyIdentityRecord service"
```

---

### Task 3: Handler — expose PATCH endpoint

**Files:**
- Modify: `services/company/identity/handlers/workspace.handler.ts`
- Test: `services/company/identity/tests/workspace.test.ts`

**Interfaces:**
- Consumes: `updateWorkspaceCompanyIdentityRecord` (Task 2).
- Produces: `PATCH /identity/workspaces/:id/company-identity` (`expose: true`) — dùng bởi frontend Task 5. `GET /identity/workspaces/:id` (đã có) giờ trả thêm `vision`/`mission`/`coreValues` tự động (vì dùng chung `Workspace`/`mapWorkspaceRow`).

- [ ] **Step 1: Viết test thất bại gọi qua handler (không chỉ service)**

Thêm vào `services/company/identity/tests/workspace.test.ts`:

```ts
import { updateWorkspaceCompanyIdentity } from "../handlers/workspace.handler";

describe("updateWorkspaceCompanyIdentity handler", () => {
  it("exposes PATCH .../company-identity and returns the updated workspace", async () => {
    const session = await createTestSession({ displayName: "Identity Handler Test" });

    const updated = await updateWorkspaceCompanyIdentity({
      id: session.workspaceId,
      authorization: `Bearer ${session.accessToken}`,
      vision: "Vision qua handler",
      mission: "Mission qua handler",
      coreValues: "Values qua handler",
    });

    expect(updated.id).toBe(session.workspaceId);
    expect(updated.vision).toBe("Vision qua handler");
  });
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd services/company && WORKSPACE_DATABASE_URL="postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable" npx vitest run identity/tests/workspace.test.ts`
Expected: FAIL — `updateWorkspaceCompanyIdentity is not a function` (chưa export từ handler).

- [ ] **Step 3: Thêm handler**

Trong `services/company/identity/handlers/workspace.handler.ts`, thêm export mới ở cuối file:

```ts
export const updateWorkspaceCompanyIdentity = api(
  { method: "PATCH", path: "/identity/workspaces/:id/company-identity", expose: true },
  async ({
    id,
    authorization,
    vision,
    mission,
    coreValues,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    vision: string;
    mission: string;
    coreValues: string;
  }): Promise<Workspace> => {
    return updateWorkspaceCompanyIdentityRecord({
      workspaceId: id,
      authorization,
      vision,
      mission,
      coreValues,
    });
  }
);
```

Và cập nhật import ở đầu file (thêm `updateWorkspaceCompanyIdentityRecord`):

```ts
import {
  Workspace,
  CreateWorkspaceParams,
  createWorkspaceRecord,
  getWorkspaceRecord,
  updateWorkspaceCompanyIdentityRecord,
  WorkspacePlatformCompanyResponse,
  getWorkspacePlatformCompany,
} from "../services/workspace.service";
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd services/company && WORKSPACE_DATABASE_URL="postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable" npx vitest run identity/tests/workspace.test.ts`
Expected: PASS toàn bộ (6 test: 2 cũ + 3 Task 2 + 1 Task 3).

- [ ] **Step 5: Chạy toàn bộ suite company để chắc không phá gì khác**

Run: `cd services/company && encore test`
Expected: PASS toàn bộ, không có test nào đỏ do thay đổi `Workspace` interface.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/identity/handlers/workspace.handler.ts services/company/identity/tests/workspace.test.ts
git commit -m "feat(company/identity): expose PATCH /identity/workspaces/:id/company-identity"
```

---

### Task 4: Frontend model — WorkspaceCompanyIdentity

**Files:**
- Create: `frontend/lib/data/models/workspace_company_identity_model.dart`
- Test: `frontend/test/workspace_company_identity_model_test.dart`

**Interfaces:**
- Produces: `class WorkspaceCompanyIdentity { workspaceId, vision, mission, coreValues }`, factory `.fromJson`, getter `bool get isComplete` — dùng bởi Task 5, 6, 9.

- [ ] **Step 1: Viết test thất bại**

```dart
// frontend/test/workspace_company_identity_model_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/workspace_company_identity_model.dart';

void main() {
  group('WorkspaceCompanyIdentity', () {
    test('fromJson parses vision/mission/coreValues from camelCase keys', () {
      final model = WorkspaceCompanyIdentity.fromJson({
        'id': 'ws_1',
        'vision': 'Vision text',
        'mission': 'Mission text',
        'coreValues': 'Values text',
      });

      expect(model.workspaceId, 'ws_1');
      expect(model.vision, 'Vision text');
      expect(model.mission, 'Mission text');
      expect(model.coreValues, 'Values text');
    });

    test('isComplete is true only when all three fields are non-empty', () {
      const complete = WorkspaceCompanyIdentity(
        workspaceId: 'ws_1',
        vision: 'v',
        mission: 'm',
        coreValues: 'c',
      );
      expect(complete.isComplete, isTrue);

      const missingMission = WorkspaceCompanyIdentity(
        workspaceId: 'ws_1',
        vision: 'v',
        mission: '   ',
        coreValues: 'c',
      );
      expect(missingMission.isComplete, isFalse);

      const nullFields = WorkspaceCompanyIdentity(workspaceId: 'ws_1');
      expect(nullFields.isComplete, isFalse);
    });
  });
}
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/workspace_company_identity_model_test.dart`
Expected: FAIL — không tìm thấy file `workspace_company_identity_model.dart`.

- [ ] **Step 3: Viết model**

```dart
// frontend/lib/data/models/workspace_company_identity_model.dart
class WorkspaceCompanyIdentity {
  const WorkspaceCompanyIdentity({
    required this.workspaceId,
    this.vision,
    this.mission,
    this.coreValues,
  });

  final String workspaceId;
  final String? vision;
  final String? mission;
  final String? coreValues;

  bool get isComplete =>
      (vision?.trim().isNotEmpty ?? false) &&
      (mission?.trim().isNotEmpty ?? false) &&
      (coreValues?.trim().isNotEmpty ?? false);

  factory WorkspaceCompanyIdentity.fromJson(Map<String, dynamic> json) {
    return WorkspaceCompanyIdentity(
      workspaceId: json['id']?.toString() ?? '',
      vision: json['vision'] as String?,
      mission: json['mission'] as String?,
      coreValues: json['coreValues'] as String?,
    );
  }
}
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/workspace_company_identity_model_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/data/models/workspace_company_identity_model.dart frontend/test/workspace_company_identity_model_test.dart
git commit -m "feat(frontend): add WorkspaceCompanyIdentity model"
```

---

### Task 5: Frontend service — CompanyIdentityService (fetch/save)

**Files:**
- Create: `frontend/lib/modules/onboarding/services/company_identity_service.dart`
- Test: `frontend/test/company_identity_service_test.dart`

**Interfaces:**
- Consumes: `WorkspaceCompanyIdentity` (Task 4), `ApiClient.get`/`.patch` (`core/network/api_client.dart`, đã có).
- Produces: `class CompanyIdentityService { Future<WorkspaceCompanyIdentity> fetch(String workspaceId); Future<WorkspaceCompanyIdentity> save(String workspaceId, {required String vision, required String mission, required String coreValues}); }`, `class CompanyIdentityException implements Exception` — dùng bởi Task 6, 9.

- [ ] **Step 1: Viết test thất bại**

```dart
// frontend/test/company_identity_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/services/company_identity_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  test('fetch returns a WorkspaceCompanyIdentity from GET /identity/workspaces/:id', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/identity/workspaces/ws_1');
      return http.Response(
        '{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    final result = await CompanyIdentityService().fetch('ws_1');
    expect(result.vision, 'V');
    expect(result.isComplete, isTrue);
  });

  test('fetch throws CompanyIdentityException on non-200', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"detail":"not found"}', 404);
    });

    expect(
      () => CompanyIdentityService().fetch('ws_missing'),
      throwsA(isA<CompanyIdentityException>()),
    );
  });

  test('save PATCHes company-identity with camelCase body and returns the updated model', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'PATCH');
      expect(request.url.path, '/identity/workspaces/ws_1/company-identity');
      expect(
        request.body,
        '{"vision":"V","mission":"M","coreValues":"C"}',
      );
      return http.Response(
        '{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    final result = await CompanyIdentityService().save(
      'ws_1',
      vision: 'V',
      mission: 'M',
      coreValues: 'C',
    );
    expect(result.isComplete, isTrue);
  });

  test('save throws CompanyIdentityException on non-200', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"detail":"vision, mission, and coreValues must all be non-empty"}', 400);
    });

    expect(
      () => CompanyIdentityService().save('ws_1', vision: '', mission: 'M', coreValues: 'C'),
      throwsA(isA<CompanyIdentityException>()),
    );
  });
}
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/company_identity_service_test.dart`
Expected: FAIL — không tìm thấy file `company_identity_service.dart`.

- [ ] **Step 3: Viết service**

```dart
// frontend/lib/modules/onboarding/services/company_identity_service.dart
import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../../../data/models/workspace_company_identity_model.dart';

class CompanyIdentityException implements Exception {
  CompanyIdentityException(this.message);
  final String message;

  @override
  String toString() => message;
}

/// Đọc/ghi Vision/Mission/Core Values cấp workspace
/// (`services/company/identity` — `GET`/`PATCH /identity/workspaces/:id`).
class CompanyIdentityService {
  Future<WorkspaceCompanyIdentity> fetch(String workspaceId) async {
    final res = await ApiClient.get('/identity/workspaces/$workspaceId');
    if (res.statusCode != 200) {
      throw CompanyIdentityException(
        'Không tải được thông tin workspace (HTTP ${res.statusCode}).',
      );
    }
    return WorkspaceCompanyIdentity.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<WorkspaceCompanyIdentity> save(
    String workspaceId, {
    required String vision,
    required String mission,
    required String coreValues,
  }) async {
    final res = await ApiClient.patch(
      '/identity/workspaces/$workspaceId/company-identity',
      body: {
        'vision': vision,
        'mission': mission,
        'coreValues': coreValues,
      },
    );
    if (res.statusCode != 200) {
      throw CompanyIdentityException(
        'Không lưu được Vision/Mission/Values (HTTP ${res.statusCode}).',
      );
    }
    return WorkspaceCompanyIdentity.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }
}
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/company_identity_service_test.dart`
Expected: PASS toàn bộ 4 test.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/onboarding/services/company_identity_service.dart frontend/test/company_identity_service_test.dart
git commit -m "feat(frontend): add CompanyIdentityService fetch/save"
```

---

### Task 6: Frontend widget — CompanyIdentityModal (nhập thủ công + lưu)

**Files:**
- Create: `frontend/lib/modules/onboarding/widgets/company_identity_modal.dart`
- Test: `frontend/test/company_identity_modal_test.dart`

**Interfaces:**
- Consumes: `CompanyIdentityService` (Task 5), `WorkspaceCompanyIdentity` (Task 4).
- Produces: `class CompanyIdentityModal extends StatefulWidget { final String workspaceId; const CompanyIdentityModal({required this.workspaceId, super.key}); }` — dùng bởi Task 8 (mở rộng thêm nút AI) và Task 9/10 (gate mở modal này).

- [ ] **Step 1: Viết test thất bại**

```dart
// frontend/test/company_identity_modal_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/widgets/company_identity_modal.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  Future<void> pumpModal(WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: CompanyIdentityModal(workspaceId: 'ws_1')),
      ),
    );
  }

  testWidgets('Save button is disabled until all three fields are filled', (tester) async {
    await pumpModal(tester);

    final saveBtn = find.widgetWithText(ElevatedButton, 'Lưu');
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('company_identity_vision_field')), 'Vision');
    await tester.enterText(find.byKey(const Key('company_identity_mission_field')), 'Mission');
    await tester.pump();
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('company_identity_values_field')), 'Values');
    await tester.pump();
    expect(tester.widget<ElevatedButton>(saveBtn).onPressed, isNotNull);
  });

  testWidgets('Save calls CompanyIdentityService.save with entered text', (tester) async {
    Map<String, dynamic>? sentBody;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'PATCH') {
        sentBody = Map<String, dynamic>.from(
          Uri.splitQueryString(request.body.replaceAll('"', '')),
        );
        return http.Response(
          '{"id":"ws_1","vision":"Vision text","mission":"Mission text","coreValues":"Values text"}',
          200,
        );
      }
      return http.Response('not found', 404);
    });

    await pumpModal(tester);
    await tester.enterText(find.byKey(const Key('company_identity_vision_field')), 'Vision text');
    await tester.enterText(find.byKey(const Key('company_identity_mission_field')), 'Mission text');
    await tester.enterText(find.byKey(const Key('company_identity_values_field')), 'Values text');
    await tester.pump();

    await tester.tap(find.widgetWithText(ElevatedButton, 'Lưu'));
    await tester.pump();
    await tester.pump();

    expect(sentBody, isNotNull);
    expect(sentBody!['vision'], 'Vision text');
  });

  testWidgets('modal has no dismiss affordance (blocking)', (tester) async {
    await pumpModal(tester);
    expect(find.byIcon(Icons.close), findsNothing);
    expect(find.byType(BackButton), findsNothing);
  });
}
```

`request.body` là JSON string; parse lỏng lẻo bằng `Uri.splitQueryString` sau khi bỏ dấu `"` chỉ để lấy nhanh giá trị trong test — nếu thấy khó đọc, thay bằng `jsonDecode(request.body)` (đã có `dart:convert` sẵn trong môi trường test) cho rõ ràng hơn; giữ đúng ý: assert `sentBody['vision'] == 'Vision text'`.

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/company_identity_modal_test.dart`
Expected: FAIL — không tìm thấy file `company_identity_modal.dart`.

- [ ] **Step 3: Viết widget**

```dart
// frontend/lib/modules/onboarding/widgets/company_identity_modal.dart
import 'package:flutter/material.dart';

import '../services/company_identity_service.dart';

/// Modal chặn cứng bắt founder điền Vision/Mission/Core Values — dùng chung
/// cho cả luồng "workspace vừa tạo" lẫn "đăng nhập vào workspace cũ thiếu
/// dữ liệu" (gate duy nhất, xem HubAuthMixin.ensureAuthenticated).
/// KHÔNG có nút đóng — founder phải lưu xong mới rời được màn hình này.
class CompanyIdentityModal extends StatefulWidget {
  const CompanyIdentityModal({required this.workspaceId, super.key});

  final String workspaceId;

  @override
  State<CompanyIdentityModal> createState() => _CompanyIdentityModalState();
}

class _CompanyIdentityModalState extends State<CompanyIdentityModal> {
  final _visionController = TextEditingController();
  final _missionController = TextEditingController();
  final _valuesController = TextEditingController();
  final _service = CompanyIdentityService();

  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    for (final c in [_visionController, _missionController, _valuesController]) {
      c.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    _visionController.dispose();
    _missionController.dispose();
    _valuesController.dispose();
    super.dispose();
  }

  bool get _canSave =>
      _visionController.text.trim().isNotEmpty &&
      _missionController.text.trim().isNotEmpty &&
      _valuesController.text.trim().isNotEmpty &&
      !_isSaving;

  Future<void> _save() async {
    if (!_canSave) return;
    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });
    try {
      await _service.save(
        widget.workspaceId,
        vision: _visionController.text.trim(),
        mission: _missionController.text.trim(),
        coreValues: _valuesController.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _errorMessage = 'Không lưu được: $e');
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Thiết lập Vision / Mission / Core Values',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Founder cần điền đủ 3 mục này trước khi vào Command Center.',
              ),
              const SizedBox(height: 16),
              TextField(
                key: const Key('company_identity_vision_field'),
                controller: _visionController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Vision'),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('company_identity_mission_field'),
                controller: _missionController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Mission'),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('company_identity_values_field'),
                controller: _valuesController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Core Values'),
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 20),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton(
                  onPressed: _canSave ? _save : null,
                  child: _isSaving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Lưu'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/company_identity_modal_test.dart`
Expected: PASS toàn bộ 3 test.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/onboarding/widgets/company_identity_modal.dart frontend/test/company_identity_modal_test.dart
git commit -m "feat(frontend): add blocking CompanyIdentityModal"
```

---

### Task 7: Frontend — pure parser cho draft AI (parseCompanyIdentityDraft)

**Files:**
- Create: `frontend/lib/modules/onboarding/services/company_identity_draft_parser.dart`
- Test: `frontend/test/company_identity_draft_parser_test.dart`

**Interfaces:**
- Produces: `class CompanyIdentityDraft { final String? vision, mission, coreValues; }`, hàm `CompanyIdentityDraft parseCompanyIdentityDraft(String text)` — dùng bởi Task 8.

- [ ] **Step 1: Viết test thất bại**

```dart
// frontend/test/company_identity_draft_parser_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/onboarding/services/company_identity_draft_parser.dart';

void main() {
  group('parseCompanyIdentityDraft', () {
    test('parses well-formed VISION/MISSION/VALUES sections', () {
      const text = 'VISION: Tro thanh so 1.\n\n'
          'MISSION: Trao quyen cho founder.\n\n'
          'VALUES: Minh bach, Toc do.';

      final draft = parseCompanyIdentityDraft(text);

      expect(draft.vision, 'Tro thanh so 1.');
      expect(draft.mission, 'Trao quyen cho founder.');
      expect(draft.coreValues, 'Minh bach, Toc do.');
    });

    test('is case-insensitive on the section labels', () {
      const text = 'vision: A\nMission: B\nValues: C';
      final draft = parseCompanyIdentityDraft(text);
      expect(draft.vision, 'A');
      expect(draft.mission, 'B');
      expect(draft.coreValues, 'C');
    });

    test('returns null fields when labels are missing (malformed reply)', () {
      const text = 'Day la mot cau tra loi tu do khong theo dinh dang.';
      final draft = parseCompanyIdentityDraft(text);
      expect(draft.vision, isNull);
      expect(draft.mission, isNull);
      expect(draft.coreValues, isNull);
    });
  });
}
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/company_identity_draft_parser_test.dart`
Expected: FAIL — không tìm thấy file `company_identity_draft_parser.dart`.

- [ ] **Step 3: Viết parser**

```dart
// frontend/lib/modules/onboarding/services/company_identity_draft_parser.dart

/// Kết quả parse câu trả lời tự do của AI thành 3 khối Vision/Mission/Values.
/// Field null nghĩa là AI không trả lời đúng định dạng — caller (modal) tự
/// quyết định fallback (đổ nguyên văn vào ô Vision), parser không tự đoán.
class CompanyIdentityDraft {
  const CompanyIdentityDraft({this.vision, this.mission, this.coreValues});

  final String? vision;
  final String? mission;
  final String? coreValues;

  bool get isComplete =>
      (vision?.trim().isNotEmpty ?? false) &&
      (mission?.trim().isNotEmpty ?? false) &&
      (coreValues?.trim().isNotEmpty ?? false);
}

String? _extractSection(String text, String label, List<String> nextLabels) {
  final labelMatch = RegExp('$label\\s*:', caseSensitive: false).firstMatch(text);
  if (labelMatch == null) return null;

  var end = text.length;
  for (final next in nextLabels) {
    final nextMatch =
        RegExp('$next\\s*:', caseSensitive: false).firstMatch(text.substring(labelMatch.end));
    if (nextMatch != null) {
      final absoluteStart = labelMatch.end + nextMatch.start;
      if (absoluteStart < end) end = absoluteStart;
    }
  }
  final section = text.substring(labelMatch.end, end).trim();
  return section.isEmpty ? null : section;
}

/// Kỳ vọng AI trả lời đúng 3 dòng `VISION:`/`MISSION:`/`VALUES:` (prompt gửi
/// đi ở Task 8 yêu cầu định dạng này rõ ràng). Không phụ thuộc thứ tự các
/// khối còn lại khi cắt biên mỗi section, chỉ cần đúng nhãn xuất hiện.
CompanyIdentityDraft parseCompanyIdentityDraft(String text) {
  return CompanyIdentityDraft(
    vision: _extractSection(text, 'VISION', ['MISSION', 'VALUES']),
    mission: _extractSection(text, 'MISSION', ['VALUES']),
    coreValues: _extractSection(text, 'VALUES', []),
  );
}
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/company_identity_draft_parser_test.dart`
Expected: PASS toàn bộ 3 test.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/onboarding/services/company_identity_draft_parser.dart frontend/test/company_identity_draft_parser_test.dart
git commit -m "feat(frontend): add parseCompanyIdentityDraft pure parser"
```

---

### Task 8: Frontend — nút "Nhờ AI soạn" trong CompanyIdentityModal

**Files:**
- Modify: `frontend/lib/modules/onboarding/widgets/company_identity_modal.dart` (Task 6)
- Test: `frontend/test/company_identity_modal_test.dart` (Task 6)

**Interfaces:**
- Consumes: `AgentChatService` (`frontend/lib/modules/chat/services/agent_chat_service.dart`, đã có — `createConversation`, `sendMessage`, `streamRunEvents`), `DataAccessDeclaration`/`DataAccessCategory` (`frontend/lib/modules/chat/models/data_access_declaration.dart`, đã có), `parseCompanyIdentityDraft` (Task 7).
- Produces: nút "Nhờ AI soạn" trong `CompanyIdentityModal` điền sẵn 3 ô form.

- [ ] **Step 1: Viết test thất bại (thêm vào `company_identity_modal_test.dart`)**

```dart
testWidgets('"Nhờ AI soạn" fills the three fields from a well-formed SSE reply', (tester) async {
  ApiClient.client = MockClient((request) async {
    final path = request.url.path;
    if (path == '/agent/conversations' && request.method == 'POST') {
      return http.Response(
        '{"id":"conv_1","workspace_id":"ws1","created_by_principal":"p1",'
        '"title":"Company Identity Draft","created_at":"2026-08-31T00:00:00Z",'
        '"updated_at":"2026-08-31T00:00:00Z"}',
        201,
      );
    }
    if (path == '/agent/conversations/conv_1/messages' && request.method == 'POST') {
      return http.Response('{"run_id":"run_1","status":"accepted"}', 202);
    }
    if (path == '/agent/runs/run_1/events') {
      return http.Response(
        'event: message.delta\n'
        'data: {"payload":{"delta":"VISION: Tro thanh so 1.\\nMISSION: Trao quyen cho founder.\\nVALUES: Minh bach, Toc do."}}\n\n'
        'event: run.completed\n'
        'data: {"payload":{"output":null}}\n\n',
        200,
        headers: {'content-type': 'text/event-stream'},
      );
    }
    return http.Response('not found', 404);
  });

  await pumpModal(tester);
  await tester.tap(find.widgetWithText(OutlinedButton, 'Nhờ AI soạn'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));

  expect(find.text('Tro thanh so 1.'), findsOneWidget);
  expect(find.text('Trao quyen cho founder.'), findsOneWidget);
  expect(find.text('Minh bach, Toc do.'), findsOneWidget);
});

testWidgets('"Nhờ AI soạn" falls back to dumping raw text into Vision when reply is malformed', (tester) async {
  ApiClient.client = MockClient((request) async {
    final path = request.url.path;
    if (path == '/agent/conversations' && request.method == 'POST') {
      return http.Response(
        '{"id":"conv_1","workspace_id":"ws1","created_by_principal":"p1",'
        '"title":"Company Identity Draft","created_at":"2026-08-31T00:00:00Z",'
        '"updated_at":"2026-08-31T00:00:00Z"}',
        201,
      );
    }
    if (path == '/agent/conversations/conv_1/messages' && request.method == 'POST') {
      return http.Response('{"run_id":"run_1","status":"accepted"}', 202);
    }
    if (path == '/agent/runs/run_1/events') {
      return http.Response(
        'event: message.delta\n'
        'data: {"payload":{"delta":"Cau tra loi tu do khong dung dinh dang."}}\n\n'
        'event: run.completed\n'
        'data: {"payload":{"output":null}}\n\n',
        200,
        headers: {'content-type': 'text/event-stream'},
      );
    }
    return http.Response('not found', 404);
  });

  await pumpModal(tester);
  await tester.tap(find.widgetWithText(OutlinedButton, 'Nhờ AI soạn'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));

  expect(
    find.textContaining('Cau tra loi tu do khong dung dinh dang.'),
    findsOneWidget,
  );
});
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/company_identity_modal_test.dart`
Expected: FAIL — không tìm thấy nút `OutlinedButton` với text `'Nhờ AI soạn'`.

- [ ] **Step 3: Mở rộng widget**

Sửa `frontend/lib/modules/onboarding/widgets/company_identity_modal.dart`:

1) Thêm import ở đầu file:

```dart
import 'dart:async';

import '../../chat/models/data_access_declaration.dart';
import '../../chat/services/agent_chat_service.dart';
import 'company_identity_draft_parser.dart';
```

(giữ nguyên import `flutter/material.dart` và `../services/company_identity_service.dart` đã có)

2) Trong `_CompanyIdentityModalState`, thêm field mới ngay dưới `_service`:

```dart
  final _chatService = AgentChatService();
  String? _conversationId;
  StreamSubscription<Map<String, dynamic>>? _aiSseSubscription;
  bool _isAiLoading = false;

  static const _aiDataAccess = DataAccessDeclaration(
    categories: {DataAccessCategory.businessConfidential},
  );
```

3) Cập nhật `dispose()`:

```dart
  @override
  void dispose() {
    _aiSseSubscription?.cancel();
    _visionController.dispose();
    _missionController.dispose();
    _valuesController.dispose();
    super.dispose();
  }
```

4) Thêm method `_askAiToDraft` và `_subscribeAiSse` (trước `build`):

```dart
  Future<void> _askAiToDraft() async {
    setState(() {
      _isAiLoading = true;
      _errorMessage = null;
    });
    try {
      _conversationId ??= (await _chatService.createConversation(
        title: 'Company Identity Draft',
        activeAgentProfile: 'strategy',
      ))
          ?.id;
      final conversationId = _conversationId;
      if (conversationId == null) {
        throw Exception('Không tạo được conversation với COSA runtime.');
      }

      final response = await _chatService.sendMessage(
        conversationId,
        content:
            'Hãy soạn Vision, Mission và Core Values cho công ty này. '
            'Trả lời ĐÚNG định dạng sau, mỗi mục một dòng bắt đầu bằng nhãn viết hoa:\n'
            'VISION: <nội dung>\nMISSION: <nội dung>\nVALUES: <nội dung>',
        dataAccess: _aiDataAccess,
      );
      final runId = response?['run_id']?.toString();
      if (runId == null) {
        throw Exception('COSA runtime không trả về run_id.');
      }
      _subscribeAiSse(runId);
    } catch (e) {
      setState(() {
        _errorMessage = 'Không nhờ được AI soạn: $e';
        _isAiLoading = false;
      });
    }
  }

  void _subscribeAiSse(String runId) {
    final buffer = StringBuffer();
    _aiSseSubscription?.cancel();
    _aiSseSubscription = _chatService.streamRunEvents(runId).listen(
      (event) {
        final eventType = event['event_type']?.toString() ?? '';
        final payload = (event['payload'] as Map<String, dynamic>?) ?? {};
        if (eventType == 'message.delta') {
          buffer.write(payload['delta']?.toString() ?? '');
        } else if (eventType == 'run.completed' ||
            eventType == 'run.failed' ||
            eventType == 'run.cancelled') {
          _applyAiDraft(buffer.toString());
        }
      },
      onError: (_) => setState(() => _isAiLoading = false),
      onDone: () => setState(() => _isAiLoading = false),
    );
  }

  void _applyAiDraft(String rawText) {
    final draft = parseCompanyIdentityDraft(rawText);
    setState(() {
      if (draft.isComplete) {
        _visionController.text = draft.vision!;
        _missionController.text = draft.mission!;
        _valuesController.text = draft.coreValues!;
      } else if (rawText.trim().isNotEmpty) {
        _visionController.text =
            '[AI trả lời không đúng định dạng — vui lòng tách thủ công]\n\n$rawText';
      }
      _isAiLoading = false;
    });
  }
```

5) Thêm nút "Nhờ AI soạn" trong `build()`, ngay trước ô Vision (sau đoạn `Text` mô tả, trước `TextField` vision):

```dart
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  onPressed: _isAiLoading ? null : _askAiToDraft,
                  child: _isAiLoading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Nhờ AI soạn'),
                ),
              ),
              const SizedBox(height: 12),
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/company_identity_modal_test.dart`
Expected: PASS toàn bộ 5 test (3 từ Task 6 + 2 mới).

- [ ] **Step 5: `dart analyze` để chắc không có unused import/warning**

Run: `cd frontend && dart analyze lib/modules/onboarding/widgets/company_identity_modal.dart lib/modules/onboarding/services/company_identity_draft_parser.dart`
Expected: `No issues found!`

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/onboarding/widgets/company_identity_modal.dart frontend/test/company_identity_modal_test.dart
git commit -m "feat(frontend): AI-assisted draft for Vision/Mission/Values via AgentChatService"
```

---

### Task 9: Frontend — CompanyIdentityGate.checkAndPrompt

**Files:**
- Create: `frontend/lib/modules/onboarding/services/company_identity_gate.dart`
- Test: `frontend/test/company_identity_gate_test.dart`

**Interfaces:**
- Consumes: `CompanyIdentityService` (Task 5), `CompanyIdentityModal` (Task 6/8).
- Produces: `class CompanyIdentityGate { static Future<void> checkAndPrompt(String workspaceId, {CompanyIdentityService? service, Future<void> Function(String workspaceId)? showModal}) }` — dùng bởi Task 10.

Tham số `showModal` cho phép test inject một hàm giả để verify gate **có gọi** hiển thị modal khi thiếu dữ liệu mà không cần dựng `Get.dialog`/navigator thật; mặc định (production) dùng `Get.dialog`.

- [ ] **Step 1: Viết test thất bại**

```dart
// frontend/test/company_identity_gate_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/services/company_identity_gate.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  test('calls showModal when the workspace is missing vision/mission/coreValues', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"id":"ws_1","vision":null,"mission":null,"coreValues":null}', 200);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async {
        shown = true;
        expect(workspaceId, 'ws_1');
      },
    );

    expect(shown, isTrue);
  });

  test('does not call showModal when the workspace already has all three fields', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}', 200);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async => shown = true,
    );

    expect(shown, isFalse);
  });

  test('fails open (does not call showModal) when the fetch itself errors', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('server error', 500);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async => shown = true,
    );

    expect(shown, isFalse);
  });
}
```

Quyết định thiết kế: **fail open** khi fetch lỗi (mạng chập chờn, backend tạm downtime) — founder không bị khoá app vì một request thất bại tạm thời; gate sẽ tự thử lại ở lần `ensureAuthenticated()` kế tiếp (mỗi lần Hub load).

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/company_identity_gate_test.dart`
Expected: FAIL — không tìm thấy file `company_identity_gate.dart`.

- [ ] **Step 3: Viết gate**

```dart
// frontend/lib/modules/onboarding/services/company_identity_gate.dart
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';

import '../widgets/company_identity_modal.dart';
import 'company_identity_service.dart';

/// Điểm gắn DUY NHẤT cho yêu cầu "workspace phải có Vision/Mission/Values" —
/// gọi từ HubAuthMixin.ensureAuthenticated() nên bắt cả 2 tình huống (workspace
/// vừa tạo / workspace cũ đăng nhập lại) bằng một logic. Fail-open khi fetch
/// lỗi — không khoá app vì một request tạm thời thất bại.
class CompanyIdentityGate {
  static Future<void> checkAndPrompt(
    String workspaceId, {
    CompanyIdentityService? service,
    Future<void> Function(String workspaceId)? showModal,
  }) async {
    final svc = service ?? CompanyIdentityService();
    try {
      final identity = await svc.fetch(workspaceId);
      if (identity.isComplete) return;
    } catch (e) {
      debugPrint('[CompanyIdentityGate] fetch error, fail-open: $e');
      return;
    }

    final show = showModal ?? _showBlockingModal;
    await show(workspaceId);
  }

  static Future<void> _showBlockingModal(String workspaceId) {
    return Get.dialog<void>(
      CompanyIdentityModal(workspaceId: workspaceId),
      barrierDismissible: false,
    );
  }
}
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/company_identity_gate_test.dart`
Expected: PASS toàn bộ 3 test.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/onboarding/services/company_identity_gate.dart frontend/test/company_identity_gate_test.dart
git commit -m "feat(frontend): add CompanyIdentityGate.checkAndPrompt"
```

---

### Task 10: Gắn gate vào HubAuthMixin.ensureAuthenticated()

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart`
- Test: `frontend/test/hologram_hub_test.dart` (thêm 1 test mới)

**Interfaces:**
- Consumes: `CompanyIdentityGate.checkAndPrompt` (Task 9), `SecureStorageService.read` (`core/services/secure_storage_service.dart`, đã có).

- [ ] **Step 1: Viết test thất bại**

Thêm vào `frontend/test/hologram_hub_test.dart`, trong `main()` (bên ngoài group hiện có, cùng cấp):

```dart
group('HologramHubController Company Identity Gate', () {
  test('ensureAuthenticated calls CompanyIdentityGate.checkAndPrompt with the stored workspace_id', () async {
    var promptedWorkspaceId = '';
    final controller = HologramHubController();
    // AuthService.isAuthenticated phụ thuộc trạng thái static toàn cục được
    // set qua AuthService.init()/setCachedToken ở nơi khác trong test suite;
    // ở đây chỉ verify gate được GỌI ĐÚNG workspace_id khi auth hợp lệ —
    // dùng setCachedToken trực tiếp để không phụ thuộc thứ tự chạy test khác.
    AuthService.setCachedToken('test_token');

    await controller.ensureAuthenticated(
      companyIdentityCheck: (workspaceId) async {
        promptedWorkspaceId = workspaceId;
      },
    );

    expect(promptedWorkspaceId, 'ws_123');
  });
});
```

Thêm import `package:frontend/modules/auth/services/auth_service.dart` ở đầu `hologram_hub_test.dart` nếu chưa có.

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `cd frontend && flutter test test/hologram_hub_test.dart`
Expected: FAIL — `ensureAuthenticated` chưa nhận tham số `companyIdentityCheck`.

- [ ] **Step 3: Sửa `ensureAuthenticated()`**

Trong `frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart`:

1) Thêm import ở đầu file:

```dart
import '../../../../core/services/secure_storage_service.dart';
import '../../../../modules/onboarding/services/company_identity_gate.dart';
```

2) Sửa signature + thân hàm `ensureAuthenticated`:

```dart
  Future<void> ensureAuthenticated({
    Future<void> Function(String workspaceId)? companyIdentityCheck,
  }) async {
    if (!AuthService.isAuthenticated) {
      RealtimeService.disconnect();
      await authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }
    final me = await authService.getMe();
    if (me == null) {
      debugPrint(
        '[HologramHub] Token không hợp lệ hoặc đã hết hạn -> Tự động chuyển về màn Đăng nhập',
      );
      RealtimeService.disconnect();
      await authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }
    if (me['display_name'] != null &&
        (me['display_name'] as String).isNotEmpty) {
      userName.value = me['display_name'] as String;
    }
    if (me['role'] != null) {
      userRole.value =
          me['role'] == 'admin' ? 'Founder Mode' : (me['role'] as String);
    }

    // Gate duy nhất cho yêu cầu "workspace phải có Vision/Mission/Values" —
    // bắt cả workspace vừa tạo lẫn workspace cũ thiếu dữ liệu. Chặn cho tới
    // khi founder điền xong (CompanyIdentityGate hiện modal non-dismissible).
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId != null && workspaceId.isNotEmpty) {
      final check = companyIdentityCheck ?? CompanyIdentityGate.checkAndPrompt;
      await check(workspaceId);
    }
  }
```

- [ ] **Step 4: Chạy lại test để xác nhận pass**

Run: `cd frontend && flutter test test/hologram_hub_test.dart`
Expected: PASS toàn bộ (test cũ + test mới).

- [ ] **Step 5: Chạy toàn bộ frontend test suite**

Run: `cd frontend && flutter test`
Expected: PASS toàn bộ (bao gồm các test đã có từ trước, không có regression).

- [ ] **Step 6: `dart analyze` toàn bộ thư mục đã đổi**

Run: `cd frontend && dart analyze lib/modules/onboarding lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart lib/data/models/workspace_company_identity_model.dart`
Expected: `No issues found!`

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart frontend/test/hologram_hub_test.dart
git commit -m "feat(frontend): gate Hub on workspace Vision/Mission/Values completeness"
```

---

## Sau khi hoàn tất toàn bộ 10 task

- [ ] Chạy full verify 2 phía:
  - Run: `cd services/company && encore test`
  - Run: `cd frontend && flutter test && flutter analyze`
  - Expected: cả hai PASS sạch, không regression.
- [ ] Thủ công verify 1 lần trên app thật (theo hướng dẫn CLAUDE.md — "chạy thử feature UI trước khi báo hoàn thành"): tạo workspace mới → xác nhận modal chặn hiện ngay khi vào Hub lần đầu → bấm "Nhờ AI soạn" → xác nhận 3 ô được điền (hoặc fallback hợp lý) → sửa tay nếu cần → Lưu → xác nhận vào được Hub bình thường → đăng xuất, đăng nhập lại → xác nhận modal KHÔNG hiện lại (đã đủ dữ liệu).
