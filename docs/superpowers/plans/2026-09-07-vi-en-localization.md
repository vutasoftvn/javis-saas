# VI–EN Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cung cấp giao diện và phản hồi agent VI–EN theo preference profile của từng người dùng, cùng module visibility tùy chọn cho Finance, Legal và CRM mà không làm thay đổi jurisdiction, kế toán, pháp lý hoặc authorization.

**Architecture:** COSA Control Plane là nguồn chuẩn cho `preferredLocale` và visibility theo workspace/người dùng. Flutter hydrate locale từ profile đã xác thực, cache giá trị không nhạy cảm để khởi động offline, và áp dụng GetX translation catalogue. Agent Platform chỉ nhận `RunRequest.locale` đã resolve có provenance; locale không được dùng cho tiền tệ, TT58, legal applicability hay quyền.

**Tech Stack:** Encore.ts, Drizzle/PostgreSQL, FastAPI/Pydantic, Python 3.11, Flutter/Dart, GetX, `intl`, pytest, Vitest, Flutter test.

**Spec:** [VI–EN Localization design](../specs/2026-09-07-vi-en-localization-design.md)

## Global Constraints

- Chỉ chấp nhận hai BCP-47 locale: `vi-VN` và `en-US`; mặc định/backfill là `vi-VN`.
- `profiles.preferred_locale` là nguồn chuẩn giữa các thiết bị; cache Flutter không phải credential và không ghi đè server sau lỗi mạng.
- Ngôn ngữ câu nhập không tự đổi ngôn ngữ phản hồi. Override chỉ hợp lệ khi client gửi trường cấu trúc `response_locale_override` cho đúng một message.
- Không suy ra currency, timezone, country, jurisdiction, legal rule, accounting regime, role hay capability từ locale.
- Không sửa dữ liệu Finance/Legal/CRM, TT58, VND, legal applicability, policy approval hoặc audit semantics trong release này.
- Module key mới chỉ là `finance`, `legal`, `crm`; `crm` map vào `WorkspaceModule.sales`. `workspaceEnabled && userVisible` chỉ kiểm soát discovery/UI, không phải authorization.
- Mọi endpoint `expose: true` phải xác thực caller, bind đúng workspace, và test nhánh cross-workspace; mutation workspace chỉ dành cho `founder`, `co-founder`, `admin`.
- Migration chỉ expand. Trước khi đặt số migration, xác minh sequence cao nhất tại `services/cosa/migrations/`; số `32` bên dưới chỉ đúng nếu chưa có migration mới.

---

## File structure

| Path | Responsibility |
|---|---|
| `services/cosa/migrations/32_profile_preferred_locale.up.sql` | Expand-only profile locale column/backfill giữ nguyên trải nghiệm hiện có. |
| `services/cosa/migrations/33_workspace_module_visibility.up.sql` | Expand-only workspace/user visibility tables và backfill giữ nguyên trải nghiệm hiện có. |
| `services/cosa/storage/schema.ts` | Drizzle models cho profile locale và visibility settings. |
| `services/cosa/services/auth.service.ts` | Validate, read, write `preferred_locale` chỉ cho principal. |
| `services/cosa/services/workspace-settings.service.ts` | Resolve visibility theo membership/operator; emit audit event cho workspace mutation. |
| `services/cosa/handlers/auth.handler.ts` | Expose DTO profile locale qua `/platform/auth/me`. |
| `apps/cosa/policies/profile_locale_client.py` | Đọc locale snapshot qua Control Plane delegation; không truy cập DB COSA trực tiếp. |
| `services/cosa/handlers/workspace-settings.handler.ts` | Endpoint visibility có typed input/output. |
| `frontend/lib/core/localization/*` | Supported locale, cache, controller và GetX translations. |
| `frontend/lib/main.dart` | Đăng ký `AppTranslations` và locale controller, bỏ locale hard-code. |
| `frontend/lib/modules/profile/*` | Hiển thị/chỉnh preference ngôn ngữ profile. |
| `frontend/lib/core/session/*` | Hydrate locale atomically từ identity profile sau xác thực. |
| `frontend/lib/core/services/voice_service.dart` | Derive language transcribe từ `LocaleController`, không còn default cố định `vi`. |
| `frontend/lib/core/services/module_visibility_controller.dart` | Fetch/cached state visibility được server resolve, không suy luận từ route. |
| `frontend/lib/core/routing/module_routes.dart` | Chặn route module bị ẩn bằng UX redirect, không thay authorization. |
| `frontend/lib/modules/dashboard/*` | Sidebar chỉ render entry có effective visibility và dùng translation key. |
| `apps/cosa/api/conversation_routes.py` | Parse/validate one-turn override, resolve server-side locale trước enqueue run. |
| `apps/cosa/worker/run_core.py` | Nhận locale resolved và đặt `RunRequest.locale`. |
| `apps/cosa/worker/autopilot_run.py`, `apps/cosa/worker/copilot_run.py` | Không hard-code tiếng Việt; carry locale có provenance cho background run. |
| `tests/**`, `services/cosa/tests/**`, `frontend/test/**` | Contract, tenancy, worker, widget và regression coverage. |

## Task 1: Persist and expose the user locale in Control Plane

**Files:**
- Create: `services/cosa/migrations/32_profile_preferred_locale.up.sql`
- Create: `services/cosa/migrations/32_profile_preferred_locale.down.sql`
- Modify: `services/cosa/storage/schema.ts:28-39`
- Modify: `services/cosa/services/auth.service.ts:22-65, 225-320`
- Modify: `services/cosa/handlers/auth.handler.ts:1-105`
- Create: `apps/cosa/policies/profile_locale_client.py`
- Create: `services/cosa/tests/auth-profile-locale.test.ts`
- Create: `tests/apps/cosa/policies/test_profile_locale_client.py`

**Interfaces:**

```ts
export const SUPPORTED_LOCALES = ["vi-VN", "en-US"] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export interface PlatformUserProfile {
  id: string;
  email: string | null;
  phone: string | null;
  full_name: string | null;
  preferred_locale: SupportedLocale;
}

export interface UpdateMeParams {
  preferred_locale?: SupportedLocale;
  phone?: string;
  full_name?: string;
  avatar_url?: string;
  headline?: string;
  bio?: string;
}

export interface LocaleSnapshot {
  workspace_id: string;
  preferred_locale: SupportedLocale;
}
```

- [ ] **Step 1: Write failing profile locale tests.**

```ts
async function createProfileForTest() {
  return registerPlatformUser({
    email: `locale-${Date.now()}-${Math.random()}@test.invalid`,
    password: "SecurePassword123",
    workspace_name: "Locale test workspace",
  });
}

it("defaults a new profile to vi-VN and returns it from GET /platform/auth/me", async () => {
  const session = await createProfileForTest();
  const me = await getPlatformUserProfile(session.user!.id);
  expect(me.preferred_locale).toBe("vi-VN");
});

it("changes only the authenticated caller locale", async () => {
  const alice = await createProfileForTest();
  const bob = await createProfileForTest();
  const changed = await updatePlatformUserProfile(alice.user!.id, { preferred_locale: "en-US" });
  expect(changed.preferred_locale).toBe("en-US");
  expect((await getPlatformUserProfile(bob.user!.id)).preferred_locale).toBe("vi-VN");
});

it("rejects unsupported locale without changing stored preference", async () => {
  const session = await createProfileForTest();
  await expect(updatePlatformUserProfile(session.user!.id, { preferred_locale: "fr-FR" as never })).rejects.toThrow();
  expect((await getPlatformUserProfile(session.user!.id)).preferred_locale).toBe("vi-VN");
});

it("returns a locale snapshot only for a caller that belongs to the workspace", async () => {
  const session = await createProfileForTest();
  const foreign = await createProfileForTest();
  const snapshot = await getLocaleSnapshotForWorkspace({
    workspaceId: session.platform_workspace_id!,
    authorization: `Bearer ${session.access_token}`,
  });
  expect(snapshot.preferred_locale).toBe("vi-VN");
  await expect(getLocaleSnapshotForWorkspace({
    workspaceId: session.platform_workspace_id!,
    authorization: `Bearer ${foreign.access_token}`,
  })).rejects.toThrow();
});
```

- [ ] **Step 2: Run the focused test and confirm it fails.**

Run: `cd services/cosa && npx vitest run tests/auth-profile-locale.test.ts`

Expected: FAIL because the profile DTO has no `preferred_locale`, and the scoped locale-snapshot endpoint/client do not exist.

- [ ] **Step 3: Add the expand-only schema change and validation.**

Migration adds `cosa.profiles.preferred_locale VARCHAR(10) NOT NULL DEFAULT 'vi-VN'` with a check constraint allowing only `vi-VN`/`en-US`. Add `preferredLocale` to Drizzle `profiles`; add the typed constant/type and a parser that raises `APIError.invalidArgument("unsupported preferred_locale")` before update. Include the column in login/register user payloads and `getPlatformUserProfile`; update it only in `updatePlatformUserProfile(userIdStr, params)`.

Add the read-only internal-boundary endpoint `GET /platform/auth/me/locale-snapshot?workspaceId=...`. It is `expose: true, auth: false` only because it must accept a Control Plane delegation minted by Agent Platform; its handler must call the existing `resolveCallerAuthorizedForWorkspace(authorization, workspaceId)` before loading the resolved caller's own profile. It returns only `{ workspace_id, preferred_locale }`, rejects a foreign workspace, and never accepts a target `userId`. This is the same authorization shape as the existing agent-policy snapshot, not a public unauthenticated profile lookup.

Implement `ProfileLocaleClient` in Agent Platform by following `CosaTenantPolicyClient`: send the delegation bearer and workspace ID to this endpoint, decode only the two supported locales into a typed `ProfileLocaleSnapshot`, and raise `ProfileLocaleUnavailable` for transport, authorization, or malformed-data failure. Its unit test uses an `httpx.MockTransport` and asserts the exact delegated `Authorization` header, the `workspaceId` query parameter, rejection of a foreign/403 response, and malformed locale rejection. Do not forward a raw Flutter bearer and do not import or query `services/cosa` tables from Python.

```ts
function parseSupportedLocale(value: string): SupportedLocale {
  if (value === "vi-VN" || value === "en-US") return value;
  throw APIError.invalidArgument("unsupported preferred_locale");
}
```

- [ ] **Step 4: Run focused test, auth regression, typecheck and migration checks.**

Run:

```bash
cd services/cosa && npx vitest run tests/auth-profile-locale.test.ts
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/policies/test_profile_locale_client.py -q
cd services/cosa && npm run typecheck
make encore-handler-boundary-check
```

Expected: PASS; direct profile mutation by an authenticated user cannot target another `user_id`.

- [ ] **Step 5: Commit the server locale contract.**

```bash
git add services/cosa/migrations/32_profile_preferred_locale.up.sql \
  services/cosa/migrations/32_profile_preferred_locale.down.sql \
  services/cosa/storage/schema.ts services/cosa/services/auth.service.ts \
  services/cosa/handlers/auth.handler.ts services/cosa/tests/auth-profile-locale.test.ts \
  apps/cosa/policies/profile_locale_client.py tests/apps/cosa/policies/test_profile_locale_client.py
git commit -m "feat(profile): persist preferred locale"
```

## Task 2: Add the server-authoritative module visibility contract

**Files:**
- Create: `services/cosa/migrations/33_workspace_module_visibility.up.sql`
- Create: `services/cosa/migrations/33_workspace_module_visibility.down.sql`
- Modify: `services/cosa/storage/schema.ts:1-150`
- Modify: `services/cosa/services/workspace-settings.service.ts`
- Modify: `services/cosa/handlers/workspace-settings.handler.ts`
- Modify: `services/cosa/tests/workspace-settings.test.ts`

**Interfaces:**

```ts
export type OptionalModuleKey = "finance" | "legal" | "crm";

export interface WorkspaceModuleVisibility {
  moduleKey: OptionalModuleKey;
  workspaceEnabled: boolean;
  userVisible: boolean;
  effectiveVisible: boolean;
}

export async function listMyWorkspaceModuleVisibilityService(
  workspaceId: string,
  authorization?: string,
): Promise<MvpSuccess<readonly WorkspaceModuleVisibility[]>>;

export async function putWorkspaceModuleEnabledService(
  workspaceId: string, moduleKey: OptionalModuleKey, enabled: boolean, authorization?: string,
): Promise<MvpSuccess<WorkspaceModuleVisibility>>;

export async function putMyModuleVisibilityService(
  workspaceId: string, moduleKey: OptionalModuleKey, visible: boolean, authorization?: string,
): Promise<MvpSuccess<WorkspaceModuleVisibility>>;
```

- [ ] **Step 1: Write failing operator, membership and effective-state tests.**

```ts
async function createWorkspaceForTest(name: string) {
  return registerPlatformUser({
    email: `${name}-${Date.now()}-${Math.random()}@test.invalid`,
    password: "SecurePassword123",
    workspace_name: name,
  });
}

it("only an operator enables a workspace module and writes an audit event", async () => {
  const founder = await createWorkspaceForTest("visibility-founder");
  const outsider = await createWorkspaceForTest("visibility-outsider");
  const workspaceId = founder.platform_workspace_id!;
  await expect(putWorkspaceModuleEnabled({ workspaceId, moduleKey: "finance", enabled: false, authorization: `Bearer ${outsider.access_token}` })).rejects.toThrow();
  expect((await putWorkspaceModuleEnabled({ workspaceId, moduleKey: "finance", enabled: false, authorization: `Bearer ${founder.access_token}` })).data.effectiveVisible).toBe(false);
  expect((await listWorkspaceAuditEvents({ workspaceId, authorization: `Bearer ${founder.access_token}` })).data).toContainEqual(expect.objectContaining({ eventType: "module_visibility.workspace_changed", targetId: "finance" }));
});

it("a member can hide only their own enabled CRM entry", async () => {
  const founder = await createWorkspaceForTest("visibility-member-founder");
  const member = await registerPlatformUser({ email: `member-${Date.now()}@test.invalid`, password: "SecurePassword123" });
  const workspaceId = founder.platform_workspace_id!;
  await db.insert(schema.workspaceMemberships).values({ id: BigInt(generateSnowflakeStr()), workspaceId: BigInt(workspaceId), userId: BigInt(member.user!.id), roleId: "member" });
  await putWorkspaceModuleEnabled({ workspaceId, moduleKey: "crm", enabled: true, authorization: `Bearer ${founder.access_token}` });
  await putMyModuleVisibility({ workspaceId, moduleKey: "crm", visible: false, authorization: `Bearer ${member.access_token}` });
  expect((await listMyWorkspaceModuleVisibility({ workspaceId, authorization: `Bearer ${member.access_token}` })).data).toContainEqual(expect.objectContaining({ moduleKey: "crm", effectiveVisible: false }));
  expect((await listMyWorkspaceModuleVisibility({ workspaceId, authorization: `Bearer ${founder.access_token}` })).data).toContainEqual(expect.objectContaining({ moduleKey: "crm", effectiveVisible: true }));
});

it("rejects a foreign workspace and invalid module key", async () => {
  const owner = await createWorkspaceForTest("visibility-owner");
  const outsider = await createWorkspaceForTest("visibility-foreign");
  await expect(putMyModuleVisibility({ workspaceId: owner.platform_workspace_id!, moduleKey: "finance", visible: false, authorization: `Bearer ${outsider.access_token}` })).rejects.toThrow();
  await expect(putMyModuleVisibility({ workspaceId: outsider.platform_workspace_id!, moduleKey: "vault" as never, visible: false, authorization: `Bearer ${outsider.access_token}` })).rejects.toThrow();
});
```

- [ ] **Step 2: Run the focused test and confirm it fails.**

Run: `cd services/cosa && npx vitest run tests/workspace-settings.test.ts`

Expected: FAIL because module visibility tables, DTOs and routes do not exist.

- [ ] **Step 3: Add tables, resolver and routes.**

Migration creates `cosa.workspace_module_settings(workspace_id, module_key, enabled, updated_by, timestamps)` and `cosa.user_module_preferences(workspace_id, user_id, module_key, visible, timestamps)`, both with composite primary keys and foreign keys to the same workspace/user records already used by `workspaceMemberships`. Backfill each optional module enabled. Absence of a user preference resolves to `true`.

Add three endpoints:

```text
GET /platform/workspaces/:workspaceId/module-visibility
PUT /platform/workspaces/:workspaceId/modules/:moduleKey
PUT /platform/workspaces/:workspaceId/my-module-preferences/:moduleKey
```

The first calls `verifyWorkspaceMembership`; the second calls `requireWorkspaceOperator`; the third derives actor ID from authorization and never accepts a body `userId`. Workspace mutation inserts `workspace_settings_audit_events` with `eventType="module_visibility.workspace_changed"`; personal visibility is not an authority mutation and has no workspace audit event.

- [ ] **Step 4: Run service tests and guardrails.**

Run:

```bash
cd services/cosa && npx vitest run tests/workspace-settings.test.ts
cd services/cosa && npm run typecheck
make encore-handler-boundary-check
make company-boundary-check
```

Expected: PASS; all three effective states (`true/true`, `true/false`, `false/true`) resolve correctly and no handler imports Drizzle.

- [ ] **Step 5: Commit the visibility API.**

```bash
git add services/cosa/migrations/33_workspace_module_visibility.up.sql \
  services/cosa/migrations/33_workspace_module_visibility.down.sql \
  services/cosa/storage/schema.ts services/cosa/services/workspace-settings.service.ts \
  services/cosa/handlers/workspace-settings.handler.ts services/cosa/tests/workspace-settings.test.ts
git commit -m "feat(workspace): add optional module visibility"
```

## Task 3: Build Flutter locale state, profile synchronization and selector

**Files:**
- Create: `frontend/lib/core/localization/supported_locale.dart`
- Create: `frontend/lib/core/localization/locale_cache.dart`
- Create: `frontend/lib/core/localization/locale_controller.dart`
- Create: `frontend/lib/core/localization/app_translations.dart`
- Modify: `frontend/lib/main.dart:88-104`
- Modify: `frontend/lib/core/session/session_binding.dart:17-27`
- Modify: `frontend/lib/modules/auth/services/auth_service.dart:467-515`
- Modify: `frontend/lib/modules/profile/controllers/profile_controller.dart`
- Modify: `frontend/lib/modules/profile/views/profile_view.dart`
- Create: `frontend/test/core/localization/locale_controller_test.dart`
- Create: `frontend/test/modules/profile/profile_locale_selector_test.dart`

**Interfaces:**

```dart
enum SupportedLocale { viVN, enUS }

extension SupportedLocaleWire on SupportedLocale {
  String get tag;
  Locale get flutterLocale;
  String get transcriptionLanguage;
  static SupportedLocale parse(String value);
}

abstract interface class LocaleCache {
  Future<SupportedLocale?> read();
  Future<void> write(SupportedLocale locale);
}

class LocaleController extends GetxController {
  final Rx<SupportedLocale> current = SupportedLocale.viVN.obs;
  Future<void> hydrateFromCache();
  Future<void> applyServerLocale(SupportedLocale locale);
  Future<bool> updatePreference(SupportedLocale locale);
}
```

- [ ] **Step 1: Write failing unit/widget tests.**

```dart
test('cached en-US renders before network identity is available', () async {
  final controller = LocaleController(cache: FakeLocaleCache('en-US'), profileApi: FakeProfileApi());
  await controller.hydrateFromCache();
  expect(controller.current.value, SupportedLocale.enUS);
});

test('failed profile PATCH keeps the prior GetX locale and cache', () async {
  final cache = FakeLocaleCache('vi-VN');
  final controller = LocaleController(cache: cache, profileApi: FailingProfileApi());
  final changed = await controller.updatePreference(SupportedLocale.enUS);
  expect(changed, isFalse);
  expect(controller.current.value, SupportedLocale.viVN);
  expect(await cache.read(), SupportedLocale.viVN);
});

testWidgets('profile language selector calls PATCH then updates labels', (tester) async {
  await tester.pumpWidget(buildProfileWithLocaleController());
  await tester.tap(find.text('English'));
  await tester.pumpAndSettle();
  expect(find.text('Language'), findsOneWidget);
});
```

- [ ] **Step 2: Run the focused tests and confirm they fail.**

Run:

```bash
cd frontend && flutter test test/core/localization/locale_controller_test.dart
cd frontend && flutter test test/modules/profile/profile_locale_selector_test.dart
```

Expected: FAIL because no typed locale/cache/controller or selector exists.

- [ ] **Step 3: Implement deterministic hydration and profile update.**

Use `SharedPreferences` through `LocaleCache` key `preferred_locale`; never use secure storage because this value is not a bearer secret. Register one permanent `LocaleController` in `SessionBinding`, hydrate cache before `runApp`, and use its `current` for `GetMaterialApp.locale`/`fallbackLocale`.

Extend `AuthResult.user` handling and `AuthService.updateProfile` to parse/send `preferred_locale`. At successful `SessionController.activateWorkspace`, call `LocaleController.applyServerLocale` before committing user-facing shell state. `applyServerLocale` calls `Get.updateLocale(locale.flutterLocale)` and writes cache. `updatePreference` PATCHes first; only then calls `applyServerLocale`.

Add a two-option profile selector with value labels `Tiếng Việt` and `English`, loading/saving disabled state, and localized failure/success feedback.

- [ ] **Step 4: Run focused Flutter tests and analyze.**

Run:

```bash
cd frontend && flutter test test/core/localization/locale_controller_test.dart test/modules/profile/profile_locale_selector_test.dart test/core/session/session_controller_test.dart
cd frontend && flutter analyze
```

Expected: PASS; switching workspace cannot overwrite a server locale with stale cache and PATCH failure is non-mutating.

- [ ] **Step 5: Commit locale state and selector.**

```bash
git add frontend/lib/core/localization frontend/lib/main.dart frontend/lib/core/session/session_binding.dart \
  frontend/lib/core/session/session_controller.dart frontend/lib/modules/auth/services/auth_service.dart \
  frontend/lib/modules/profile frontend/test/core/localization frontend/test/modules/profile
git commit -m "feat(frontend): sync profile locale with GetX"
```

## Task 4: Catalog and migrate Flutter copy to GetX translations

**Files:**
- Modify: `frontend/lib/core/localization/app_translations.dart`
- Modify: `frontend/lib/main.dart`
- Modify: `frontend/lib/core/shell/app_shell.dart`
- Modify: `frontend/lib/modules/dashboard/models/dashboard_nav_config.dart`
- Modify: `frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart`
- Modify: `frontend/lib/modules/chat/views/**`
- Modify: `frontend/lib/modules/profile/views/profile_view.dart`
- Modify: `frontend/lib/modules/finance/views/**`
- Modify: `frontend/lib/modules/legal/**`
- Modify: `frontend/lib/modules/sales/**`
- Modify: `frontend/lib/modules/marketing/**`
- Modify: `frontend/lib/modules/settings/**`
- Create: `frontend/test/core/localization/app_translations_test.dart`
- Create: `frontend/test/core/localization/localized_navigation_test.dart`

**Interfaces:**

```dart
abstract final class L10nKey {
  static const profileLanguageTitle = 'profile.language.title';
  static const profileLanguageVi = 'profile.language.vi';
  static const profileLanguageEn = 'profile.language.en';
  static const chatNewConversation = 'chat.newConversation';
  static const moduleFinance = 'module.finance';
  static const moduleLegal = 'module.legal';
  static const moduleCrm = 'module.crm';
}
```

- [ ] **Step 1: Write failing catalogue and shell/navigation tests.**

```dart
test('every required key has non-empty VI and EN values', () {
  for (final key in L10nKey.required) {
    expect(AppTranslations.vi[key], isNotEmpty);
    expect(AppTranslations.en[key], isNotEmpty);
  }
});

testWidgets('sidebar re-renders finance label after changing to en-US', (tester) async {
  await tester.pumpWidget(buildLocalizedSidebar(SupportedLocale.viVN));
  expect(find.text('Tài chính'), findsOneWidget);
  await Get.find<LocaleController>().applyServerLocale(SupportedLocale.enUS);
  await tester.pumpAndSettle();
  expect(find.text('Finance'), findsOneWidget);
});
```

- [ ] **Step 2: Run tests and confirm failure.**

Run: `cd frontend && flutter test test/core/localization/app_translations_test.dart test/core/localization/localized_navigation_test.dart`

Expected: FAIL because existing copy is hard-coded and keys/catalogue are absent.

- [ ] **Step 3: Add maps and replace user-facing strings by semantic keys.**

`AppTranslations.keys` contains only `vi_VN` and `en_US`. Replace static labels, dialog copy, status text, errors owned by Flutter and empty states with `.tr`/`.trParams`; do not translate route paths, API fields, error codes, enum values, `TT58`, `VND`, or raw backend error detail. Change `DashboardNavItem.label` and `DashboardNavGroup.title` from rendered text to `labelKey`/`titleKey`, resolving them in sidebar build.

Inventory and migrate in this order so shared chrome becomes usable first: core shell/routing → dashboard navigation → profile/auth/settings → chat/hologram chat → Finance/Legal/Sales/Marketing → remaining module views. After every directory, run `rg -n "Text\\(['\\\"]" frontend/lib/<directory>` and classify remaining literals as either translations, tests, log-only, identifiers, or intentional product names. Each user-facing literal must become a key before the directory is accepted.

- [ ] **Step 4: Add locale-aware formatting at UI boundaries.**

Introduce shared `LocalizedFormatters` using `NumberFormat`/`DateFormat` with `LocaleController.current.value.tag`. Replace local `VND` string concatenation only with formatting of the existing currency code/value; it must not convert currency or change transaction data. Add tests for `vi-VN` and `en-US` decimal/date rendering of the same numeric input.

- [ ] **Step 5: Run translation, navigation, affected widget tests and analyzer.**

Run:

```bash
cd frontend && flutter test test/core/localization/app_translations_test.dart test/core/localization/localized_navigation_test.dart test/modules/dashboard/dashboard_sidebar_test.dart test/modules/chat/chat_module_test.dart test/hub_chat_panel_test.dart
cd frontend && flutter analyze
```

Expected: PASS; locale change updates navigation and shared chat/profile copy without a restart.

- [ ] **Step 6: Commit the catalogued UI.**

```bash
git add frontend/lib/core/localization frontend/lib/core/shell frontend/lib/modules \
  frontend/test/core/localization frontend/test/modules/dashboard frontend/test/modules/chat frontend/test/hub_chat_panel_test.dart
git commit -m "feat(frontend): localize VI EN interface"
```

## Task 5: Propagate resolved locale through chat, worker and voice paths

**Files:**
- Modify: `apps/cosa/api/conversation_routes.py:98-294`
- Modify: `apps/cosa/api/schemas.py:91-125`
- Modify: `apps/cosa/composition/agent_plane.py:47-255`
- Create: `apps/cosa/policies/profile_locale_client.py`
- Modify: `apps/cosa/worker/run_core.py:74-158`
- Modify: `apps/cosa/worker/autopilot_run.py:112-136`
- Modify: `apps/cosa/worker/copilot_run.py:288-318`
- Modify: `frontend/lib/modules/chat/services/agent_chat_service.dart:112-165`
- Modify: `frontend/lib/modules/chat/controllers/chat_controller.dart:143-230`
- Modify: `frontend/lib/core/services/voice_service.dart:11-120`
- Modify: `packages/agent/contracts/run.py:35-48`
- Test: `tests/apps/cosa/wga/test_run_core.py`
- Test: `tests/apps/cosa/test_autopilot_run.py`
- Test: `tests/apps/cosa/test_copilot_run.py`
- Test: `tests/agent/prompts/test_bundle.py`
- Test: `frontend/test/core/services/voice_service_logging_test.dart`
- Create: `tests/apps/cosa/test_conversation_locale.py`
- Create: `tests/apps/cosa/policies/test_profile_locale_client.py`

**Interfaces:**

```python
SUPPORTED_LOCALES = frozenset({"vi-VN", "en-US"})

@dataclass(frozen=True)
class ResolvedLocale:
    value: str
    source: Literal["profile", "turn_override", "system_fallback"]

def resolve_response_locale(
    *, profile_locale: str | None, response_locale_override: str | None, has_principal: bool
) -> ResolvedLocale: ...

async def prepare_request(..., locale: ResolvedLocale, ...) -> RunCorePrep: ...

@dataclass(frozen=True)
class ProfileLocaleSnapshot:
    workspace_id: str
    preferred_locale: str

class ProfileLocaleUnavailable(RuntimeError): ...
```

- [ ] **Step 1: Write failing agent locale tests.**

```python
async def test_message_uses_profile_en_us_when_content_is_vietnamese(client, en_us_identity):
    response = await client.post("/agent/conversations/c1/messages", json={
        "content": "Hãy tóm tắt", "role": "user", "data_access": valid_access(),
    }, headers=en_us_identity.headers)
    assert queued_run(response).metadata["locale_source"] == "profile"
    assert queued_run(response).locale == "en-US"

async def test_structured_turn_override_does_not_change_profile(client, en_us_identity):
    response = await client.post("/agent/conversations/c1/messages", json={
        "content": "xin chào", "response_locale_override": "vi-VN", "role": "user", "data_access": valid_access(),
    }, headers=en_us_identity.headers)
    assert queued_run(response).locale == "vi-VN"
    assert (await profile_for(en_us_identity)).preferred_locale == "en-US"

async def test_unknown_override_is_rejected_before_message_persistence(client, identity):
    response = await client.post("/agent/conversations/c1/messages", json={
        "content": "hello", "response_locale_override": "fr-FR", "role": "user", "data_access": valid_access(),
    }, headers=identity.headers)
    assert response.status_code == 422
    assert await message_count("c1") == 0

async def test_profile_locale_snapshot_failure_is_side_effect_free(client, identity, locale_client_unavailable):
    response = await client.post("/agent/conversations/c1/messages", json={
        "content": "hello", "role": "user", "data_access": valid_access(),
    }, headers=identity.headers)
    assert response.status_code == 503
    assert await message_count("c1") == 0
```

Define `valid_access`, `profile_for`, `queued_run`, and `locale_client_unavailable` as test-local fixtures/stubs. The run stub must capture the enqueue payload, while the unavailable client raises `ProfileLocaleUnavailable`; tests must not use a browser-provided locale as a fallback.

- [ ] **Step 2: Run focused Python tests and confirm failure.**

Run:

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_conversation_locale.py tests/apps/cosa/wga/test_run_core.py tests/agent/prompts/test_bundle.py -q
```

Expected: FAIL because conversation schema does not accept override and `prepare_request` does not receive locale.

- [ ] **Step 3: Resolve locale at authenticated boundary and persist provenance.**

Add optional `response_locale_override` to `MessageCreate` in `apps/cosa/api/schemas.py`, validate it against the two values before saving the message, and obtain profile locale through `ProfileLocaleClient` using `identity.mint_control_plane_delegation()` and the authenticated workspace ID. Do not accept a profile locale sent by Flutter as authority. Persist `locale`/`locale_source` in structured run metadata. Pass `ResolvedLocale.value` to `prepare_request` and then `RunRequest.locale`.

Extend `CosaAgentPlane.__init__`, `build_cosa_agent_plane`, and `close_cosa_agent_plane` in `apps/cosa/composition/agent_plane.py` with one injectable `profile_locale_client`, defaulting to `ProfileLocaleClient`. Expose it as `plane.profile_locale_client` so the route can be supplied a deterministic fake in tests and the persistent HTTP client is closed in the API lifespan.

For messages without explicit override, use the snapshot profile locale. If locale snapshot retrieval fails for an authenticated person, return a retryable 503 before message persistence or enqueue; never silently fall back to cache/browser/prompt language. For an explicitly identified system/headless task with no person, use `vi-VN` with `system_fallback`. Never infer from prompt text.

- [ ] **Step 4: Carry locale in background workloads and remove Vietnamese fixed prompt.**

All event payload constructors must set a validated locale and source. `autopilot_run` reads that structured payload and sets `RunRequest.locale`; `copilot_run` composes neutral canonical instruction/context and relies on `PromptBundle` locale policy rather than Vietnamese sentence literals. Existing `PromptBundle` remains canonical English and must retain current governance sections.

- [ ] **Step 5: Bind voice transcription to active locale.**

Remove default method parameter `language = 'vi'` from public voice paths. Resolve `LocaleController.current.value.transcriptionLanguage` immediately before multipart upload. Tests prove `vi-VN -> vi`, `en-US -> en`, and preserve existing raw-audio cleanup/redacted-log behavior.

- [ ] **Step 6: Run all focused tests.**

Run:

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_conversation_locale.py tests/apps/cosa/wga/test_run_core.py tests/apps/cosa/test_autopilot_run.py tests/apps/cosa/test_copilot_run.py tests/agent/prompts/test_bundle.py -q
cd frontend && flutter test test/core/services/voice_service_logging_test.dart test/modules/chat/chat_module_test.dart
```

Expected: PASS; a Vietnamese input from an `en-US` profile produces `RunRequest.locale == "en-US"`, invalid override is side-effect free, and no agent path silently reverts to `vi-VN` except the explicit system fallback.

- [ ] **Step 7: Commit locale propagation.**

```bash
git add apps/cosa/api/conversation_routes.py apps/cosa/api/schemas.py apps/cosa/composition/agent_plane.py \
  apps/cosa/policies/profile_locale_client.py apps/cosa/worker/run_core.py \
  apps/cosa/worker/autopilot_run.py apps/cosa/worker/copilot_run.py \
  packages/agent/contracts/run.py frontend/lib/modules/chat frontend/lib/core/services/voice_service.dart \
  tests/apps/cosa/test_conversation_locale.py tests/apps/cosa/policies/test_profile_locale_client.py tests/apps/cosa/wga/test_run_core.py \
  tests/apps/cosa/test_autopilot_run.py tests/apps/cosa/test_copilot_run.py tests/agent/prompts/test_bundle.py \
  frontend/test/core/services/voice_service_logging_test.dart frontend/test/modules/chat/chat_module_test.dart
git commit -m "feat(agent): resolve response locale from profile"
```

## Task 6: Consume module visibility in Flutter navigation and settings

**Files:**
- Create: `frontend/lib/core/services/module_visibility_service.dart`
- Create: `frontend/lib/core/services/module_visibility_controller.dart`
- Modify: `frontend/lib/core/session/session_controller.dart`
- Modify: `frontend/lib/core/routing/module_routes.dart`
- Modify: `frontend/lib/modules/dashboard/models/dashboard_nav_config.dart`
- Modify: `frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart`
- Modify: `frontend/lib/modules/settings/views/settings_view.dart`
- Create: `frontend/test/core/services/module_visibility_controller_test.dart`
- Modify: `frontend/test/modules/dashboard/dashboard_sidebar_test.dart`
- Create: `frontend/test/core/routing/module_visibility_redirect_test.dart`

**Interfaces:**

```dart
enum OptionalModule { finance, legal, crm }

class ModuleVisibility {
  const ModuleVisibility({
    required this.module,
    required this.workspaceEnabled,
    required this.userVisible,
  });
  bool get effectiveVisible => workspaceEnabled && userVisible;
}

class ModuleVisibilityController extends GetxController {
  final RxMap<OptionalModule, ModuleVisibility> entries = <OptionalModule, ModuleVisibility>{}.obs;
  Future<void> reloadForWorkspace(String workspaceId);
  bool isVisible(WorkspaceModule module);
  Future<void> setMyVisible(OptionalModule module, bool visible);
  Future<void> setWorkspaceEnabled(OptionalModule module, bool enabled);
}
```

- [ ] **Step 1: Write failing controller, sidebar and route tests.**

```dart
test('CRM maps to WorkspaceModule.sales and an absent preference defaults visible', () async {
  final controller = ModuleVisibilityController(api: FakeVisibilityApi(crmEnabled: true));
  await controller.reloadForWorkspace('w1');
  expect(controller.isVisible(WorkspaceModule.sales), isTrue);
});

testWidgets('hides Finance and Legal navigation but leaves core modules visible', (tester) async {
  await tester.pumpWidget(buildSidebar(visibility: hiddenFinanceLegal()));
  expect(find.text('Finance'), findsNothing);
  expect(find.text('Legal'), findsNothing);
  expect(find.text('Tasks'), findsOneWidget);
});

testWidgets('redirects a direct finance route to hub when Finance is hidden', (tester) async {
  await tester.pumpWidget(buildAppAt(WorkspaceModule.finance.path, visibility: hiddenFinance()));
  expect(Get.currentRoute, AppRoutes.hub);
});
```

- [ ] **Step 2: Run focused Flutter tests and confirm failure.**

Run:

```bash
cd frontend && flutter test test/core/services/module_visibility_controller_test.dart test/modules/dashboard/dashboard_sidebar_test.dart test/core/routing/module_visibility_redirect_test.dart
```

Expected: FAIL because the app has only static `FeatureFlagsController` filtering and no server visibility client.

- [ ] **Step 3: Implement server DTO client and workspace lifecycle.**

`ModuleVisibilityService` calls the GET/PUT endpoints from Task 2 through `ApiClient`; its decode rejects unknown module key or malformed booleans. `SessionController._commit` calls `reloadForWorkspace` only after identity/session snapshot commit; logout clears entries. Guard `WorkspaceModule.finance`, `WorkspaceModule.legal`, and `WorkspaceModule.sales` using `isVisible`; all other modules return true. A hidden deep link redirects to hub with a translated informational snackbar, never returns an authorization error fabricated by the client.

- [ ] **Step 4: Add settings controls with role-aware behavior.**

Settings shows each optional module’s personal toggle to all members. If session role is founder/co-founder/admin, it additionally shows workspace enable toggle; member UI never renders this mutation. Disable controls during network update, retain previous `RxMap` state on an error, and show translated error copy. Do not remove routes, bindings, API clients or stored module data when a module is hidden.

- [ ] **Step 5: Run focused tests and analyzer.**

Run:

```bash
cd frontend && flutter test test/core/services/module_visibility_controller_test.dart test/modules/dashboard/dashboard_sidebar_test.dart test/core/routing/module_visibility_redirect_test.dart test/core/session/session_controller_test.dart
cd frontend && flutter analyze
```

Expected: PASS; changing user visibility only affects the caller’s navigation, and a server-disabled module stays hidden even when personal preference is true.

- [ ] **Step 6: Commit the visibility client.**

```bash
git add frontend/lib/core/services/module_visibility_service.dart frontend/lib/core/services/module_visibility_controller.dart \
  frontend/lib/core/session/session_controller.dart frontend/lib/core/routing/module_routes.dart \
  frontend/lib/modules/dashboard frontend/lib/modules/settings \
  frontend/test/core/services/module_visibility_controller_test.dart frontend/test/modules/dashboard/dashboard_sidebar_test.dart \
  frontend/test/core/routing/module_visibility_redirect_test.dart frontend/test/core/session/session_controller_test.dart
git commit -m "feat(frontend): respect optional module visibility"
```

## Task 7: Freeze contracts and prove cross-plane regressions

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Regenerate: `frontend/lib/core/network/mvp_endpoints.g.dart`
- Modify: `docs/architecture/generated/route-inventory.md` if its documented generator produces changes
- Create: `tests/integration/test_vi_en_locale_cross_plane.py`
- Modify: `services/cosa/tests/workspace-settings.test.ts`
- Modify: `frontend/test/auth_flow_test.dart`
- Modify: `frontend/test/core/session/session_controller_test.dart`

**Interfaces:**

```text
POST /agent/conversations/:id/messages accepts optional response_locale_override.
GET /platform/auth/me returns required preferred_locale.
GET /platform/auth/me/locale-snapshot returns only the delegated caller's preferred_locale for its authorized workspace.
GET /platform/workspaces/:workspaceId/module-visibility returns three visibility rows.
PUT /platform/workspaces/:workspaceId/modules/:moduleKey is operator-only.
PUT /platform/workspaces/:workspaceId/my-module-preferences/:moduleKey is self-only.
```

- [ ] **Step 1: Write a failing end-to-end contract scenario.**

```python
async def test_en_profile_keeps_vietnamese_business_configuration_unchanged(e2e_client):
    user = await e2e_client.register_user(preferred_locale="vi-VN")
    await e2e_client.patch_me(user, {"preferred_locale": "en-US"})
    run = await e2e_client.send_message(user, "Hãy tóm tắt báo cáo")
    assert run.locale == "en-US"
    assert await e2e_client.accounting_mode(user.workspace_id) == "TT58_MODE_1"
    assert await e2e_client.default_currency(user.workspace_id) == "VND"

async def test_profile_locale_and_workspace_visibility_are_tenant_isolated(e2e_client):
    alice, bob = await e2e_client.create_separate_workspaces()
    await e2e_client.patch_me(alice, {"preferred_locale": "en-US"})
    await e2e_client.set_my_module_visibility(alice, "finance", False)
    assert (await e2e_client.get_me(bob)).preferred_locale == "vi-VN"
    assert (await e2e_client.list_visibility(bob, bob.workspace_id))["finance"].effective_visible is True
```

- [ ] **Step 2: Run the test and confirm it fails before contracts are wired.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/integration/test_vi_en_locale_cross_plane.py -q`

Expected: FAIL before every API/schema boundary from Tasks 1–6 is available.

- [ ] **Step 3: Update generated contracts through their owner workflow.**

Add all new public endpoint definitions to `shared/contracts/mvp-surface.json`, run the repository’s contract generator instead of hand-editing generated Dart, and verify generated endpoint ownership/plane/auth metadata. Keep legacy route semantics unchanged. Add `preferred_locale` to platform auth response fixtures used by Flutter and TypeScript tests.

- [ ] **Step 4: Run focused and required repository gates.**

Run:

```bash
make frontend-api-contract-check
make route-auth-allowlist-check
make contract-freeze-check
make services-test-cosa
make agent-test
make frontend-test
make frontend-analyze
```

Expected: PASS; all public route additions are frozen in contract inventory, localized UI tests pass, and no boundary test treats UI visibility as authorization.

- [ ] **Step 5: Run the cross-plane integration test on disposable Postgres.**

Run: `make e2e-cross-plane-smoke`

Expected: PASS with an actual Control Plane → Flutter/API contract → Agent run path; if environment cannot supply disposable Postgres/Encore, record the exact blocker and do not claim the cross-plane scenario passed.

- [ ] **Step 6: Commit contracts and verification coverage.**

```bash
git add shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart \
  docs/architecture/generated tests/integration/test_vi_en_locale_cross_plane.py \
  services/cosa/tests/workspace-settings.test.ts frontend/test/auth_flow_test.dart frontend/test/core/session/session_controller_test.dart
git commit -m "test(i18n): freeze VI EN locale contracts"
```

## Delivery sequence

Execute Tasks 1 and 2 serially because they share migration sequence and Control Plane schema. Tasks 3 and 5 can start after Task 1; Task 6 starts after Task 2 and Task 3; Task 4 can proceed after Task 3; Task 7 runs only when Tasks 1–6 are green. Do not release the UI selector before Task 1 server validation, and do not release module settings before Task 2 tenancy tests.

## Self-review

- Profile locale: Tasks 1 and 3 cover storage, auth response, cache, failed write and device/session hydration.
- GetX VI–EN UI and formatting: Task 4 covers catalog, shell/navigation, feature modules and formatter behavior.
- Agent language policy and all run paths: Task 5 covers authenticated conversation, one-turn override, `prepare_request`, autopilot, copilot and voice.
- Visibility and separation from authorization: Tasks 2 and 6 cover server policy, member/operator boundaries, routes, sidebar and settings UI.
- Future jurisdiction safety: global constraints plus Task 7 prove language does not change TT58/VND; no country/accounting schema enters this plan.
- Contract, tenancy and real-stack proof: Task 7 runs generated contracts, service/agent/frontend gates and disposable-Postgres smoke.
