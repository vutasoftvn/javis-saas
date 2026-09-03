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
    // KHÔNG dùng `pumpAndSettle`: test này build `HologramHubView` trực tiếp,
    // không qua `AppShell`, nên `FloatingVoiceHologram` không nằm trong cây
    // widget — đã verify bằng `SchedulerBinding.instance.transientCallbackCount`
    // (== 1 sau khi pump ổn định) và `find.byType(CircularProgressIndicator)`.
    // Nguyên nhân thật: `ApiClient` không được mock ở test này (không giống
    // `hologram_hub_view_single_controller_test.dart`), nên request thật của
    // `FounderCommandCenterController.loadDashboardData()` (gọi tự động từ
    // `onInit()`) không bao giờ resolve trong khung thời gian test — `isLoading`
    // kẹt ở `true`, `HologramHubView.build()` render `CircularProgressIndicator`
    // (animation indeterminate vô hạn của chính Flutter) khiến `pumpAndSettle()`
    // timeout. Dùng `pump` hữu hạn thay thế, đủ cho animation mở bottom sheet
    // (~300ms mặc định của Material) thay vì chờ settle toàn bộ cây widget.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('OKRs'), findsOneWidget);
    expect(find.text('Dự án'), findsOneWidget);
  });
}
