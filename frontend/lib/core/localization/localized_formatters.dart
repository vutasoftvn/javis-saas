import 'package:intl/intl.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'supported_locale.dart';

Future<void> initializeLocaleFormatting() async {
  await initializeDateFormatting('vi_VN', null);
  await initializeDateFormatting('en_US', null);
}

class LocalizedFormatters {
  final SupportedLocale locale;

  const LocalizedFormatters({this.locale = SupportedLocale.viVN});

  String formatCurrency(num amount, {String currencyCode = 'VND'}) {
    if (currencyCode == 'VND') {
      // In vi-VN, 1000000 -> 1.000.000 ₫
      // In en-US, 1000000 -> ₫1,000,000
      final formatter = NumberFormat.currency(
        locale: locale.tag,
        symbol: '₫',
        decimalDigits: 0,
      );
      return formatter.format(amount).trim();
    }
    final formatter = NumberFormat.currency(
      locale: locale.tag,
      name: currencyCode,
    );
    return formatter.format(amount).trim();
  }

  String formatNumber(num number, {int? decimalDigits}) {
    final formatter = NumberFormat.decimalPatternDigits(
      locale: locale.tag,
      decimalDigits: decimalDigits,
    );
    return formatter.format(number);
  }

  String formatDate(DateTime date) {
    final formatter = DateFormat.yMd(locale.tag);
    return formatter.format(date);
  }

  String formatDateTime(DateTime dateTime) {
    final formatter = DateFormat.yMd(locale.tag).add_jm();
    return formatter.format(dateTime);
  }
}
