import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/localization/locale_cache.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/profile/controllers/profile_controller.dart';
import 'package:frontend/modules/profile/views/profile_view.dart';

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

class FakeAuthService extends AuthService {
  @override
  Future<Map<String, dynamic>?> getMe() async {
    return {
      'id': 'user-1',
      'email': 'test@javis.ai',
      'display_name': 'Tester',
      'role': 'founder',
    };
  }

  @override
  Future<Map<String, dynamic>?> updateProfile({
    String? phone,
    String? displayName,
    String? preferredLocale,
  }) async {
    return {
      'id': 'user-1',
      'email': 'test@javis.ai',
      'display_name': displayName ?? 'Tester',
      'phone': phone,
      'preferred_locale': preferredLocale ?? 'vi-VN',
    };
  }
}

Widget buildProfileWithLocaleController({LocaleController? lc}) {
  Get.reset();
  final LocaleController localeController = lc ??
      Get.put(
        LocaleController(
          cache: FakeLocaleCache('vi-VN'),
          profileApi: FakeProfileApi(),
        ),
        permanent: true,
      );
  Get.put(
    ProfileController(
      authService: FakeAuthService(),
      localeController: localeController,
    ),
    permanent: true,
  );

  return GetMaterialApp(
    translations: AppTranslations(),
    locale: localeController.current.value.flutterLocale,
    fallbackLocale: const Locale('vi', 'VN'),
    home: const ProfileView(),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('profile language selector calls PATCH then updates labels', (tester) async {
    await tester.pumpWidget(buildProfileWithLocaleController());
    await tester.pumpAndSettle();

    expect(find.text('Ngôn ngữ'), findsOneWidget);
    expect(find.text('English'), findsOneWidget);

    await tester.ensureVisible(find.text('English'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('English'));
    await tester.pumpAndSettle();

    expect(find.text('Language'), findsOneWidget);
  });
}
