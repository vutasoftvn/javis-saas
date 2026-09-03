# Tab "Tổng quan" cho module Work — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm tab "Tổng quan" vào module Work (`/work/tasks`), hiển thị việc hôm nay, thống kê task theo trạng thái, thông tin quản trị project đang chọn, và tóm tắt OKR/12WY — không đổi Kanban hiện có.

**Architecture:** `TasksView` đổi từ 1 màn hình đơn thành `TabBarView` 2 tab (Tổng quan + Kanban, nội dung Kanban tách nguyên trạng thành `TaskKanbanTab`). `WorkOverviewController` mới đọc lại `TasksController.tasks` đã tải sẵn (không fetch riêng cho 2 khối đầu), gọi `ProjectOperatingSetupService`/`OkrService`/`TwelveWyService` hiện có cho 2 khối sau.

**Tech Stack:** Flutter, GetX, `http.testing.MockClient` cho test (pattern đã dùng trong `okr_service_test.dart`).

## Global Constraints

- Không tạo endpoint backend mới (spec §2.3, §3).
- Không đổi logic/API của Kanban hiện có — chỉ di chuyển UI (spec §2.1).
- Không xây chart library — chỉ thẻ số + list (spec §3).
- OKR/12WY summary hiển thị theo cycle hiện tại chung của workspace, KHÔNG lọc
  theo project đang chọn — đây là giới hạn có sẵn của `OkrService.getObjectives()`
  (không nhận tham số project) và `TwelveWyService.getDashboard(projectId)`
  (tham số `projectId` hiện bị bỏ qua trong implementation, luôn lấy cycle đầu
  tiên toàn workspace — xem `twelve_wy_service.dart:35-46`). Không sửa 2 service
  này trong plan này (ngoài phạm vi spec).
- "Bấm vào mở task đó" ở khối Việc hôm nay: xác nhận qua code, **không có** cơ
  chế mở chi tiết 1 task nào tồn tại sẵn (`kanban_task_card.dart` không có
  `onTap` mở dialog/route nào) — spec giả định sai. Xử lý: bấm vào 1 item ở
  "Việc hôm nay" chuyển sang tab Kanban (không mở chi tiết task, vì việc đó
  chưa tồn tại và không thuộc phạm vi spec này).

---

## Task 1: Tách Kanban thành tab riêng, dựng khung TabBarView

**Files:**
- Create: `frontend/lib/modules/tasks/views/tabs/task_kanban_tab.dart`
- Create: `frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart` (khung rỗng, nội dung thật thêm ở Task 2-4)
- Modify: `frontend/lib/modules/tasks/views/tasks_view.dart`
- Test: `frontend/test/modules/tasks/views/tasks_view_test.dart`

**Interfaces:**
- Produces: `TaskKanbanTab` (StatelessWidget, không tham số, đọc `Get.find<TasksController>()` y hệt `TasksView` cũ).
- Produces: `WorkOverviewTab` (StatelessWidget, không tham số) — khung rỗng ở task này, Task 2 sẽ điền nội dung.

- [ ] **Step 1: Viết test trước — xác nhận 2 tab tồn tại và Kanban vẫn hiển thị đúng cột**

```dart
// frontend/test/modules/tasks/views/tasks_view_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/views/tasks_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    Get.put(TasksController());
  });

  testWidgets('has Tổng quan and Kanban tabs, Kanban shows all 5 columns', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: TasksView())),
    );
    await tester.pump();

    expect(find.text('Tổng quan'), findsOneWidget);
    expect(find.text('Kanban'), findsOneWidget);

    // Mặc định vào tab đầu (Tổng quan) — chuyển sang tab Kanban để kiểm tra
    await tester.tap(find.text('Kanban'));
    await tester.pumpAndSettle();

    for (final title in [
      'Cần làm',
      'Đang làm',
      'Chờ duyệt',
      'Tạm dừng / Nghẽn',
      'Hoàn thành',
    ]) {
      expect(find.text(title), findsWidgets);
    }
  });
}
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/tasks/views/tasks_view_test.dart`
Expected: FAIL — `TasksView` hiện chưa có `TabBar`/text "Tổng quan"/"Kanban".

- [ ] **Step 3: Tạo `TaskKanbanTab` — copy nguyên nội dung Kanban hiện có**

```dart
// frontend/lib/modules/tasks/views/tabs/task_kanban_tab.dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/tasks_controller.dart';
import '../widgets/kanban_column_widget.dart';

class TaskKanbanTab extends GetView<TasksController> {
  const TaskKanbanTab({super.key});

  static const List<Map<String, dynamic>> columns = [
    {'title': 'Cần làm', 'status': 'todo', 'color': Color(0xFF38BDF8)},
    {'title': 'Đang làm', 'status': 'in_progress', 'color': Color(0xFF00F0FF)},
    {'title': 'Chờ duyệt', 'status': 'waiting_approval', 'color': Color(0xFFF59E0B)},
    {'title': 'Tạm dừng / Nghẽn', 'status': 'blocked', 'color': Color(0xFFEF4444)},
    {'title': 'Hoàn thành', 'status': 'done', 'color': Color(0xFF10B981)},
  ];

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }

      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth >= 1400;
            if (isWide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (int i = 0; i < columns.length; i++) ...[
                    if (i > 0) const SizedBox(width: 12),
                    Expanded(
                      child: KanbanColumnWidget(
                        title: columns[i]['title'] as String,
                        status: columns[i]['status'] as String,
                        columnColor: columns[i]['color'] as Color,
                        controller: controller,
                      ),
                    ),
                  ],
                ],
              );
            }

            return ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: columns.length,
              separatorBuilder: (_, _) => const SizedBox(width: 14),
              itemBuilder: (context, index) {
                return SizedBox(
                  width: 290,
                  child: KanbanColumnWidget(
                    title: columns[index]['title'] as String,
                    status: columns[index]['status'] as String,
                    columnColor: columns[index]['color'] as Color,
                    controller: controller,
                  ),
                );
              },
            );
          },
        ),
      );
    });
  }
}
```

- [ ] **Step 4: Tạo khung rỗng `WorkOverviewTab` (nội dung thật ở Task 2-4)**

```dart
// frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart
import 'package:flutter/material.dart';

class WorkOverviewTab extends StatelessWidget {
  const WorkOverviewTab({super.key});

  @override
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}
```

- [ ] **Step 5: Sửa `TasksView` thành `TabBarView` 2 tab**

Thay toàn bộ nội dung `frontend/lib/modules/tasks/views/tasks_view.dart` bằng:

```dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/tasks_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import 'tabs/task_kanban_tab.dart';
import 'tabs/work_overview_tab.dart';
import 'widgets/add_task_dialog.dart';

class TasksView extends GetView<TasksController> {
  const TasksView({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Container(
        color: Colors.transparent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            CosaFloatingAppBar(
              title: 'Công việc & Vận hành',
              subtitle: 'Quản lý tiến độ nhiệm vụ, phê duyệt và điều phối tự động',
              actions: [
                Container(
                  decoration: const BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    tooltip: 'Thêm công việc',
                    icon: const Icon(Icons.add, color: Colors.white, size: 20),
                    onPressed: () => AddTaskDialog.show(context, controller, 'todo'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const TabBar(
              isScrollable: true,
              labelColor: AppTheme.primary,
              unselectedLabelColor: AppTheme.textMutedDark,
              indicatorColor: AppTheme.primary,
              tabs: [
                Tab(text: 'Tổng quan'),
                Tab(text: 'Kanban'),
              ],
            ),
            const SizedBox(height: 12),
            const Expanded(
              child: TabBarView(
                children: [
                  WorkOverviewTab(),
                  TaskKanbanTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

Xoá field `columns` cũ khỏi `TasksView` (đã chuyển sang `TaskKanbanTab`).

- [ ] **Step 6: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/tasks/views/tasks_view_test.dart`
Expected: PASS.

- [ ] **Step 7: `dart analyze` sạch**

Run: `cd frontend && dart analyze lib/modules/tasks/`
Expected: No issues found.

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/tasks/views/tasks_view.dart \
  frontend/lib/modules/tasks/views/tabs/task_kanban_tab.dart \
  frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart \
  frontend/test/modules/tasks/views/tasks_view_test.dart
git commit -m "refactor(tasks): tach Kanban thanh tab rieng, dung khung TabBarView cho TasksView

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: `WorkOverviewController` + khối "Việc hôm nay" và "Thống kê theo trạng thái"

**Files:**
- Create: `frontend/lib/modules/tasks/controllers/work_overview_controller.dart`
- Modify: `frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart`
- Modify: `frontend/lib/modules/tasks/bindings/tasks_binding.dart`
- Test: `frontend/test/modules/tasks/controllers/work_overview_controller_test.dart`

**Interfaces:**
- Consumes: `TasksController.tasks` (`RxList<TaskKanbanModel>`, đã tồn tại — xem `frontend/lib/modules/tasks/controllers/tasks_controller.dart:19`), `TaskKanbanModel.dueDate` (`String?`, format ISO date/datetime — xem `frontend/lib/data/models/task_kanban_model.dart:92,120`), `TaskKanbanStatus` enum (`todo`/`inProgress`/`waitingApproval`/`blocked`/`done`/`cancelled`).
- Produces: `WorkOverviewController({required TasksController tasksController})` — `List<TaskKanbanModel> get todayTasks`, `Map<TaskKanbanStatus, int> get statusCounts` (2 getter thuần, đọc trực tiếp từ `tasksController.tasks`, không có state Rx riêng cho 2 khối này — dùng `Obx` bọc ngoài đọc `tasksController.tasks` để tự rebuild).

- [ ] **Step 1: Viết test trước cho `todayTasks`/`statusCounts`**

```dart
// frontend/test/modules/tasks/controllers/work_overview_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/controllers/work_overview_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('todayTasks includes overdue and due-today, non-done tasks only', () {
    final tasksController = TasksController();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day).toIso8601String();
    final yesterday = DateTime(now.year, now.month, now.day - 1).toIso8601String();
    final tomorrow = DateTime(now.year, now.month, now.day + 1).toIso8601String();

    tasksController.tasks.assignAll([
      TaskKanbanModel(id: '1', title: 'Overdue', status: TaskKanbanStatus.todo, dueDate: yesterday),
      TaskKanbanModel(id: '2', title: 'Due today', status: TaskKanbanStatus.inProgress, dueDate: today),
      TaskKanbanModel(id: '3', title: 'Due tomorrow', status: TaskKanbanStatus.todo, dueDate: tomorrow),
      TaskKanbanModel(id: '4', title: 'Overdue but done', status: TaskKanbanStatus.done, dueDate: yesterday),
      TaskKanbanModel(id: '5', title: 'No due date', status: TaskKanbanStatus.todo, dueDate: null),
    ]);

    final controller = WorkOverviewController(tasksController: tasksController);

    expect(controller.todayTasks.map((t) => t.id).toList(), ['1', '2']);
  });

  test('statusCounts tallies every task by status', () {
    final tasksController = TasksController();
    tasksController.tasks.assignAll([
      TaskKanbanModel(id: '1', title: 'A', status: TaskKanbanStatus.todo),
      TaskKanbanModel(id: '2', title: 'B', status: TaskKanbanStatus.todo),
      TaskKanbanModel(id: '3', title: 'C', status: TaskKanbanStatus.done),
    ]);

    final controller = WorkOverviewController(tasksController: tasksController);

    expect(controller.statusCounts[TaskKanbanStatus.todo], 2);
    expect(controller.statusCounts[TaskKanbanStatus.done], 1);
    expect(controller.statusCounts[TaskKanbanStatus.blocked] ?? 0, 0);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/tasks/controllers/work_overview_controller_test.dart`
Expected: FAIL — file `work_overview_controller.dart` chưa tồn tại.

- [ ] **Step 3: Viết `WorkOverviewController` (chỉ phần Task 2, chưa có phần project/OKR/12WY — Task 3-4 sẽ mở rộng cùng file này)**

```dart
// frontend/lib/modules/tasks/controllers/work_overview_controller.dart
import 'package:get/get.dart';
import '../../../data/models/task_kanban_model.dart';
import 'tasks_controller.dart';

class WorkOverviewController extends GetxController {
  WorkOverviewController({required this.tasksController});

  final TasksController tasksController;

  List<TaskKanbanModel> get todayTasks {
    final now = DateTime.now();
    final startOfToday = DateTime(now.year, now.month, now.day);
    final endOfToday = startOfToday.add(const Duration(days: 1));

    final result = tasksController.tasks.where((t) {
      if (t.status == TaskKanbanStatus.done ||
          t.status == TaskKanbanStatus.cancelled) {
        return false;
      }
      final due = t.dueDate != null ? DateTime.tryParse(t.dueDate!) : null;
      if (due == null) return false;
      return due.isBefore(endOfToday);
    }).toList();

    result.sort((a, b) {
      final dueA = DateTime.tryParse(a.dueDate!)!;
      final dueB = DateTime.tryParse(b.dueDate!)!;
      return dueA.compareTo(dueB);
    });
    return result;
  }

  Map<TaskKanbanStatus, int> get statusCounts {
    final counts = <TaskKanbanStatus, int>{};
    for (final status in TaskKanbanStatus.values) {
      counts[status] = 0;
    }
    for (final task in tasksController.tasks) {
      counts[task.status] = (counts[task.status] ?? 0) + 1;
    }
    return counts;
  }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/tasks/controllers/work_overview_controller_test.dart`
Expected: PASS.

- [ ] **Step 5: Đăng ký `WorkOverviewController` trong `TasksBinding`**

Sửa `frontend/lib/modules/tasks/bindings/tasks_binding.dart`:

```dart
import 'package:get/get.dart';
import '../controllers/tasks_controller.dart';
import '../controllers/work_overview_controller.dart';

class TasksBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<TasksController>(() => TasksController());
    Get.lazyPut<WorkOverviewController>(
      () => WorkOverviewController(tasksController: Get.find<TasksController>()),
    );
  }
}
```

- [ ] **Step 6: Viết nội dung thật cho `WorkOverviewTab` — 2 khối đầu**

```dart
// frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../controllers/work_overview_controller.dart';

class WorkOverviewTab extends GetView<WorkOverviewController> {
  const WorkOverviewTab({super.key});

  static const _statusColors = {
    TaskKanbanStatus.todo: Color(0xFF38BDF8),
    TaskKanbanStatus.inProgress: Color(0xFF00F0FF),
    TaskKanbanStatus.waitingApproval: Color(0xFFF59E0B),
    TaskKanbanStatus.blocked: Color(0xFFEF4444),
    TaskKanbanStatus.done: Color(0xFF10B981),
    TaskKanbanStatus.cancelled: AppTheme.textMutedDark,
  };

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildStatusCounts(),
          const SizedBox(height: 20),
          _buildTodayTasks(),
        ],
      ),
    );
  }

  Widget _buildStatusCounts() {
    return Obx(() {
      final counts = controller.statusCounts;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: TaskKanbanStatus.values
            .where((s) => s != TaskKanbanStatus.cancelled)
            .map((status) {
          return Container(
            width: 150,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _statusColors[status]!.withValues(alpha: 0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${counts[status] ?? 0}',
                  style: TextStyle(
                    color: _statusColors[status],
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  status.title,
                  style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                ),
              ],
            ),
          );
        }).toList(),
      );
    });
  }

  Widget _buildTodayTasks() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Việc hôm nay',
            style: TextStyle(color: AppTheme.textDark, fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Obx(() {
            final tasks = controller.todayTasks;
            if (tasks.isEmpty) {
              return const Text(
                'Không có việc nào đến hạn hôm nay.',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              );
            }
            return Column(
              children: tasks.map((task) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Icon(Icons.circle, size: 8, color: _statusColors[task.status]),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          task.title,
                          style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                        ),
                      ),
                      TextButton(
                        onPressed: () => DefaultTabController.of(context).animateTo(1),
                        child: const Text('Xem ở Kanban'),
                      ),
                    ],
                  ),
                );
              }).toList(),
            );
          }),
        ],
      ),
    );
  }
}
```

**Lưu ý:** `DefaultTabController.of(context)` trong `TextButton.onPressed` cần `context` — dùng `Builder` để lấy đúng context nằm dưới `DefaultTabController` (đã được tạo ở `TasksView` Task 1). Bọc `Row` trong `Builder(builder: (context) => Row(...))` nếu compiler báo lỗi thiếu `context` hợp lệ tại vị trí này.

- [ ] **Step 7: Chạy `dart analyze`, xác nhận sạch**

Run: `cd frontend && dart analyze lib/modules/tasks/`
Expected: No issues found. Nếu có lỗi liên quan `DefaultTabController.of(context)`, áp dụng ghi chú ở Step 6.

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/tasks/controllers/work_overview_controller.dart \
  frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart \
  frontend/lib/modules/tasks/bindings/tasks_binding.dart \
  frontend/test/modules/tasks/controllers/work_overview_controller_test.dart
git commit -m "feat(tasks): WorkOverviewController + khoi Viec hom nay va Thong ke theo trang thai

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Chọn project + khối "Thông tin quản trị project"

**Files:**
- Modify: `frontend/lib/modules/tasks/controllers/work_overview_controller.dart`
- Modify: `frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart`
- Test: `frontend/test/modules/tasks/controllers/work_overview_controller_test.dart`

**Interfaces:**
- Consumes: `FounderCommandCenterController.projectsList` (`RxList<dynamic>`, mỗi phần tử `Map<String, dynamic>` có ít nhất `'id'`, `'title'` — xem `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart:99`), `ProjectOperatingSetupService.get(String projectId)` → `ProjectOperatingSetup` (`frontend/lib/modules/strategy/services/project_operating_setup_service.dart`, đã tồn tại từ trước).
- Produces: `WorkOverviewController.selectedProjectId` (`RxnString`), `WorkOverviewController.projectSetup` (`Rxn<ProjectOperatingSetup>`), `WorkOverviewController.isProjectInfoLoading` (`RxBool`), `WorkOverviewController.projectInfoError` (`RxnString`), `Future<void> selectProject(String projectId)`.

- [ ] **Step 1: Viết test trước — chọn project gọi đúng service, cập nhật state**

```dart
// thêm vào frontend/test/modules/tasks/controllers/work_overview_controller_test.dart
import 'package:frontend/core/contracts/enums.generated.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';

class FakeProjectOperatingSetupService extends ProjectOperatingSetupService {
  FakeProjectOperatingSetupService(this._setup);
  final ProjectOperatingSetup _setup;

  @override
  Future<ProjectOperatingSetup> get(String projectId) async => _setup;
}

// thêm vào main(), cùng cấp với 2 test đã có:
test('selectProject loads operating setup for the chosen project', () async {
  final tasksController = TasksController();
  final fakeSetup = const ProjectOperatingSetup(
    projectId: 'p-1',
    workspaceId: 'w-1',
    status: OperatingSetupStatus.active,
    selectedStage: ProjectLifecycleStage.p0Discovery,
  );
  final controller = WorkOverviewController(
    tasksController: tasksController,
    projectOperatingSetupService: FakeProjectOperatingSetupService(fakeSetup),
  );

  await controller.selectProject('p-1');

  expect(controller.selectedProjectId.value, 'p-1');
  expect(controller.projectSetup.value?.status, OperatingSetupStatus.active);
  expect(controller.isProjectInfoLoading.value, isFalse);
  expect(controller.projectInfoError.value, isNull);
});
```

Đã xác nhận trực tiếp trong `frontend/lib/data/models/project_operating_setup_model.dart:108-138`:
`ProjectOperatingSetup` có `status: OperatingSetupStatus` (bắt buộc, không
nullable) và `selectedStage: ProjectLifecycleStage?` — code test trên khớp
đúng, không cần sửa.

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/tasks/controllers/work_overview_controller_test.dart`
Expected: FAIL — `selectProject` và tham số `projectOperatingSetupService` chưa tồn tại.

- [ ] **Step 3: Mở rộng `WorkOverviewController`**

Sửa `frontend/lib/modules/tasks/controllers/work_overview_controller.dart`,
thêm import và mở rộng constructor + state:

```dart
import '../../strategy/services/project_operating_setup_service.dart';
import '../../../data/models/project_operating_setup_model.dart';

class WorkOverviewController extends GetxController {
  WorkOverviewController({
    required this.tasksController,
    ProjectOperatingSetupService? projectOperatingSetupService,
  }) : _projectOperatingSetupService =
            projectOperatingSetupService ?? ProjectOperatingSetupService();

  final TasksController tasksController;
  final ProjectOperatingSetupService _projectOperatingSetupService;

  final selectedProjectId = RxnString();
  final projectSetup = Rxn<ProjectOperatingSetup>();
  final isProjectInfoLoading = false.obs;
  final projectInfoError = RxnString();

  Future<void> selectProject(String projectId) async {
    selectedProjectId.value = projectId;
    isProjectInfoLoading.value = true;
    projectInfoError.value = null;
    try {
      projectSetup.value = await _projectOperatingSetupService.get(projectId);
    } catch (e) {
      projectInfoError.value = e.toString();
    } finally {
      isProjectInfoLoading.value = false;
    }
  }

  // ... todayTasks/statusCounts giữ nguyên từ Task 2
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/tasks/controllers/work_overview_controller_test.dart`
Expected: PASS (cả 3 test).

- [ ] **Step 5: Thêm dropdown chọn project + hiển thị thông tin quản trị vào `WorkOverviewTab`**

Thêm import `founder_command_center_controller.dart` và khối UI mới vào
`work_overview_tab.dart`, chèn giữa `_buildStatusCounts()` và
`_buildTodayTasks()` trong `build()`:

```dart
import 'package:get/get.dart';
import '../../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../../../../core/contracts/enums.generated.dart';

// trong build():
_buildProjectAdminInfo(),
const SizedBox(height: 20),

// method mới:
Widget _buildProjectAdminInfo() {
  final fcc = Get.find<FounderCommandCenterController>();
  return Obx(() {
    final projects = fcc.projectsList;
    if (projects.isEmpty) return const SizedBox.shrink();

    final selectedId = controller.selectedProjectId.value ?? projects.first['id']?.toString();
    if (controller.selectedProjectId.value == null && selectedId != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => controller.selectProject(selectedId));
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Thông tin quản trị project',
                style: TextStyle(color: AppTheme.textDark, fontSize: 15, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              DropdownButton<String>(
                value: selectedId,
                dropdownColor: AppTheme.surfaceDark,
                items: projects.map((p) {
                  final id = p['id']?.toString() ?? '';
                  final title = p['title']?.toString() ?? id;
                  return DropdownMenuItem(value: id, child: Text(title, style: const TextStyle(color: AppTheme.textDark)));
                }).toList(),
                onChanged: (id) {
                  if (id != null) controller.selectProject(id);
                },
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (controller.isProjectInfoLoading.value)
            const Center(child: CircularProgressIndicator())
          else if (controller.projectInfoError.value != null)
            Text(
              'Không tải được thông tin project: ${controller.projectInfoError.value}',
              style: const TextStyle(color: AppTheme.error, fontSize: 13),
            )
          else if (controller.projectSetup.value != null) ...[
            _infoRow('Giai đoạn', controller.projectSetup.value!.selectedStage?.name ?? 'Chưa chọn'),
            _infoRow('Trạng thái setup', controller.projectSetup.value!.status.name),
          ],
        ],
      ),
    );
  });
}

Widget _infoRow(String label, String value) => Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(color: AppTheme.textDark, fontSize: 13)),
          ),
        ],
      ),
    );
```

Kiểm tra tên field thật của `ProjectOperatingSetup` (`selectedStage` là enum
hay string?) trong `frontend/lib/data/models/project_operating_setup_model.dart`
trước khi viết — sửa `.name` thành cách hiển thị đúng kiểu dữ liệu thật nếu
khác giả định ở trên.

- [ ] **Step 6: `dart analyze` sạch, chạy lại toàn bộ test module tasks**

Run: `cd frontend && dart analyze lib/modules/tasks/ && flutter test test/modules/tasks/`
Expected: No issues found; tất cả test PASS.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/tasks/controllers/work_overview_controller.dart \
  frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart \
  frontend/test/modules/tasks/controllers/work_overview_controller_test.dart
git commit -m "feat(tasks): chon project + khoi Thong tin quan tri project trong tab Tong quan

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Khối "OKR + 12WY rút gọn"

**Files:**
- Modify: `frontend/lib/modules/tasks/controllers/work_overview_controller.dart`
- Modify: `frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart`
- Test: `frontend/test/modules/tasks/controllers/work_overview_controller_test.dart`

**Interfaces:**
- Consumes: `OkrService().getKeyResults()` → `StrategyListResult<Map<String, dynamic>>` với mỗi item có `'current_value'`/`'target_value'` (`double`, xem `frontend/lib/modules/strategy/services/okr_service.dart:92-104,123-124`); `TwelveWyService().getDashboard(dynamic projectId)` → `TwelveWyDashboardModel?` với field `currentWeekExecutionScore` (`double`, xem `frontend/lib/data/models/twelve_wy_model.dart:173`).
- Produces: `WorkOverviewController.okrCompletionRatio` (`RxnDouble`, 0.0-1.0), `WorkOverviewController.twelveWyExecutionScore` (`RxnDouble`), `Future<void> loadOkrAndTwelveWySummary()`.

- [ ] **Step 1: Viết test trước**

```dart
// thêm vào frontend/test/modules/tasks/controllers/work_overview_controller_test.dart
import 'package:frontend/modules/strategy/models/strategy_list_result.dart';
import 'package:frontend/modules/strategy/services/okr_service.dart';
import 'package:frontend/modules/strategy/services/twelve_wy_service.dart';
import 'package:frontend/data/models/twelve_wy_model.dart';

class FakeOkrService extends OkrService {
  @override
  Future<StrategyListResult<Map<String, dynamic>>> getKeyResults({String? objectiveId}) async {
    return StrategyListResult.success([
      {'current_value': 50.0, 'target_value': 100.0},
      {'current_value': 100.0, 'target_value': 100.0},
    ]);
  }
}

class FakeTwelveWyService extends TwelveWyService {
  @override
  Future<TwelveWyDashboardModel?> getDashboard(dynamic projectId) async {
    return TwelveWyDashboardModel(
      cycle: TwelveWeekCycleModel(
        id: 1,
        workspaceId: 1,
        title: 'Cycle 1',
        visionStatement: '',
        stageAtStart: 'P0_DISCOVERY',
        currentWeek: 2,
        totalWeeks: 12,
        overallExecutionScore: 0.75,
        status: 'ACTIVE',
        createdAt: DateTime.now(),
      ),
      currentWeek: 2,
      currentWeekExecutionScore: 0.75,
      tacticsByWeek: const {},
      weeklyScores: const {},
    );
  }
}

// test mới:
test('loadOkrAndTwelveWySummary computes average KR completion and reads execution score', () async {
  final controller = WorkOverviewController(
    tasksController: TasksController(),
    okrService: FakeOkrService(),
    twelveWyService: FakeTwelveWyService(),
  );

  await controller.loadOkrAndTwelveWySummary();

  expect(controller.okrCompletionRatio.value, 0.75); // avg(50/100, 100/100)
  expect(controller.twelveWyExecutionScore.value, 0.75);
});
```

Đã xác nhận trực tiếp trong `frontend/lib/data/models/twelve_wy_model.dart:73-99`:
constructor `TwelveWeekCycleModel` có đúng các tham số named ở trên
(`id`, `workspaceId`, `title`, `visionStatement`, `stageAtStart`,
`currentWeek`, `totalWeeks`, `status`, `overallExecutionScore` bắt buộc;
`projectId`/`startDate`/`endDate` tuỳ chọn) — code test trên khớp đúng.

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/tasks/controllers/work_overview_controller_test.dart`
Expected: FAIL — `okrCompletionRatio`, `twelveWyExecutionScore`, `loadOkrAndTwelveWySummary`, và tham số `okrService`/`twelveWyService` chưa tồn tại.

- [ ] **Step 3: Mở rộng `WorkOverviewController`**

```dart
import '../../strategy/services/okr_service.dart';
import '../../strategy/services/twelve_wy_service.dart';

class WorkOverviewController extends GetxController {
  WorkOverviewController({
    required this.tasksController,
    ProjectOperatingSetupService? projectOperatingSetupService,
    OkrService? okrService,
    TwelveWyService? twelveWyService,
  })  : _projectOperatingSetupService =
            projectOperatingSetupService ?? ProjectOperatingSetupService(),
        _okrService = okrService ?? OkrService(),
        _twelveWyService = twelveWyService ?? TwelveWyService();

  final OkrService _okrService;
  final TwelveWyService _twelveWyService;

  final okrCompletionRatio = RxnDouble();
  final twelveWyExecutionScore = RxnDouble();

  Future<void> loadOkrAndTwelveWySummary() async {
    final krResult = await _okrService.getKeyResults();
    if (!krResult.isFailure && krResult.items.isNotEmpty) {
      final ratios = krResult.items.map((kr) {
        final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
        final target = (kr['target_value'] as num?)?.toDouble() ?? 0.0;
        if (target <= 0) return 0.0;
        return (current / target).clamp(0.0, 1.0);
      });
      okrCompletionRatio.value = ratios.reduce((a, b) => a + b) / ratios.length;
    }

    final dashboard = await _twelveWyService.getDashboard(selectedProjectId.value);
    twelveWyExecutionScore.value = dashboard?.currentWeekExecutionScore;
  }

  // ... phần còn lại giữ nguyên từ Task 2-3
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/tasks/controllers/work_overview_controller_test.dart`
Expected: PASS (cả 4 test).

- [ ] **Step 5: Thêm khối UI vào `WorkOverviewTab`, gọi `loadOkrAndTwelveWySummary` khi tab mount**

Thêm vào `work_overview_tab.dart`: gọi `controller.loadOkrAndTwelveWySummary()`
1 lần khi widget build lần đầu (dùng `WidgetsBinding.instance.addPostFrameCallback`
trong 1 `StatefulWidget` wrapper nhỏ, hoặc dùng `ever`/`once` trên
`selectedProjectId` để trigger lại khi đổi project — chọn cách nào đơn giản
hơn khi viết code, miễn có test xác nhận nó thực sự được gọi), và khối hiển
thị:

```dart
Widget _buildOkrTwelveWySummary() {
  return Obx(() {
    final okr = controller.okrCompletionRatio.value;
    final wy = controller.twelveWyExecutionScore.value;
    return Row(
      children: [
        Expanded(
          child: InkWell(
            onTap: () => Get.toNamed('/work/strategy'),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('OKR chu kỳ hiện tại', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  const SizedBox(height: 6),
                  Text(
                    okr != null ? '${(okr * 100).round()}%' : '—',
                    style: const TextStyle(color: AppTheme.primary, fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: InkWell(
            onTap: () => Get.toNamed('/work/strategy'),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Điểm thực thi tuần (12WY)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  const SizedBox(height: 6),
                  Text(
                    wy != null ? '${(wy * 100).round()}%' : '—',
                    style: const TextStyle(color: AppTheme.primary, fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  });
}
```

Dùng `WorkspaceModule.strategy.path` thay vì literal string — đã xác nhận
extension `WorkspaceModuleRoute.path` (`frontend/lib/core/routing/module_routes.dart:60-66`)
trả về `/work/strategy` cho `WorkspaceModule.strategy`. Thêm import
`import '../../../../core/routing/module_routes.dart';` vào
`work_overview_tab.dart` và đổi cả 2 `onTap` thành
`Get.toNamed(WorkspaceModule.strategy.path)`.

- [ ] **Step 6: `dart analyze` sạch, chạy lại toàn bộ test module tasks**

Run: `cd frontend && dart analyze lib/modules/tasks/ && flutter test test/modules/tasks/`
Expected: No issues found; tất cả test PASS.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/tasks/controllers/work_overview_controller.dart \
  frontend/lib/modules/tasks/views/tabs/work_overview_tab.dart \
  frontend/test/modules/tasks/controllers/work_overview_controller_test.dart
git commit -m "feat(tasks): khoi OKR + 12WY rut gon trong tab Tong quan

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
