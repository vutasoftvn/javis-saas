import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/lenses/tows_matrix_widget.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    Get.put<LocaleController>(LocaleController());
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('TowsMatrixWidget switches between Vietnamese and English translations', (tester) async {
    tester.view.physicalSize = const Size(1200, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      GetMaterialApp(
        translations: AppTranslations(),
        locale: const Locale('vi', 'VN'),
        fallbackLocale: const Locale('vi', 'VN'),
        home: Scaffold(
          body: TowsMatrixWidget(
            towsOptions: const [],
            selectionLimit: 2,
            onCreateOption: (_, _, _) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // VI translations
    expect(find.text('Ma trận TOWS: Ghép nối yếu tố bên trong và bên ngoài để ra quyết định chiến lược.'), findsOneWidget);
    expect(find.text('0 / 2 chiến lược đã chọn'), findsOneWidget);
    expect(find.text('Chiến Lược SO (Tận Dụng Đột Phá)'), findsOneWidget);
    expect(find.text('Chưa có chiến lược'), findsNWidgets(4));

    // Switch to English
    Get.updateLocale(const Locale('en', 'US'));
    await tester.pumpAndSettle();

    // EN translations
    expect(find.text('TOWS Matrix: Pair internal & external factors to drive strategic decisions.'), findsOneWidget);
    expect(find.text('0 / 2 strategies selected'), findsOneWidget);
    expect(find.text('SO Strategy (Maxi-Maxi: Strengths-Opportunities)'), findsOneWidget);
    expect(find.text('No strategies yet'), findsNWidgets(4));
  });
}
