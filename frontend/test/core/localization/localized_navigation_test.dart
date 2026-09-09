import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/localization/locale_cache.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/core/services/feature_flags_controller.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/dashboard/views/widgets/dashboard_sidebar.dart';

class FakeLocaleCache implements LocaleCache {
  SupportedLocale? _val;
  FakeLocaleCache([this._val]);

  @override
  Future<SupportedLocale?> read() async => _val;

  @override
  Future<void> write(SupportedLocale locale) async {
    _val = locale;
  }
}

Widget buildLocalizedSidebar(SupportedLocale initial) {
  Get.reset();
  final lc = Get.put(
    LocaleController(
      cache: FakeLocaleCache(initial),
    ),
    permanent: true,
  );
  lc.current.value = initial;

  Get.put(FeatureFlagsController(), permanent: true);
  final dashboardController = Get.put(DashboardController(), permanent: true);
  // Founder Trial R1: Finance group is index 3 (Conversation, Cycle, AI, Finance).
  dashboardController.expandedGroupIndex.value = 3;

  return GetMaterialApp(
    translations: AppTranslations(),
    locale: initial.flutterLocale,
    fallbackLocale: const Locale('vi', 'VN'),
    home: Scaffold(
      body: DashboardDesktopSidebar(controller: dashboardController),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('sidebar re-renders a nav label after changing to en-US', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(buildLocalizedSidebar(SupportedLocale.viVN));
    await tester.pumpAndSettle();

    expect(find.text('Tài chính'), findsWidgets);

    await Get.find<LocaleController>().applyServerLocale(SupportedLocale.enUS);
    await tester.pumpAndSettle();

    expect(find.text('Finance'), findsWidgets);
  });
}
