import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/localized_formatters.dart';
import 'package:frontend/core/localization/supported_locale.dart';

void main() {
  setUpAll(() async {
    await initializeLocaleFormatting();
  });

  group('LocalizedFormatters', () {
    test('formats numbers differently for vi-VN and en-US', () {
      final viFormatter = const LocalizedFormatters(locale: SupportedLocale.viVN);
      final enFormatter = const LocalizedFormatters(locale: SupportedLocale.enUS);

      final viNumber = viFormatter.formatNumber(1234567.89, decimalDigits: 2);
      final enNumber = enFormatter.formatNumber(1234567.89, decimalDigits: 2);

      // vi-VN uses comma for decimal and period for grouping
      expect(viNumber, contains('1.234.567,89'));
      // en-US uses period for decimal and comma for grouping
      expect(enNumber, contains('1,234,567.89'));
    });

    test('formats VND currency for vi-VN and en-US', () {
      final viFormatter = const LocalizedFormatters(locale: SupportedLocale.viVN);
      final enFormatter = const LocalizedFormatters(locale: SupportedLocale.enUS);

      final viVnd = viFormatter.formatCurrency(5000000);
      final enVnd = enFormatter.formatCurrency(5000000);

      expect(viVnd, contains('5.000.000'));
      expect(viVnd, contains('₫'));
      expect(enVnd, contains('5,000,000'));
      expect(enVnd, contains('₫'));
    });

    test('formats date consistently per locale', () {
      final viFormatter = const LocalizedFormatters(locale: SupportedLocale.viVN);
      final enFormatter = const LocalizedFormatters(locale: SupportedLocale.enUS);

      final date = DateTime(2026, 9, 7);
      final viDate = viFormatter.formatDate(date);
      final enDate = enFormatter.formatDate(date);

      expect(viDate, isNotEmpty);
      expect(enDate, isNotEmpty);
      // en-US is M/d/y
      expect(enDate, contains('9/7/2026'));
      // vi-VN is d/M/y
      expect(viDate, contains('7/9/2026'));
    });
  });
}
