// Fix-review (2026-09-04, final review, Fix 1) — regression test cho bug
// "tick checkbox không cập nhật UI". Root cause: `HologramHubView` đọc
// `controller.activeProjectSetup.value` bên trong `_buildCommandCenterTab`,
// hàm này chỉ thực sự chạy trong builder của `LayoutBuilder` — một build
// pass RIÊNG, tách khỏi builder của `Obx` bao ngoài nó. `Obx` chỉ track các
// Rx read xảy ra ĐỒNG BỘ trong chính builder của nó; đến lúc `LayoutBuilder`
// build xong thì GetX đã un-bind proxy tracking, nên đọc `activeProjectSetup`
// bên trong đó không được track bởi bất kỳ `Obx` nào. Sửa bằng cách bọc
// riêng một `Obx` ngay tại call-site của `Top3FocusWidget` (xem
// `hologram_hub_view.dart`).
//
// Test này chứng minh CẢ HAI vế:
//   1. Pattern ĐÃ SỬA (Obx bọc trực tiếp quanh Top3FocusWidget) rebuild đúng
//      khi Rxn.value đổi sau lần pump đầu.
//   2. Pattern LỖI CŨ (đọc Rxn.value trong LayoutBuilder lồng trong Obx bao
//      ngoài — đúng cấu trúc cũ của `HologramHubView`) KHÔNG rebuild — để
//      chứng minh test này thật sự phân biệt được đúng/sai, không phải một
//      assertion luôn xanh bất kể có Obx hay không.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/data/models/company_pulse_model.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/top3_focus_widget.dart';

ProjectOperatingSetup _setupWith(String actionTitle, TaskKanbanStatus status) {
  return ProjectOperatingSetup(
    projectId: 'proj-1',
    workspaceId: 'ws_123',
    status: OperatingSetupStatus.active,
    firstWeekActions: [
      FirstWeekActionDraft(id: 'a1', title: actionTitle, status: status),
    ],
  );
}

void main() {
  setUp(() {
    Get.testMode = true;
  });

  testWidgets(
    'FIXED pattern: Top3FocusWidget wrapped directly in its own Obx rebuilds when the bound Rxn value changes',
    (tester) async {
      final setup = Rxn<ProjectOperatingSetup>(_setupWith('Interview lead #1', TaskKanbanStatus.todo));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Obx(
              () => Top3FocusWidget(
                actions: const <NextBestActionModel>[],
                onActionTap: (_) {},
                firstWeekActions: setup.value?.firstWeekActions ?? const [],
              ),
            ),
          ),
        ),
      );

      expect(find.text('Interview lead #1'), findsOneWidget);
      var checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
      expect(checkbox.value, isFalse);

      // Mô phỏng đúng những gì `_refreshActiveProjectSetup()` làm: gán một
      // giá trị MỚI (instance khác) cho Rx sau khi request server hoàn tất.
      setup.value = _setupWith('Interview lead #1', TaskKanbanStatus.done);
      await tester.pump();

      checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
      expect(
        checkbox.value,
        isTrue,
        reason: 'Obx bọc trực tiếp quanh Top3FocusWidget phải rebuild và phản ánh status mới sau khi Rxn.value đổi.',
      );
    },
  );

  testWidgets(
    'BUGGY pattern (pre-fix): reading Rxn.value inside a LayoutBuilder nested in an outer Obx does NOT rebuild on change',
    (tester) async {
      final setup = Rxn<ProjectOperatingSetup>(_setupWith('Interview lead #1', TaskKanbanStatus.todo));
      // Trong `HologramHubView` thật, Obx bao ngoài (dòng ~66) đọc đồng bộ
      // `controller.isLoading.value` trước khi trả về `LayoutBuilder` — đó
      // là quan sát viên duy nhất mà Obx đó thấy được. Tái tạo đúng chi tiết
      // này (thay vì Obx hoàn toàn rỗng) vì GetX chủ động throw
      // "improper use of GetX" khi builder của Obx không đọc BẤT KỲ Rx nào
      // đồng bộ — không tái tạo được bug thật nếu thiếu chi tiết này.
      final isLoading = false.obs;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Obx(() {
              // Đúng cấu trúc lỗi cũ của `HologramHubView`: builder của Obx
              // bao ngoài chỉ đọc `isLoading` (không liên quan) rồi trả về
              // LayoutBuilder — không đọc `setup` (Rx liên quan) ở đây.
              if (isLoading.value) return const SizedBox.shrink();
              return LayoutBuilder(
                builder: (context, constraints) {
                  // Đọc Rx thật sự xảy ra ở ĐÂY — bên trong builder của
                  // LayoutBuilder, một build pass riêng — không được Obx bao
                  // ngoài track.
                  return Top3FocusWidget(
                    actions: const <NextBestActionModel>[],
                    onActionTap: (_) {},
                    firstWeekActions: setup.value?.firstWeekActions ?? const [],
                  );
                },
              );
            }),
          ),
        ),
      );

      var checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
      expect(checkbox.value, isFalse);

      setup.value = _setupWith('Interview lead #1', TaskKanbanStatus.done);
      await tester.pump();

      checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
      expect(
        checkbox.value,
        isFalse,
        reason:
            'Đây chính là bug đã báo cáo: đọc Rx bên trong LayoutBuilder lồng trong Obx bao ngoài không được '
            'track, nên checkbox KHÔNG cập nhật dù Rxn.value đã đổi. Assertion này chứng minh test phía trên '
            'thật sự phân biệt được pattern đúng/sai, không phải luôn xanh.',
      );
    },
  );
}
