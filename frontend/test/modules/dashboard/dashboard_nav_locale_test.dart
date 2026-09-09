import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/services/feature_flags_controller.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/dashboard_sidebar.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    Get.put<FeatureFlagsController>(FeatureFlagsController());
    Get.put<LocaleController>(LocaleController());
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('DashboardDesktopSidebar renders Vietnamese titles in vi_VN and English in en_US', (tester) async {
    tester.view.physicalSize = const Size(1200, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final controller = DashboardController();

    await tester.pumpWidget(
      GetMaterialApp(
        translations: AppTranslations(),
        locale: const Locale('vi', 'VN'),
        fallbackLocale: const Locale('vi', 'VN'),
        home: Scaffold(
          body: DashboardDesktopSidebar(controller: controller),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // In Vietnamese
    expect(find.text('Hội thoại & Trung tâm'), findsOneWidget);
    expect(find.text('Chu kỳ & Chiến lược'), findsOneWidget);
    expect(find.text('Đội ngũ AI & Nghiệp vụ'), findsOneWidget);

    // Switch to English
    Get.updateLocale(const Locale('en', 'US'));
    await tester.pumpAndSettle();

    // In English
    expect(find.text('Conversation & Center'), findsOneWidget);
    expect(find.text('Cycle & Strategy'), findsOneWidget);
    expect(find.text('AI Team & Business'), findsOneWidget);
  });
}
