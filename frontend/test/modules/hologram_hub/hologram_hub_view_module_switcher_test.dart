import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    AppShellController.ensureShellDependencies();
  });

  testWidgets('tapping the menu icon opens a module list with OKRs entry', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    await tester.tap(find.byTooltip('Chuyển module'));
    // `FloatingVoiceHologram` (Task 5, sống trong AppShell chrome) chạy
    // animation vô hạn nên `pumpAndSettle()` không bao giờ settle trong toàn
    // bộ test suite này (xem cùng pattern ở `test/core/shell/app_shell_test.dart`)
    // — dùng `pump` tường minh đủ cho animation mở bottom sheet (~300ms mặc
    // định của Material) thay vì chờ settle toàn bộ cây widget.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('OKRs'), findsOneWidget);
    expect(find.text('Dự án'), findsOneWidget);
  });
}
