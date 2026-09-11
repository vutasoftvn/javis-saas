import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/executive_advisory_board_controller.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/views/executive_advisory_board_view.dart';

ExecutiveAdvisorRole _mockRole({
  required String roleKey,
  required String title,
  required ExecutiveActivationState state,
  String? disabledReason,
}) {
  return ExecutiveAdvisorRole(
    roleKey: roleKey,
    title: title,
    domain: 'advisory',
    advisoryLevel: 'L1',
    description: 'Advisory role description',
    capabilities: const ['read_data'],
    activationState: state,
    underlyingProfileKey: 'profile',
    assignmentStatus: state == ExecutiveActivationState.active ? 'ACTIVE' : 'UNASSIGNED',
    specHash: 'hash',
    disabledReason: disabledReason,
  );
}

Future<void> _pumpBoard(
  WidgetTester tester, {
  required ExecutiveAdvisoryBoardController controller,
}) async {
  await tester.pumpWidget(
    GetMaterialApp(
      home: Scaffold(
        body: ExecutiveAdvisoryBoardView(
          projectId: 'proj-101',
          controller: controller,
        ),
      ),
    ),
  );
}

void main() {
  tearDown(() {
    Get.reset();
  });

  testWidgets('unavailable role is rendered as "Chưa sẵn sàng" and does not show activate button', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.roles.assignAll([
      _mockRole(
        roleKey: 'ciso',
        title: 'CISO Advisor',
        state: ExecutiveActivationState.unavailable,
        disabledReason: 'Chưa có cấu hình an ninh',
      ),
    ]);

    await _pumpBoard(tester, controller: controller);

    expect(find.text('Chưa sẵn sàng'), findsOneWidget);
    expect(find.text('Kích hoạt'), findsNothing);
    expect(find.text('Chưa có cấu hình an ninh'), findsOneWidget);
  });

  testWidgets('available not activated role renders "Chưa kích hoạt" badge and "Kích hoạt" button', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.roles.assignAll([
      _mockRole(
        roleKey: 'cfo',
        title: 'CFO Advisor',
        state: ExecutiveActivationState.availableNotActivated,
      ),
    ]);

    await _pumpBoard(tester, controller: controller);

    expect(find.text('Chưa kích hoạt'), findsOneWidget);
    expect(find.text('Kích hoạt'), findsOneWidget);
  });

  testWidgets('active role renders "Đang hoạt động" badge and "Tạm dừng" button', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.roles.assignAll([
      _mockRole(
        roleKey: 'cmo',
        title: 'CMO Advisor',
        state: ExecutiveActivationState.active,
      ),
    ]);

    await _pumpBoard(tester, controller: controller);

    expect(find.text('Đang hoạt động'), findsOneWidget);
    expect(find.text('Tạm dừng'), findsOneWidget);
  });

  testWidgets('renders active deliberation card when present', (tester) async {
    final controller = ExecutiveAdvisoryBoardController();
    controller.currentDeliberation.value = ExecutiveDeliberation(
      id: 'delib-1',
      workspaceId: 'ws-1',
      projectId: 'proj-101',
      title: 'Kế hoạch ngân sách 2026',
      state: 'AWAITING_FOUNDER',
      activeFrameVersion: 1,
      version: 2,
      createdBy: 'user-1',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
      activeFrame: {
        'question': 'Có nên tăng chi phí tuyển dụng 20%?',
      },
      analyses: [
        DeliberationAnalysis(
          id: 'analysis-1',
          frameVersion: 1,
          roleKey: 'cfo',
          runId: 'run-1',
          status: 'COMPLETED',
          descriptor: {
            'conclusion': 'Khả thi về dòng tiền',
            'confidence': 'HIGH',
          },
          createdAt: DateTime.now(),
        ),
      ],
    );

    await _pumpBoard(tester, controller: controller);

    expect(find.text('Kế hoạch ngân sách 2026'), findsOneWidget);
    expect(find.text('Có nên tăng chi phí tuyển dụng 20%?'), findsOneWidget);
    expect(find.text('Khả thi về dòng tiền'), findsOneWidget);
    expect(find.text('Phê duyệt (Approve)'), findsOneWidget);
  });
}
