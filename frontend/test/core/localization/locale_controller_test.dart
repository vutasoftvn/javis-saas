import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/locale_cache.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';

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

class FailingProfileApi implements ProfileLocaleApi {
  @override
  Future<bool> updatePreferredLocale(SupportedLocale locale) async {
    return false;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('LocaleController', () {
    test('cached en-US renders before network identity is available', () async {
      final controller = LocaleController(
        cache: FakeLocaleCache('en-US'),
        profileApi: FakeProfileApi(),
      );
      await controller.hydrateFromCache();
      expect(controller.current.value, SupportedLocale.enUS);
    });

    test('failed profile PATCH keeps the prior GetX locale and cache', () async {
      final cache = FakeLocaleCache('vi-VN');
      final controller = LocaleController(
        cache: cache,
        profileApi: FailingProfileApi(),
      );
      final changed = await controller.updatePreference(SupportedLocale.enUS);
      expect(changed, isFalse);
      expect(controller.current.value, SupportedLocale.viVN);
      expect(await cache.read(), SupportedLocale.viVN);
    });

    test('successful updatePreference persists to cache and updates state', () async {
      final cache = FakeLocaleCache('vi-VN');
      final api = FakeProfileApi();
      final controller = LocaleController(cache: cache, profileApi: api);
      final changed = await controller.updatePreference(SupportedLocale.enUS);

      expect(changed, isTrue);
      expect(api.updated, SupportedLocale.enUS);
      expect(controller.current.value, SupportedLocale.enUS);
      expect(await cache.read(), SupportedLocale.enUS);
    });

    test('SupportedLocaleWire correctly parses and provides tags', () {
      expect(SupportedLocaleWire.parse('en-US'), SupportedLocale.enUS);
      expect(SupportedLocaleWire.parse('en_US'), SupportedLocale.enUS);
      expect(SupportedLocaleWire.parse('en'), SupportedLocale.enUS);
      expect(SupportedLocaleWire.parse('vi-VN'), SupportedLocale.viVN);
      expect(SupportedLocaleWire.parse('vi'), SupportedLocale.viVN);
      expect(SupportedLocaleWire.parse('unknown'), SupportedLocale.viVN);

      expect(SupportedLocale.viVN.tag, 'vi-VN');
      expect(SupportedLocale.enUS.tag, 'en-US');
      expect(SupportedLocale.viVN.transcriptionLanguage, 'vi');
      expect(SupportedLocale.enUS.transcriptionLanguage, 'en');
    });

    test('setLocale directly updates locale and persists to cache', () async {
      final cache = FakeLocaleCache('vi-VN');
      final controller = LocaleController(cache: cache);
      await controller.setLocale(SupportedLocale.enUS);

      expect(controller.current.value, SupportedLocale.enUS);
      expect(await cache.read(), SupportedLocale.enUS);
    });

    test('toggleLocale switches between viVN and enUS', () async {
      final cache = FakeLocaleCache('vi-VN');
      final controller = LocaleController(cache: cache);
      controller.current.value = SupportedLocale.viVN;

      await controller.toggleLocale();
      expect(controller.current.value, SupportedLocale.enUS);
      expect(await cache.read(), SupportedLocale.enUS);

      await controller.toggleLocale();
      expect(controller.current.value, SupportedLocale.viVN);
      expect(await cache.read(), SupportedLocale.viVN);
    });
  });
}
