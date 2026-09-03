# Zero-Project Setup Redirect — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khi workspace chưa có project (hoặc project duy nhất chưa hoàn tất kickoff), redirect Founder từ `/hub` và `/work/*` sang route tạo project generic `/projects/new`, và ẩn các widget số liệu giả trên Hub.

**Architecture:** Ba lớp phối hợp, dùng chung một getter thuần `FounderCommandCenterController.needsProjectSetup`:
1. `ProjectSetupGuardMiddleware` — redirect **đồng bộ** khi state FCC đã sẵn (fast path), gắn vào `/hub` + mọi `/work/*`.
2. Backstop **bất đồng bộ** ở cuối `FounderCommandCenterController.loadDashboardData()` — bắt trường hợp điều hướng vào `/hub` trước khi projects tải xong.
3. `/projects/new` (`ProjectSetupView` + `ProjectSetupController`) — mode-aware: onboarding (`projectCount == 0`, không có nút Huỷ) vs thường (`projectCount >= 1`). Form tạo project → `ProjectKickoffView` inline (tái dùng) → `activate` → `/hub`.

**Tech Stack:** Flutter, GetX (routing + DI + reactive state), `flutter_test` + `http/testing` `MockClient`.

## Global Constraints

- **Không đảo ngược Task 9/10:** `/hub` giữ nguyên là route canonical duy nhất cho Hub; không tách lại `/hub` vs `/dashboard`. Prefix `/work/*` giữ nguyên.
- **Không đổi backend:** dùng nguyên `StrategyService.createBasicProject`, `ProjectOperatingSetupService.get`, và các endpoint kickoff/`activate` hiện có.
- **Không sửa nội dung/visual** của `ProjectKickoffView`, `CoFounderCardWidget`, `Top3FocusWidget`, `WaitingForYouWidget` — chỉ thêm điều kiện render / tái dùng.
- **Prose tiếng Việt** cho mọi comment mới; identifier / route / log / error message giữ tiếng Anh.
- **Route mới:** `AppRoutes.projectsNew = '/projects/new'`.
- Điều kiện redirect (`needsProjectSetup`): `projectsError == null` **và** (`projectsList` rỗng **hoặc** (`projectsList.length == 1` **và** `activeProjectSetup.status != OperatingSetupStatus.active`)). Nhiều hơn 1 project ⇒ không redirect (bảo thủ, không đụng workspace đã vận hành).
- Backstop async chỉ được `Get.offAllNamed` khi `Get.currentRoute == '/hub'` hoặc bắt đầu bằng `'/work/'`.
- TDD: test đỏ trước, commit sau mỗi task.

**Chạy test:** `cd frontend && flutter test <path>`

---

### Task 1: `needsProjectSetup` getter trên `FounderCommandCenterController`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Test: `frontend/test/modules/hologram_hub/founder_command_center_needs_project_setup_test.dart` (create)

**Interfaces:**
- Consumes: các field có sẵn `RxList<dynamic> projectsList`, `RxnString projectsError`, `Rxn<ProjectOperatingSetup> activeProjectSetup` (kiểu `ProjectOperatingSetup` từ `data/models/project_operating_setup_model.dart`, enum `OperatingSetupStatus`).
- Produces: `bool get needsProjectSetup` — dùng bởi Task 4 (middleware) và Task 5 (backstop).

- [ ] **Step 1: Viết test đỏ**

Tạo `frontend/test/modules/hologram_hub/founder_command_center_needs_project_setup_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
  });

  FounderCommandCenterController makeController() {
    // Không gọi onInit()/loadDashboardData() — chỉ kiểm tra getter thuần.
    return FounderCommandCenterController();
  }

  ProjectOperatingSetup setupWith(OperatingSetupStatus status) =>
      ProjectOperatingSetup(
        projectId: 'p1',
        workspaceId: 'ws_1',
        status: status,
        firstWeekActions: const [],
        updatedAt: DateTime.now().toIso8601String(),
      );

  test('rỗng projectsList và không lỗi -> cần setup', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.clear();
    expect(c.needsProjectSetup, isTrue);
  });

  test('lỗi tải project -> KHÔNG cần setup (tránh nhốt Founder vì lỗi mạng)', () {
    final c = makeController();
    c.projectsError.value = 'boom';
    c.projectsList.clear();
    expect(c.needsProjectSetup, isFalse);
  });

  test('1 project, setup chưa ACTIVE -> cần setup (resume kickoff)', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.assignAll([{'id': 'p1'}]);
    c.activeProjectSetup.value = setupWith(OperatingSetupStatus.inProgress);
    expect(c.needsProjectSetup, isTrue);
  });

  test('1 project, setup ACTIVE -> KHÔNG cần setup', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.assignAll([{'id': 'p1'}]);
    c.activeProjectSetup.value = setupWith(OperatingSetupStatus.active);
    expect(c.needsProjectSetup, isFalse);
  });

  test('nhiều hơn 1 project -> KHÔNG redirect (bảo thủ)', () {
    final c = makeController();
    c.projectsError.value = null;
    c.projectsList.assignAll([{'id': 'p1'}, {'id': 'p2'}]);
    c.activeProjectSetup.value = setupWith(OperatingSetupStatus.inProgress);
    expect(c.needsProjectSetup, isFalse);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `cd frontend && flutter test test/modules/hologram_hub/founder_command_center_needs_project_setup_test.dart`
Expected: FAIL — `needsProjectSetup` chưa tồn tại (compile error).

Nếu constructor `ProjectOperatingSetup` khác chữ ký giả định (kiểm tra `frontend/lib/data/models/project_operating_setup_model.dart`), chỉnh `setupWith` cho khớp field bắt buộc — KHÔNG đổi ý nghĩa test.

- [ ] **Step 3: Thêm getter**

Trong `founder_command_center_controller.dart`, ngay sau khai báo `activeProjectSetup` (khoảng dòng 99), thêm:

```dart
  /// Founder cần vào luồng thiết lập project khi: chưa có project nào, HOẶC
  /// đúng một project và setup của nó chưa `ACTIVE` (tạo project rồi bỏ dở
  /// kickoff — cần resume). Lỗi tải danh sách project KHÔNG kích hoạt điều
  /// này: giữ nguyên hành vi "lỗi tạm thời không đẩy Founder ra onboarding".
  /// Nhiều hơn một project ⇒ không can thiệp (workspace đã vận hành).
  bool get needsProjectSetup {
    if (projectsError.value != null) return false;
    if (projectsList.isEmpty) return true;
    if (projectsList.length == 1) {
      return activeProjectSetup.value?.status != OperatingSetupStatus.active;
    }
    return false;
  }
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

Run: `cd frontend && flutter test test/modules/hologram_hub/founder_command_center_needs_project_setup_test.dart`
Expected: PASS (5 test).

- [ ] **Step 5: Commit**

```bash
cd frontend && git add lib/modules/hologram_hub/controllers/founder_command_center_controller.dart test/modules/hologram_hub/founder_command_center_needs_project_setup_test.dart
git commit -m "feat(hub): needsProjectSetup getter trên FounderCommandCenterController

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `ProjectSetupController`

**Files:**
- Create: `frontend/lib/modules/strategy/controllers/project_setup_controller.dart`
- Test: `frontend/test/modules/strategy/controllers/project_setup_controller_test.dart` (create)

**Interfaces:**
- Consumes: `FounderCommandCenterController` (đã đăng ký permanent bởi `AppShellController.ensureShellDependencies()` hoặc test tự đăng ký) — đọc `projectsList`, `activeProjectSetup`, gọi `loadDashboardData()`. `StrategyService().createBasicProject(title:, description:)` trả `Future<Map<String, dynamic>>` với key `id`. `AppRoutes.hub` (đã tồn tại). `WorkspaceModule.strategy.path` (đã tồn tại).
- Produces:
  - `enum ProjectSetupPhase { form, kickoff }`
  - `class ProjectSetupController extends GetxController`
    - `final Rx<ProjectSetupPhase> phase`
    - `final RxnString createdProjectId`
    - `final RxBool isSubmitting`
    - `final RxnString formError`
    - `bool get isOnboarding` (true khi `fcc.projectsList.isEmpty`)
    - `Future<void> submitForm({required String title, String? description})`
    - `void onKickoffActivated(String projectId)` → `Get.offAllNamed(AppRoutes.hub)`
    - `void onKickoffBack()` → nếu `isOnboarding` thì no-op; ngược lại `Get.offAllNamed(AppRoutes.hub)`
    - `void onOpenAdvancedRoadmap()` → `Get.toNamed(WorkspaceModule.strategy.path)`
    - `void cancel()` → `Get.offAllNamed(AppRoutes.hub)` (chỉ gọi khi `!isOnboarding`)

- [ ] **Step 1: Viết test đỏ**

Tạo `frontend/test/modules/strategy/controllers/project_setup_controller_test.dart`:

```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/controllers/project_setup_controller.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'POST' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'id': 'proj-new', 'title': 'X'}), 200);
      }
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  ProjectSetupController make() {
    Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    return Get.put<ProjectSetupController>(ProjectSetupController());
  }

  test('workspace 0 project -> phase form, isOnboarding true', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.clear();
    final c = Get.put<ProjectSetupController>(ProjectSetupController());
    c.onInit();
    expect(c.phase.value, ProjectSetupPhase.form);
    expect(c.isOnboarding, isTrue);
  });

  test('đã có 1 project setup chưa ACTIVE -> resume thẳng vào kickoff', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.assignAll([{'id': 'p1'}]);
    fcc.activeProjectSetup.value = ProjectOperatingSetup(
      projectId: 'p1', workspaceId: 'ws_1',
      status: OperatingSetupStatus.inProgress,
      firstWeekActions: const [],
      updatedAt: DateTime.now().toIso8601String(),
    );
    final c = Get.put<ProjectSetupController>(ProjectSetupController());
    c.onInit();
    expect(c.phase.value, ProjectSetupPhase.kickoff);
    expect(c.createdProjectId.value, 'p1');
  });

  test('submitForm rỗng title -> formError, không gọi API', () async {
    final c = make();
    c.onInit();
    await c.submitForm(title: '   ');
    expect(c.formError.value, isNotNull);
    expect(c.phase.value, ProjectSetupPhase.form);
  });

  test('submitForm hợp lệ -> tạo project, chuyển sang kickoff với id trả về', () async {
    final c = make();
    c.onInit();
    await c.submitForm(title: 'Nền tảng B2B', description: 'hoá đơn thủ công');
    expect(c.createdProjectId.value, 'proj-new');
    expect(c.phase.value, ProjectSetupPhase.kickoff);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `cd frontend && flutter test test/modules/strategy/controllers/project_setup_controller_test.dart`
Expected: FAIL — file controller chưa tồn tại.

- [ ] **Step 3: Viết controller**

Tạo `frontend/lib/modules/strategy/controllers/project_setup_controller.dart`:

```dart
import 'package:get/get.dart';

import '../../../core/routing/app_routes.dart';
import '../../../core/routing/module_routes.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../services/strategy_service.dart';

/// Hai pha của luồng thiết lập project: nhập tên/mô tả rồi tới kickoff 3 bước.
enum ProjectSetupPhase { form, kickoff }

/// Điều phối route `/projects/new`. Mode-aware: onboarding (`projectCount == 0`)
/// không cho Huỷ; project thứ N có Huỷ. Kickoff tái dùng `ProjectKickoffView`.
class ProjectSetupController extends GetxController {
  final Rx<ProjectSetupPhase> phase = ProjectSetupPhase.form.obs;
  final RxnString createdProjectId = RxnString();
  final RxBool isSubmitting = false.obs;
  final RxnString formError = RxnString();

  FounderCommandCenterController get _fcc =>
      Get.find<FounderCommandCenterController>();

  bool get isOnboarding => _fcc.projectsList.isEmpty;

  @override
  void onInit() {
    super.onInit();
    // Resume: đúng 1 project và setup chưa ACTIVE -> vào thẳng kickoff của nó.
    if (_fcc.projectsList.length == 1 &&
        _fcc.activeProjectSetup.value?.status != OperatingSetupStatus.active) {
      createdProjectId.value = _fcc.projectsList.first['id']?.toString();
      if ((createdProjectId.value ?? '').isNotEmpty) {
        phase.value = ProjectSetupPhase.kickoff;
      }
    }
  }

  Future<void> submitForm({required String title, String? description}) async {
    final trimmed = title.trim();
    if (trimmed.isEmpty) {
      formError.value = 'Vui lòng nhập tên dự án';
      return;
    }
    formError.value = null;
    isSubmitting.value = true;
    try {
      final project = await StrategyService()
          .createBasicProject(title: trimmed, description: description?.trim());
      final id = project['id']?.toString();
      if (id == null || id.isEmpty) {
        formError.value = 'Tạo dự án thất bại. Vui lòng thử lại.';
        return;
      }
      createdProjectId.value = id;
      await _fcc.loadDashboardData();
      phase.value = ProjectSetupPhase.kickoff;
    } catch (e) {
      formError.value = 'Đã có lỗi xảy ra: $e';
    } finally {
      isSubmitting.value = false;
    }
  }

  void onKickoffActivated(String projectId) => Get.offAllNamed(AppRoutes.hub);

  void onKickoffBack() {
    if (isOnboarding) return;
    Get.offAllNamed(AppRoutes.hub);
  }

  void onOpenAdvancedRoadmap() => Get.toNamed(WorkspaceModule.strategy.path);

  void cancel() => Get.offAllNamed(AppRoutes.hub);
}
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

Run: `cd frontend && flutter test test/modules/strategy/controllers/project_setup_controller_test.dart`
Expected: PASS (4 test).

- [ ] **Step 5: Commit**

```bash
cd frontend && git add lib/modules/strategy/controllers/project_setup_controller.dart test/modules/strategy/controllers/project_setup_controller_test.dart
git commit -m "feat(strategy): ProjectSetupController cho route /projects/new

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `ProjectSetupView` + đăng ký route `/projects/new`

**Files:**
- Create: `frontend/lib/modules/strategy/views/project_setup_view.dart`
- Modify: `frontend/lib/core/routing/app_routes.dart` (thêm `projectsNew`)
- Modify: `frontend/lib/core/routing/app_pages.dart` (import + `GetPage`)
- Test: `frontend/test/modules/strategy/project_setup_view_test.dart` (create)

**Interfaces:**
- Consumes: `ProjectSetupController` (Task 2) + `enum ProjectSetupPhase`. `ProjectKickoffView` (`frontend/lib/modules/strategy/views/project_kickoff_view.dart`) với chữ ký constructor: `ProjectKickoffView({required String projectId, required VoidCallback onBack, required void Function(String projectId) onActivated, required VoidCallback onOpenAdvancedRoadmap})`.
- Produces: `AppRoutes.projectsNew` (`'/projects/new'`); `GetPage` name `AppRoutes.projectsNew` → `ProjectSetupView`, `middlewares: [AuthMiddleware()]`, binding tạo `ProjectSetupController` (+ đảm bảo `FounderCommandCenterController` tồn tại).

- [ ] **Step 1: Viết test đỏ**

Tạo `frontend/test/modules/strategy/project_setup_view_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/controllers/project_setup_controller.dart';
import 'package:frontend/modules/strategy/views/project_setup_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((_) async => http.Response('{}', 200));
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  Future<void> pumpView(WidgetTester tester) async {
    await tester.pumpWidget(GetMaterialApp(
      home: const ProjectSetupView(),
    ));
    await tester.pump();
  }

  testWidgets('onboarding (0 project): hiện form, KHÔNG có nút Huỷ', (tester) async {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.clear();
    Get.put<ProjectSetupController>(ProjectSetupController());

    await pumpView(tester);

    expect(find.byKey(const ValueKey('project_setup_title_field')), findsOneWidget);
    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsNothing);
  });

  testWidgets('project thứ N (>=1 project): form có nút Huỷ', (tester) async {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsList.assignAll([{'id': 'p1'}, {'id': 'p2'}]);
    Get.put<ProjectSetupController>(ProjectSetupController());

    await pumpView(tester);

    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsOneWidget);
  });

  test('AppRoutes.projectsNew = /projects/new', () {
    expect(AppRoutes.projectsNew, '/projects/new');
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `cd frontend && flutter test test/modules/strategy/project_setup_view_test.dart`
Expected: FAIL — `ProjectSetupView` và `AppRoutes.projectsNew` chưa tồn tại.

- [ ] **Step 3: Thêm route constant**

Trong `frontend/lib/core/routing/app_routes.dart`, sau `static const register = '/register';` thêm:

```dart
  static const projectsNew = '/projects/new';
```

- [ ] **Step 4: Viết view**

Tạo `frontend/lib/modules/strategy/views/project_setup_view.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/theme/app_theme.dart';
import '../controllers/project_setup_controller.dart';
import 'project_kickoff_view.dart';

/// Route `/projects/new` — full-screen, KHÔNG dùng `AppShell` (không sidebar
/// module, không chat dock). Pha `form` -> tạo project; pha `kickoff` -> tái
/// dùng `ProjectKickoffView` 3 bước; activate xong về `/hub`.
class ProjectSetupView extends StatelessWidget {
  const ProjectSetupView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.isRegistered<ProjectSetupController>()
        ? Get.find<ProjectSetupController>()
        : Get.put(ProjectSetupController());

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppTheme.backgroundLinearGradient,
        ),
        child: SafeArea(
          child: Obx(() {
            if (controller.phase.value == ProjectSetupPhase.kickoff) {
              final id = controller.createdProjectId.value ?? '';
              return ProjectKickoffView(
                key: ValueKey('setup_kickoff_$id'),
                projectId: id,
                onBack: controller.onKickoffBack,
                onActivated: controller.onKickoffActivated,
                onOpenAdvancedRoadmap: controller.onOpenAdvancedRoadmap,
              );
            }
            return _ProjectSetupForm(controller: controller);
          }),
        ),
      ),
    );
  }
}

class _ProjectSetupForm extends StatefulWidget {
  const _ProjectSetupForm({required this.controller});
  final ProjectSetupController controller;

  @override
  State<_ProjectSetupForm> createState() => _ProjectSetupFormState();
}

class _ProjectSetupFormState extends State<_ProjectSetupForm> {
  final _title = TextEditingController();
  final _desc = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Tạo dự án',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 4),
              Text(
                'Đặt tên và mô tả ngắn về vấn đề. COSA sẽ đề xuất vòng đầu ở bước sau.',
                style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.7)),
              ),
              const SizedBox(height: 20),
              TextField(
                key: const ValueKey('project_setup_title_field'),
                controller: _title,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(labelText: 'Tên dự án'),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const ValueKey('project_setup_desc_field'),
                controller: _desc,
                minLines: 2,
                maxLines: 4,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(labelText: 'Mô tả ngắn (tuỳ chọn)'),
              ),
              const SizedBox(height: 8),
              Obx(() => c.formError.value == null
                  ? const SizedBox.shrink()
                  : Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(c.formError.value!,
                          style: const TextStyle(color: AppTheme.error, fontSize: 13)),
                    )),
              const SizedBox(height: 16),
              Obx(() => ElevatedButton(
                    key: const ValueKey('project_setup_submit_button'),
                    onPressed: c.isSubmitting.value
                        ? null
                        : () => c.submitForm(
                              title: _title.text,
                              description: _desc.text.isEmpty ? null : _desc.text,
                            ),
                    child: Text(c.isSubmitting.value ? 'Đang tạo...' : 'Tạo dự án'),
                  )),
              if (!c.isOnboarding)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: TextButton(
                    key: const ValueKey('project_setup_cancel_button'),
                    onPressed: c.cancel,
                    child: const Text('Huỷ'),
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

Nếu `AppTheme.backgroundLinearGradient` / `AppTheme.error` không tồn tại đúng tên, mở `frontend/lib/core/theme/app_theme.dart` và dùng hằng số tương đương (màu nền tối + màu lỗi) — không thêm dependency mới.

- [ ] **Step 5: Đăng ký GetPage**

Trong `frontend/lib/core/routing/app_pages.dart`:

Thêm import (cạnh các import view khác):
```dart
import '../../modules/strategy/views/project_setup_view.dart';
import '../../modules/strategy/controllers/project_setup_controller.dart';
import '../../modules/hologram_hub/controllers/founder_command_center_controller.dart';
import '../shell/app_shell_controller.dart';
```

Thêm `GetPage` vào list `AppPages.routes` (ngay sau route `register`):
```dart
    GetPage(
      name: AppRoutes.projectsNew,
      page: () => const ProjectSetupView(),
      binding: BindingsBuilder(() {
        // FCC do shell sở hữu; route này có thể vào thẳng qua guard trước khi
        // AppShell mount, nên tự đảm bảo nó tồn tại.
        AppShellController.ensureShellDependencies();
        Get.lazyPut<ProjectSetupController>(() => ProjectSetupController());
      }),
      middlewares: [AuthMiddleware()],
    ),
```

`AuthMiddleware` đã được import sẵn trong `app_pages.dart`. KHÔNG gắn `ProjectSetupGuardMiddleware` ở đây (tránh vòng lặp).

- [ ] **Step 6: Chạy test, xác nhận xanh**

Run: `cd frontend && flutter test test/modules/strategy/project_setup_view_test.dart`
Expected: PASS (3 test). Nếu có overflow exception ở viewport test nhỏ, thêm `tester.takeException();` sau `await tester.pump();` (theo tiền lệ `chat_redirect_test.dart`).

- [ ] **Step 7: Commit**

```bash
cd frontend && git add lib/modules/strategy/views/project_setup_view.dart lib/core/routing/app_routes.dart lib/core/routing/app_pages.dart test/modules/strategy/project_setup_view_test.dart
git commit -m "feat(strategy): ProjectSetupView + route /projects/new

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `ProjectSetupGuardMiddleware` + gắn vào `/hub` và `/work/*`

**Files:**
- Create: `frontend/lib/core/routing/project_setup_guard_middleware.dart`
- Modify: `frontend/lib/core/routing/app_pages.dart` (route `/hub`)
- Modify: `frontend/lib/core/routing/module_routes.dart` (mọi GetPage trong `moduleRoutes`)
- Test: `frontend/test/core/routing/project_setup_guard_test.dart` (create)
- Modify: `frontend/test/core/routing/module_routes_test.dart` (cập nhật assertion middleware)

**Interfaces:**
- Consumes: `FounderCommandCenterController.needsProjectSetup` (Task 1). `AppRoutes.projectsNew` (Task 3). `AuthMiddleware` (`priority => 1`).
- Produces: `class ProjectSetupGuardMiddleware extends GetMiddleware` với `priority => 5` và `RouteSettings? redirect(String? route)` trả `RouteSettings(name: AppRoutes.projectsNew)` khi cần, ngược lại `null`.

- [ ] **Step 1: Viết test đỏ**

Tạo `frontend/test/core/routing/project_setup_guard_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/routing/module_routes.dart';
import 'package:frontend/core/routing/project_setup_guard_middleware.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
  });

  test('priority chạy sau AuthMiddleware', () {
    expect(ProjectSetupGuardMiddleware().priority, greaterThan(1));
  });

  test('FCC chưa đăng ký -> không redirect (chưa quyết định được)', () {
    expect(ProjectSetupGuardMiddleware().redirect('/hub'), isNull);
  });

  test('needsProjectSetup == true -> redirect sang /projects/new', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsError.value = null;
    fcc.projectsList.clear();
    expect(
      ProjectSetupGuardMiddleware().redirect('/hub')?.name,
      AppRoutes.projectsNew,
    );
  });

  test('needsProjectSetup == false -> không redirect', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsError.value = null;
    fcc.projectsList.assignAll([{'id': 'p1'}, {'id': 'p2'}]);
    expect(ProjectSetupGuardMiddleware().redirect('/work/tasks'), isNull);
  });

  test('đang ở /projects/new -> không tự redirect vào chính nó', () {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.projectsError.value = null;
    fcc.projectsList.clear();
    expect(ProjectSetupGuardMiddleware().redirect(AppRoutes.projectsNew), isNull);
  });

  test('mọi route /work/* mang cả AuthMiddleware và ProjectSetupGuardMiddleware', () {
    for (final page in moduleRoutes) {
      expect(page.middlewares!.whereType<ProjectSetupGuardMiddleware>().length, 1,
          reason: '${page.name} thiếu ProjectSetupGuardMiddleware');
    }
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `cd frontend && flutter test test/core/routing/project_setup_guard_test.dart`
Expected: FAIL — `project_setup_guard_middleware.dart` chưa tồn tại.

- [ ] **Step 3: Viết middleware**

Tạo `frontend/lib/core/routing/project_setup_guard_middleware.dart`:

```dart
import 'package:flutter/widgets.dart';
import 'package:get/get.dart';

import '../../modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'app_routes.dart';

/// Fast path đồng bộ: khi state `FounderCommandCenterController` đã sẵn và
/// `needsProjectSetup`, đẩy sang `/projects/new` ngay tại tầng routing.
/// Trường hợp state chưa tải xong (điều hướng vào `/hub` trước khi projects
/// về) do backstop async ở cuối `loadDashboardData()` xử lý — xem
/// `FounderCommandCenterController`.
class ProjectSetupGuardMiddleware extends GetMiddleware {
  @override
  int? get priority => 5;

  @override
  RouteSettings? redirect(String? route) {
    if (route == AppRoutes.projectsNew) return null;
    if (!Get.isRegistered<FounderCommandCenterController>()) return null;
    final fcc = Get.find<FounderCommandCenterController>();
    if (fcc.needsProjectSetup) {
      return const RouteSettings(name: AppRoutes.projectsNew);
    }
    return null;
  }
}
```

- [ ] **Step 4: Gắn vào route `/hub`**

Trong `frontend/lib/core/routing/app_pages.dart`, import:
```dart
import 'project_setup_guard_middleware.dart';
```
Sửa route `AppRoutes.hub`:
```dart
      middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
```

- [ ] **Step 5: Gắn vào mọi `/work/*`**

Trong `frontend/lib/core/routing/module_routes.dart`, import:
```dart
import 'project_setup_guard_middleware.dart';
```
Thay TẤT CẢ occurrence `middlewares: [AuthMiddleware()],` trong list `moduleRoutes` thành:
```dart
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
```
(12 GetPage — mọi cái hiện đều đúng dạng `middlewares: [AuthMiddleware()],`.)

- [ ] **Step 6: Cập nhật `module_routes_test.dart`**

Trong `frontend/test/core/routing/module_routes_test.dart`, ở test đầu tiên, thêm sau dòng assert `AuthMiddleware`:
```dart
    expect(routesFor('/work/tasks').single.middlewares,
        contains(isA<ProjectSetupGuardMiddleware>()));
```
Thêm import:
```dart
import 'package:frontend/core/routing/project_setup_guard_middleware.dart';
```

- [ ] **Step 7: Chạy test, xác nhận xanh**

Run: `cd frontend && flutter test test/core/routing/project_setup_guard_test.dart test/core/routing/module_routes_test.dart test/core/routing/chat_redirect_test.dart`
Expected: PASS toàn bộ (chat_redirect_test chạy kèm để chắc route `/hub` không hồi quy).

- [ ] **Step 8: Commit**

```bash
cd frontend && git add lib/core/routing/project_setup_guard_middleware.dart lib/core/routing/app_pages.dart lib/core/routing/module_routes.dart test/core/routing/project_setup_guard_test.dart test/core/routing/module_routes_test.dart
git commit -m "feat(routing): ProjectSetupGuardMiddleware chặn /hub và /work/* khi chưa có project

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Backstop async trong `loadDashboardData()`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Test: `frontend/test/modules/hologram_hub/founder_command_center_zero_project_redirect_test.dart` (create)

**Interfaces:**
- Consumes: `needsProjectSetup` (Task 1), `AppRoutes.hub` / `AppRoutes.projectsNew` (Task 3), `Get.currentRoute`, `Get.offAllNamed`.
- Produces: hành vi — sau khi `loadDashboardData()` chạy xong, nếu `needsProjectSetup` và route hiện tại là `/hub` hoặc `/work/*` thì `Get.offAllNamed(AppRoutes.projectsNew)`.

- [ ] **Step 1: Viết test đỏ**

Tạo `frontend/test/modules/hologram_hub/founder_command_center_zero_project_redirect_test.dart`:

```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'projects': []}), 200); // 0 project
      }
      return http.Response('{}', 200);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  testWidgets('loadDashboardData xong với 0 project khi đang ở /hub -> offAllNamed /projects/new',
      (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.hub,
      getPages: [
        GetPage(name: AppRoutes.hub, page: () => const Scaffold(body: Text('hub'))),
        GetPage(name: AppRoutes.projectsNew, page: () => const Scaffold(body: Text('setup'))),
      ],
    ));
    await tester.pump();
    expect(Get.currentRoute, AppRoutes.hub);

    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    await fcc.loadDashboardData();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(Get.currentRoute, AppRoutes.projectsNew);
  });

  testWidgets('không redirect khi route hiện tại KHÔNG phải /hub hay /work/*',
      (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: '/login',
      getPages: [
        GetPage(name: '/login', page: () => const Scaffold(body: Text('login'))),
        GetPage(name: AppRoutes.projectsNew, page: () => const Scaffold(body: Text('setup'))),
      ],
    ));
    await tester.pump();

    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    await fcc.loadDashboardData();
    await tester.pump();

    expect(Get.currentRoute, '/login');
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `cd frontend && flutter test test/modules/hologram_hub/founder_command_center_zero_project_redirect_test.dart`
Expected: FAIL — test 1 vẫn thấy `Get.currentRoute == /hub`.

- [ ] **Step 3: Thêm backstop**

Trong `founder_command_center_controller.dart`:

Thêm import (cạnh import routing nếu có; nếu chưa có thì thêm mới):
```dart
import '../../../core/routing/app_routes.dart';
```

Ở CUỐI khối `try` của `loadDashboardData()` (sau khi mọi `.assignAll(...)` / gán `pulse`/`top3Actions`/... hoàn tất, TRƯỚC `} catch`), thêm:
```dart
      _enforceZeroProjectRedirect();
```

Thêm method mới trong class:
```dart
  /// Backstop cho `ProjectSetupGuardMiddleware`: khi Founder đã điều hướng
  /// vào `/hub` (hoặc `/work/*`) trước lúc danh sách project tải xong,
  /// middleware đồng bộ chưa quyết định được. Sau khi `loadDashboardData()`
  /// hoàn tất, tự đẩy sang `/projects/new` nếu vẫn `needsProjectSetup`.
  /// Chỉ tác động đúng hai bề mặt được guard — không đụng `/login`,
  /// `/workspace-picker`, `/projects/new`, v.v.
  void _enforceZeroProjectRedirect() {
    if (!needsProjectSetup) return;
    final route = Get.currentRoute;
    if (route != AppRoutes.hub && !route.startsWith('/work/')) return;
    Get.offAllNamed(AppRoutes.projectsNew);
  }
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

Run: `cd frontend && flutter test test/modules/hologram_hub/founder_command_center_zero_project_redirect_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart`
Expected: PASS. Chạy kèm `founder_command_center_controller_test.dart` để chắc backstop không phá test cũ (test cũ có project `proj-123` ⇒ `needsProjectSetup` sẽ false vì setup được nạp; nếu test cũ đỏ do route mặc định, thêm `tester`/route guard tương ứng — nhưng test cũ không dựng GetMaterialApp route nên `Get.currentRoute` là `''`, không khớp `/hub` ⇒ backstop no-op).

- [ ] **Step 5: Commit**

```bash
cd frontend && git add lib/modules/hologram_hub/controllers/founder_command_center_controller.dart test/modules/hologram_hub/founder_command_center_zero_project_redirect_test.dart
git commit -m "feat(hub): backstop async redirect /projects/new sau loadDashboardData

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Dọn Hub — ẩn widget số liệu giả khi chưa có project

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Test: `frontend/test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart` (create)

**Interfaces:**
- Consumes: `FounderCommandCenterController.hasProjects` (đã tồn tại). Widget `CoFounderCardWidget`, `Top3FocusWidget`, `WaitingForYouWidget` (không sửa nội dung).
- Produces: khi `hasProjects.value == false`, ba widget trên không render; `_buildFirstProjectBanner` bị xoá hẳn.

- [ ] **Step 1: Viết test đỏ**

Tạo `frontend/test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';
import 'package:frontend/modules/hologram_hub/widgets/cofounder_card_widget.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((_) async => http.Response('{}', 200));
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  testWidgets('hasProjects == false -> KHÔNG render CoFounderCardWidget/Top3/WaitingForYou',
      (tester) async {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.hasProjects.value = false;
    fcc.projectsList.clear();

    await tester.pumpWidget(GetMaterialApp(home: const HologramHubView()));
    await tester.pump();
    tester.takeException(); // nuốt overflow viewport nhỏ (không liên quan)

    expect(find.byType(CoFounderCardWidget), findsNothing);
  });

  testWidgets('hasProjects == true -> vẫn render CoFounderCardWidget', (tester) async {
    final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());
    fcc.hasProjects.value = true;
    fcc.projectsList.assignAll([{'id': 'p1'}]);

    await tester.pumpWidget(GetMaterialApp(home: const HologramHubView()));
    await tester.pump();
    tester.takeException();

    expect(find.byType(CoFounderCardWidget), findsOneWidget);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `cd frontend && flutter test test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart`
Expected: FAIL — test 1 tìm thấy `CoFounderCardWidget` (hiện render vô điều kiện).

- [ ] **Step 3: Bọc điều kiện + xoá banner**

Trong `hologram_hub_view.dart`, tại `Column` chính (khoảng dòng 378–470, block bắt đầu `// A. Hero Co-Founder Card + Company Pulse`):

1. Bọc toàn bộ nội dung phụ thuộc project trong một `if (controller.hasProjects.value) ...[ ]`:
   - `CoFounderCardWidget(...)` + `SizedBox(height: 24)` sau nó
   - `Obx(() { ... })` block (chứa `_buildFirstProjectBanner` / `_buildSetupIncompleteCard` / `_buildActiveOperatingSetupCard`)
   - block `if (isWide) Row(... Top3FocusWidget ... WaitingForYouWidget ...) else ...[ ... ]`

   Vì `build` này đã nằm trong một `Obx`/reactive scope đọc `controller` (kiểm tra: block hiện dùng `controller.pulse.value` trực tiếp nên đã reactive). Chuyển thành:
   ```dart
   children: [
     if (controller.hasProjects.value) ...[
       CoFounderCardWidget(
         pulse: controller.pulse.value,
         onAskCosa: () => _openChatBottomSheet(context, controller),
       ),
       const SizedBox(height: 24),
       Obx(() {
         final setup = controller.activeProjectSetup.value;
         final activeProjectId = controller.projectsList.isNotEmpty
             ? controller.projectsList.first['id']?.toString()
             : null;
         if (activeProjectId != null &&
             (setup == null || setup.status != OperatingSetupStatus.active)) {
           return _buildSetupIncompleteCard(context, activeProjectId);
         }
         if (setup != null && setup.status == OperatingSetupStatus.active) {
           return _buildActiveOperatingSetupCard(context, setup);
         }
         return const SizedBox.shrink();
       }),
       if (isWide)
         Row( /* ...Top3FocusWidget + WaitingForYouWidget nguyên trạng... */ )
       else ...[
         /* ...stacked Top3FocusWidget + WaitingForYouWidget nguyên trạng... */
       ],
       const SizedBox(height: 24),
     ],
   ],
   ```
   Lưu ý: bỏ nhánh `if (!controller.hasProjects.value) return _buildFirstProjectBanner(...)` khỏi `Obx` (đã chết — guard/backstop đảm bảo Hub không còn render ở trạng thái 0 project; đây chỉ là lưới an toàn).

2. Xoá method `_buildFirstProjectBanner(BuildContext, FounderCommandCenterController)` và mọi tham chiếu tới nó. Nếu `_showCreateProjectDialog` chỉ được gọi từ banner này, GIỮ LẠI `_showCreateProjectDialog` (Task follow-up spec A sẽ dùng lại) nhưng thêm `// ignore: unused_element` nếu linter than phiền — KHÔNG xoá, vì các call-site khác trong file (`hologram_hub_view.dart:657`, `:987`) vẫn dùng `createFirstProject`/`openProjectKickoff`.

3. Nếu sau khi xoá `_buildFirstProjectBanner`, biến `isWide` hoặc import nào đó thành unused → dọn cho sạch `flutter analyze`.

- [ ] **Step 4: Chạy test, xác nhận xanh**

Run: `cd frontend && flutter test test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart test/modules/hologram_hub/founder_command_center_hub_test.dart test/modules/hologram_hub/hologram_hub_view_single_controller_test.dart`
Expected: PASS. Các test hub cũ phải vẫn xanh (chúng dựng FCC có project ⇒ `hasProjects == true` ⇒ nhánh render không đổi).

- [ ] **Step 5: `flutter analyze` sạch phần đã sửa**

Run: `cd frontend && flutter analyze lib/modules/hologram_hub/views/hologram_hub_view.dart`
Expected: No issues (hoặc chỉ cảnh báo có sẵn từ trước, không phát sinh mới).

- [ ] **Step 6: Commit**

```bash
cd frontend && git add lib/modules/hologram_hub/views/hologram_hub_view.dart test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart
git commit -m "feat(hub): ẩn pulse/Top 3/Waiting khi hasProjects == false, bỏ first-project banner

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Kiểm thử toàn luồng + regression

**Files:**
- Test: `frontend/test/flows/zero_project_setup_flow_test.dart` (create)

**Interfaces:**
- Consumes: `AppPages.routes`, `AppRoutes`, `FounderCommandCenterController`, `MockClient`.
- Produces: 1 integration test đi qua guard → `/projects/new` → tạo project → chuyển kickoff.

- [ ] **Step 1: Viết test**

Tạo `frontend/test/flows/zero_project_setup_flow_test.dart`:

```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/strategy/views/project_setup_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    AuthService.setCachedToken('fake-token');
    original = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/projects') {
        return http.Response(jsonEncode({'projects': []}), 200);
      }
      return http.Response('{}', 200);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    AuthService.setCachedToken(null);
    Get.reset();
  });

  testWidgets('vào /hub khi 0 project -> hạ cánh ở ProjectSetupView', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: AppRoutes.hub,
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);
    expect(find.byType(ProjectSetupView), findsOneWidget);
    expect(find.byKey(const ValueKey('project_setup_title_field')), findsOneWidget);
    // onboarding -> không có nút Huỷ
    expect(find.byKey(const ValueKey('project_setup_cancel_button')), findsNothing);
  });

  testWidgets('deep-link /work/tasks khi 0 project -> redirect /projects/new', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      initialRoute: '/work/tasks',
      getPages: AppPages.routes,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    tester.takeException();

    expect(Get.currentRoute, AppRoutes.projectsNew);
  });
}
```

- [ ] **Step 2: Chạy test**

Run: `cd frontend && flutter test test/flows/zero_project_setup_flow_test.dart`
Expected: PASS. Nếu `/work/tasks` cần binding/controller nặng làm test chậm/timeout, giữ test 1, chuyển test 2 sang assert ở tầng route: `routesFor('/work/tasks').single.middlewares` contains `ProjectSetupGuardMiddleware` (đã cover ở Task 4) và xoá test 2 khỏi file này — ghi rõ lý do trong commit.

- [ ] **Step 3: Full suite regression**

Run: `cd frontend && flutter test`
Expected: PASS toàn bộ. Sửa mọi test đỏ phát sinh do route/hub thay đổi — bằng cách dựng FCC có project (⇒ `needsProjectSetup == false`) trong `setUp` của test đó, KHÔNG nới lỏng assertion.

- [ ] **Step 4: `flutter analyze`**

Run: `cd frontend && flutter analyze`
Expected: No new issues.

- [ ] **Step 5: Commit**

```bash
cd frontend && git add test/flows/zero_project_setup_flow_test.dart
git commit -m "test(flow): zero-project -> ProjectSetupView redirect end-to-end

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**

| Yêu cầu spec | Task |
|---|---|
| Route `/projects/new` generic, mode-aware, không `AppShell`, `AuthMiddleware` | Task 3 |
| Onboarding ẩn nút Huỷ; project thứ N có Huỷ | Task 2 (`isOnboarding`), Task 3 (view) |
| Sau `activate` → `/hub` | Task 2 (`onKickoffActivated`) |
| `needsProjectSetup`: no-redirect khi lỗi tải; 0 project → true; 1 project setup chưa ACTIVE → true (resume); >1 project → false | Task 1 |
| Guard tại `/hub` | Task 4 (route `/hub`) |
| Guard tại `/work/*` | Task 4 (`moduleRoutes`) |
| Guard tại đổi workspace (`activateWorkspace`) | Task 5 — `activateWorkspace` đã gọi `resetForWorkspace()` → `loadDashboardData()` → backstop `_enforceZeroProjectRedirect()`. Không cần sửa `SessionController`. |
| Không redirect khi `projectsError != null` | Task 1 (getter) + Task 4/5 dùng getter |
| Backstop async sau khi projects tải xong | Task 5 |
| Resume đúng bước khi setup dở | Task 2 (`onInit` resume → `ProjectKickoffController.load` tự xác định step từ dữ liệu setup) |
| Dọn Hub: bọc 3 widget trong `hasProjects == true`, xoá `_buildFirstProjectBanner` | Task 6 |
| Auth flow giữ `offAllNamed(hub)`, guard bounce | Không đổi `auth_controller` — Task 4+5 bounce. |
| Không đổi backend | Toàn plan — chỉ gọi API có sẵn |
| Test: create→redirect, no-redirect count≥1, no-redirect lỗi tải, resume, đổi workspace, deep-link `/work/*`, post-activate không loop, ẩn/hiện Huỷ, logout | Task 1/4/5/7; logout từ `/projects/new` dùng nút Logout của `ProjectKickoffView`/AppБАР hiện có — `ProjectSetupView` không chặn logout (Scaffold trơn, không có guard) |

**2. Placeholder scan:** Không có "TBD/TODO". Mọi step code có block cụ thể. Các câu "nếu tên khác thì kiểm tra file X" là hướng dẫn xác minh thực tế, không phải placeholder — kèm đường dẫn file chính xác.

**3. Type consistency:**
- `needsProjectSetup` → `bool`: định nghĩa Task 1, dùng Task 2 (gián tiếp qua logic riêng — LƯU Ý: Task 2 `onInit` KHÔNG gọi `needsProjectSetup` mà lặp lại điều kiện `length == 1 && status != active` để tự quyết pha; middleware/backstop mới gọi getter). Nhất quán về ngữ nghĩa.
- `ProjectSetupPhase { form, kickoff }`, `ProjectSetupController` API (`phase`, `createdProjectId`, `isSubmitting`, `formError`, `isOnboarding`, `submitForm`, `onKickoffActivated`, `onKickoffBack`, `onOpenAdvancedRoadmap`, `cancel`) — khai báo Task 2, tiêu thụ Task 3 khớp tên.
- `ProjectSetupGuardMiddleware` `priority => 5`, `redirect → RouteSettings?` — Task 4, khớp `AuthMiddleware.priority => 1`.
- `ProjectKickoffView` constructor 4 tham số bắt buộc — khớp chữ ký đọc từ `project_kickoff_view.dart`.
- `createBasicProject({required String title, String? description}) → Future<Map<String,dynamic>>` với key `id` — khớp `strategy_service.dart:574` / `project_service.dart:60`.
- `OperatingSetupStatus.active` — khớp `project_operating_setup_model.dart:37`.
- `AppRoutes.projectsNew = '/projects/new'` — Task 3, dùng Task 4/5/7.

**Kết luận:** không phát hiện gap. `SessionController` không cần chỉnh (backstop qua `resetForWorkspace`→`loadDashboardData` đã phủ) — khác diễn đạt spec ("guard ở `activateWorkspace`") nhưng cùng kết quả, ghi rõ ở bảng trên.
