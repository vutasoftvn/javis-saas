import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/core/widgets/app_toast.dart';
import 'package:get/get.dart';

void main() {
  setUp(() {
    AppToast.allowInTest = true;
  });

  tearDown(() {
    AppToast.allowInTest = false;
    Get.reset();
  });

  testWidgets('AppToast handles headless invocation safely without crashing', (tester) async {
    AppToast.allowInTest = false;
    expect(() => AppToast.success('Test message'), returnsNormally);
    expect(() => AppToast.error('Error message'), returnsNormally);
    expect(() => AppToast.warning('Warning message'), returnsNormally);
    expect(() => AppToast.info('Info message'), returnsNormally);
  });

  testWidgets('AppToast renders in GetMaterialApp in Vietnamese mode', (tester) async {
    Get.locale = const Locale('vi', 'VN');
    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('vi', 'VN'),
        home: Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () {
                AppToast.success(
                  'Thao tác thành công',
                  title: 'Chúc mừng',
                );
              },
              child: const Text('Show Toast'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Show Toast'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Thao tác thành công'), findsOneWidget);
    expect(find.text('Chúc mừng'), findsOneWidget);

    await tester.pumpAndSettle(const Duration(seconds: 5));
  });

  testWidgets('AppToast automatically translates known strings and titles in English mode', (tester) async {
    Get.locale = const Locale('en', 'US');
    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('en', 'US'),
        home: Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () {
                AppToast.error(
                  'Thao tác thành công',
                  title: 'Chưa khả dụng',
                );
              },
              child: const Text('Show Toast'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Show Toast'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 'Thao tác thành công' should be translated to 'Operation successful'
    // 'Chưa khả dụng' should be translated to 'Feature Unavailable'
    expect(find.text('Operation successful'), findsOneWidget);
    expect(find.text('Feature Unavailable'), findsOneWidget);

    await tester.pumpAndSettle(const Duration(seconds: 5));
  });

  testWidgets('AppToast translates dynamic pattern strings in English mode', (tester) async {
    final lc = Get.put(LocaleController());
    lc.current.value = SupportedLocale.enUS;
    Get.locale = const Locale('en', 'US');

    await tester.pumpWidget(
      GetMaterialApp(
        locale: const Locale('en', 'US'),
        home: Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () {
                AppToast.success(
                  'Đã lưu nhiệm vụ từ COSA Bot vào danh sách tuần!',
                );
              },
              child: const Text('Show Toast'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Show Toast'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Saved task from COSA Bot to weekly backlog!'), findsOneWidget);
    expect(find.text('Success'), findsOneWidget);

    await tester.pumpAndSettle(const Duration(seconds: 5));
  });
}
