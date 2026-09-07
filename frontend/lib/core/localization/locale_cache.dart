import 'package:shared_preferences/shared_preferences.dart';
import 'supported_locale.dart';

abstract interface class LocaleCache {
  Future<SupportedLocale?> read();
  Future<void> write(SupportedLocale locale);
}

class SharedPreferencesLocaleCache implements LocaleCache {
  static const String key = 'preferred_locale';
  final SharedPreferences? _prefs;

  SharedPreferencesLocaleCache([this._prefs]);

  @override
  Future<SupportedLocale?> read() async {
    final prefs = _prefs ?? await SharedPreferences.getInstance();
    final val = prefs.getString(key);
    if (val == null || val.isEmpty) return null;
    return SupportedLocaleWire.parse(val);
  }

  @override
  Future<void> write(SupportedLocale locale) async {
    final prefs = _prefs ?? await SharedPreferences.getInstance();
    await prefs.setString(key, locale.tag);
  }
}
