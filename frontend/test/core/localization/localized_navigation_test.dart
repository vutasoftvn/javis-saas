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
  // Expand group containing Finance (group index 4: 'Tài chính & Tri thức')
  dashboardController.expandedGroupIndex.value = 4;

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

  testWidgets('sidebar re-renders finance label after changing to en-US', (tester) async {
    await tester.pumpWidget(buildLocalizedSidebar(SupportedLocale.viVN));
    await tester.pumpAndSettle();

    expect(find.text('Tài chính'), findsOneWidget);

    await Get.find<LocaleController>().applyServerLocale(SupportedLocale.enUS);
    await tester.pumpAndSettle();

    expect(find.text('Finance'), findsOneWidget);
  });
}
