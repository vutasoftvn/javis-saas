import 'dart:ui';

enum SupportedLocale {
  viVN,
  enUS,
}

extension SupportedLocaleWire on SupportedLocale {
  String get tag => switch (this) {
        SupportedLocale.viVN => 'vi-VN',
        SupportedLocale.enUS => 'en-US',
      };

  Locale get flutterLocale => switch (this) {
        SupportedLocale.viVN => const Locale('vi', 'VN'),
        SupportedLocale.enUS => const Locale('en', 'US'),
      };

  String get transcriptionLanguage => switch (this) {
        SupportedLocale.viVN => 'vi',
        SupportedLocale.enUS => 'en',
      };

  static SupportedLocale parse(String value) {
    final clean = value.trim().replaceAll('_', '-').toLowerCase();
    if (clean.startsWith('en')) {
      return SupportedLocale.enUS;
    }
    return SupportedLocale.viVN;
  }
}
