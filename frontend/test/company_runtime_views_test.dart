import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/company_runtime/controllers/company_runtime_controller.dart';
import 'package:frontend/modules/company_runtime/views/needs_you_view.dart';
import 'package:frontend/modules/company_runtime/views/blocked_work_view.dart';
import 'package:frontend/modules/company_runtime/views/work_inspector_view.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/needs_you_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
  });

  testWidgets('NeedsYouView renders empty state cleanly', (WidgetTester tester) async {
    final controller = Get.put(CompanyRuntimeController());
    controller.needsYouItems.clear();
    controller.loading.value = false;

    await tester.pumpWidget(
      const GetMaterialApp(
        home: NeedsYouView(),
      ),
    );

    expect(find.text('Needs You — Founder Exception Queue'), findsOneWidget);
    expect(find.text('Tuyệt vời! Không có việc gì cần xử lý ngay bây giờ.'), findsOneWidget);
  });

  testWidgets('NeedsYouView renders items with action buttons', (WidgetTester tester) async {
    final controller = Get.put(CompanyRuntimeController());
    controller.needsYouItems.assignAll([
      {
        'id': '101',
        'source_type': 'BLOCKER',
        'priority': 'P0',
        'reason': 'Choose pricing model before enterprise contract',
        'requested_action': 'Select Tier A or Tier B',
      }
    ]);
    controller.loading.value = false;

    await tester.pumpWidget(
      const GetMaterialApp(
        home: NeedsYouView(),
      ),
    );

    expect(find.text('Choose pricing model before enterprise contract'), findsOneWidget);
    expect(find.text('P0'), findsOneWidget);
    expect(find.text('Đã xử lý'), findsOneWidget);
    expect(find.text('Hoãn 1 ngày'), findsOneWidget);
  });

  testWidgets('BlockedWorkView renders list of blockers', (WidgetTester tester) async {
    final controller = Get.put(CompanyRuntimeController());
    controller.blockers.assignAll([
      {
        'id': '201',
        'assigned_function': 'FINANCE',
        'blocker_type': 'FINANCE_EXCEPTION',
        'description': 'Transaction missing invoice documentation',
        'status': 'OPEN',
      }
    ]);
    controller.loading.value = false;

    await tester.pumpWidget(
      const GetMaterialApp(
        home: BlockedWorkView(),
      ),
    );

    expect(find.text('Blocked Work & Exceptions'), findsOneWidget);
    expect(find.text('FINANCE'), findsOneWidget);
    expect(find.text('Transaction missing invoice documentation'), findsOneWidget);
    expect(find.text('Giải tỏa Blocker'), findsOneWidget);
  });

  testWidgets('WorkInspectorView renders search and inspector sections', (WidgetTester tester) async {
    final controller = Get.put(CompanyRuntimeController());
    controller.currentInspectorData.value = {
      'task': {'id': '301', 'title': 'Deploy Landing Page', 'status': 'in_progress', 'priority': 'high'},
      'outcome': {'title': 'Landing Page Live', 'desired_result': 'Staging URL active', 'rework_count': 0},
      'dependencies': {'upstream': [], 'downstream': []},
      'reviews': [],
      'handoffs': [],
      'blockers': [],
      'artifacts': [],
    };
    controller.loading.value = false;

    await tester.pumpWidget(
      const GetMaterialApp(
        home: WorkInspectorView(),
      ),
    );

    expect(find.text('Work Inspector — 360° Traceability'), findsOneWidget);
    expect(find.text('Deploy Landing Page'), findsOneWidget);
    expect(find.text('1. Task Execution Unit'), findsOneWidget);
    expect(find.text('2. Work Contract & Acceptance Criteria'), findsOneWidget);
  });

  testWidgets('NeedsYouPanel renders on hub right rail', (WidgetTester tester) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: NeedsYouPanel(
            items: const [
              {'reason': 'Approve marketing launch', 'priority': 'P0'}
            ],
            onViewAll: () {},
          ),
        ),
      ),
    );

    expect(find.text('NEEDS YOU — EXCEPTIONS'), findsOneWidget);
    expect(find.text('Approve marketing launch'), findsOneWidget);
    expect(find.text('XEM TOÀN BỘ NEEDS YOU'), findsOneWidget);
  });
}
