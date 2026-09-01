import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/services/feature_flags_controller.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/dashboard_sidebar.dart';
import 'package:frontend/modules/dashboard/views/widgets/dashboard_stage_demo_bar.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    Get.put<FeatureFlagsController>(FeatureFlagsController());
  });

  tearDown(() {
    Get.reset();
  });

  test('DashboardController defaults to demo mode and stage filtering disabled', () {
    final controller = DashboardController();
    expect(controller.isDemoModeActive.value, isFalse);
    expect(controller.isStageFilteringEnabled.value, isFalse);
  });

  testWidgets('DashboardDesktopSidebar hides DashboardStageDemoBar when demo mode is false', (tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final controller = DashboardController();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DashboardDesktopSidebar(controller: controller),
        ),
      ),
    );
    await tester.pump();

    // Verify demo stage bar is not rendered
    expect(find.byType(DashboardStageDemoBar), findsNothing);
    expect(find.textContaining('Demo Stage'), findsNothing);
    expect(find.text('Đổi Stage'), findsNothing);
    expect(find.textContaining('Lọc ưu tiên'), findsNothing);
    expect(find.text('Ưu tiên'), findsNothing);
    expect(find.text('Sau'), findsNothing);
  });

  testWidgets('DashboardDesktopSidebar shows DashboardStageDemoBar when demo mode is active', (tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final controller = DashboardController();
    controller.isDemoModeActive.value = true;
    controller.isStageFilteringEnabled.value = true;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DashboardDesktopSidebar(controller: controller),
        ),
      ),
    );
    await tester.pump();

    // Verify demo stage bar appears when explicitly enabled
    expect(find.byType(DashboardStageDemoBar), findsOneWidget);
    expect(find.textContaining('Demo Stage:'), findsOneWidget);
    expect(find.text('Đổi Stage'), findsOneWidget);
  });

  testWidgets('DashboardMobileDrawer hides DashboardStageDemoBar when demo mode is false', (tester) async {
    tester.view.physicalSize = const Size(600, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final controller = DashboardController();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          drawer: DashboardMobileDrawer(controller: controller),
          body: Container(),
        ),
      ),
    );

    final scaffoldState = tester.state<ScaffoldState>(find.byType(Scaffold));
    scaffoldState.openDrawer();
    await tester.pumpAndSettle();

    // Verify demo stage bar is not rendered in drawer
    expect(find.byType(DashboardStageDemoBar), findsNothing);
    expect(find.textContaining('Demo Stage'), findsNothing);
  });
}
