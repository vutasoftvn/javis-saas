import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../modules/auth/services/auth_service.dart';
import 'locale_cache.dart';
import 'supported_locale.dart';

abstract interface class ProfileLocaleApi {
  Future<bool> updatePreferredLocale(SupportedLocale locale);
}

class DefaultProfileLocaleApi implements ProfileLocaleApi {
  final AuthService _authService;
  DefaultProfileLocaleApi([AuthService? authService])
      : _authService = authService ?? AuthService();

  @override
  Future<bool> updatePreferredLocale(SupportedLocale locale) async {
    final res = await _authService.updateProfile(preferredLocale: locale.tag);
    return res != null;
  }
}

class LocaleController extends GetxController {
  LocaleController({
    LocaleCache? cache,
    ProfileLocaleApi? profileApi,
  })  : _cache = cache ?? SharedPreferencesLocaleCache(),
        _profileApi = profileApi ?? DefaultProfileLocaleApi();

  final LocaleCache _cache;
  final ProfileLocaleApi _profileApi;

  final Rx<SupportedLocale> current = SupportedLocale.viVN.obs;

  Locale get flutterLocale => current.value.flutterLocale;

  @override
  void onInit() {
    super.onInit();
    hydrateFromCache();
  }

  void _safeUpdateGetLocale(Locale loc) {
    Get.locale = loc;
    final binding = WidgetsBinding.instance;
    final isTest = binding.runtimeType.toString().contains('Test');
    if (!isTest && Get.context != null) {
      try {
        Get.updateLocale(loc);
      } catch (_) {}
    }
  }

  Future<void> hydrateFromCache() async {
    try {
      final cached = await _cache.read();
      if (cached != null) {
        current.value = cached;
        _safeUpdateGetLocale(cached.flutterLocale);
      }
    } catch (_) {
      // fallback
    }
  }

  Future<void> applyServerLocale(SupportedLocale locale) async {
    current.value = locale;
    _safeUpdateGetLocale(locale.flutterLocale);
    await _cache.write(locale);
  }

  Future<bool> updatePreference(SupportedLocale locale) async {
    final success = await _profileApi.updatePreferredLocale(locale);
    if (!success) {
      return false;
    }
    await applyServerLocale(locale);
    return true;
  }

  Future<void> switchLanguage(String code) async {
    final parsed = SupportedLocaleWire.parse(code);
    await updatePreference(parsed);
  }

  Future<void> setLocale(SupportedLocale locale) async {
    await applyServerLocale(locale);
  }

  Future<void> toggleLocale() async {
    final next = current.value == SupportedLocale.viVN
        ? SupportedLocale.enUS
        : SupportedLocale.viVN;
    await setLocale(next);
  }
}
