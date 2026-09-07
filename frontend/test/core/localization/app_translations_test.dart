import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/app_translations.dart';

void main() {
  group('AppTranslations', () {
    test('every required key has non-empty VI and EN values', () {
      for (final key in L10nKey.required) {
        expect(
          AppTranslations.vi[key],
          isNotEmpty,
          reason: 'Missing or empty VI translation for key: $key',
        );
        expect(
          AppTranslations.en[key],
          isNotEmpty,
          reason: 'Missing or empty EN translation for key: $key',
        );
      }
    });

    test('keys getter returns both vi_VN and en_US maps', () {
      final translations = AppTranslations();
      final keys = translations.keys;
      expect(keys.containsKey('vi_VN'), isTrue);
      expect(keys.containsKey('en_US'), isTrue);
      expect(keys['vi_VN']![L10nKey.moduleFinance], 'Tài chính');
      expect(keys['en_US']![L10nKey.moduleFinance], 'Finance');
    });
  });
}
