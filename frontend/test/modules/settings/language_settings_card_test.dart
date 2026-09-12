import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/localization/locale_cache.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/modules/settings/views/widgets/language_settings_card.dart';
import 'package:get/get.dart';

class FakeLocaleCache implements LocaleCache {
  SupportedLocale? _val;
  FakeLocaleCache([String? initial])
      : _val = initial != null ? SupportedLocaleWire.parse(initial) : null;

  @override
  Future<SupportedLocale?> read() async => _val;

  @override
  Future<void> write(SupportedLocale locale) async {
    _val = locale;
  }
}

class FakeProfileApi implements ProfileLocaleApi {
  SupportedLocale? updated;

  @override
  Future<bool> updatePreferredLocale(SupportedLocale locale) async {
    updated = locale;
    return true;
  }
}

Widget buildTestWidget({String initial = 'vi-VN'}) {
  Get.reset();
  final cache = FakeLocaleCache(initial);
  final lc = Get.put(
    LocaleController(
      cache: cache,
      profileApi: FakeProfileApi(),
    ),
    permanent: true,
  );
  lc.current.value = SupportedLocaleWire.parse(initial);
  Get.locale = lc.current.value.flutterLocale;

  return GetMaterialApp(
    translations: AppTranslations(),
    locale: lc.current.value.flutterLocale,
    fallbackLocale: const Locale('vi', 'VN'),
    home: const Scaffold(
      body: SingleChildScrollView(
        child: LanguageSettingsCard(),
      ),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    Get.reset();
  });

  group('LanguageSettingsCard', () {
    testWidgets('renders language options in Vietnamese mode', (tester) async {
      await tester.pumpWidget(buildTestWidget(initial: 'vi-VN'));
      await tester.pumpAndSettle();

      expect(find.text('Ngôn ngữ giao diện'), findsOneWidget);
      expect(find.text('Tiếng Việt'), findsOneWidget);
      expect(find.text('English'), findsOneWidget);
    });

    testWidgets('tapping English changes locale to en-US and updates card title', (tester) async {
      await tester.pumpWidget(buildTestWidget(initial: 'vi-VN'));
      await tester.pumpAndSettle();

      expect(find.text('Ngôn ngữ giao diện'), findsOneWidget);

      await tester.tap(find.byKey(const Key('settings_lang_en')));
      await tester.pumpAndSettle();

      final lc = Get.find<LocaleController>();
      expect(lc.current.value, SupportedLocale.enUS);
      expect(find.text('Interface Language'), findsOneWidget);
    });

    testWidgets('tapping Tiếng Việt switches back to Vietnamese', (tester) async {
      await tester.pumpWidget(buildTestWidget(initial: 'en-US'));
      await tester.pumpAndSettle();

      expect(find.text('Interface Language'), findsOneWidget);

      await tester.tap(find.byKey(const Key('settings_lang_vi')));
      await tester.pumpAndSettle();

      final lc = Get.find<LocaleController>();
      expect(lc.current.value, SupportedLocale.viVN);
      expect(find.text('Ngôn ngữ giao diện'), findsOneWidget);
    });
  });
}
