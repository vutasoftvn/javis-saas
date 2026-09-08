import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/core/localization/locale_cache.dart';
import 'package:frontend/core/localization/locale_controller.dart';
import 'package:frontend/core/localization/supported_locale.dart';
import 'package:frontend/modules/auth/controllers/auth_controller.dart';
import 'package:frontend/modules/auth/views/login_view.dart';
import 'package:frontend/modules/auth/views/register_view.dart';

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

Widget buildLoginViewWithLocale({String initial = 'vi-VN'}) {
  Get.reset();
  final cache = FakeLocaleCache(initial);
  final localeController = Get.put(
    LocaleController(cache: cache),
    permanent: true,
  );
  localeController.current.value = SupportedLocaleWire.parse(initial);
  Get.locale = localeController.current.value.flutterLocale;

  Get.put(AuthController(), permanent: true);

  return GetMaterialApp(
    translations: AppTranslations(),
    locale: localeController.current.value.flutterLocale,
    fallbackLocale: const Locale('vi', 'VN'),
    home: const LoginView(),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    Get.reset();
  });

  group('AuthLanguageSwitcher & LoginView', () {
    testWidgets('renders language switcher below form card with flag icon and text', (tester) async {
      tester.view.physicalSize = const Size(1200, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildLoginViewWithLocale());
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('auth_language_switcher')), findsOneWidget);
      expect(find.byKey(const Key('auth_language_flag')), findsOneWidget);
      expect(find.byKey(const Key('auth_language_text')), findsOneWidget);
      expect(find.text('Tiếng Việt'), findsOneWidget);

      // Initial Vietnamese text
      expect(find.text('Đăng Nhập'), findsOneWidget);
      expect(find.text('Chưa có tài khoản?'), findsOneWidget);
    });

    testWidgets('tapping card toggles locale to English and updates LoginView labels', (tester) async {
      tester.view.physicalSize = const Size(1200, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildLoginViewWithLocale(initial: 'vi-VN'));
      await tester.pumpAndSettle();

      expect(find.text('Đăng Nhập'), findsOneWidget);
      expect(find.text('Tiếng Việt'), findsOneWidget);

      await tester.ensureVisible(find.byKey(const Key('auth_language_switcher')));
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      final lc = Get.find<LocaleController>();
      expect(lc.current.value, SupportedLocale.enUS);

      expect(find.text('English'), findsOneWidget);
      expect(find.text('Log In'), findsOneWidget);
      expect(find.text("Don't have an account?"), findsOneWidget);
      expect(find.text('Remember this account'), findsOneWidget);
    });

    testWidgets('tapping card again switches back to Vietnamese', (tester) async {
      tester.view.physicalSize = const Size(1200, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildLoginViewWithLocale(initial: 'en-US'));
      await tester.pumpAndSettle();

      expect(find.text('Log In'), findsOneWidget);
      expect(find.text('English'), findsOneWidget);

      await tester.ensureVisible(find.byKey(const Key('auth_language_switcher')));
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      final lc = Get.find<LocaleController>();
      expect(lc.current.value, SupportedLocale.viVN);

      expect(find.text('Tiếng Việt'), findsOneWidget);
      expect(find.text('Đăng Nhập'), findsOneWidget);
      expect(find.text('Chưa có tài khoản?'), findsOneWidget);
    });

    testWidgets('tapping card multiple times cycles between languages smoothly', (tester) async {
      tester.view.physicalSize = const Size(1200, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(buildLoginViewWithLocale(initial: 'vi-VN'));
      await tester.pumpAndSettle();

      final lc = Get.find<LocaleController>();
      expect(lc.current.value, SupportedLocale.viVN);

      // Tap 1 -> switches to EN
      await tester.ensureVisible(find.byKey(const Key('auth_language_switcher')));
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      expect(lc.current.value, SupportedLocale.enUS);
      expect(find.text('English'), findsOneWidget);
      expect(find.text('Log In'), findsOneWidget);

      // Tap 2 -> switches back to VI
      await tester.ensureVisible(find.byKey(const Key('auth_language_switcher')));
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      expect(lc.current.value, SupportedLocale.viVN);
      expect(find.text('Tiếng Việt'), findsOneWidget);
      expect(find.text('Đăng Nhập'), findsOneWidget);

      // Tap 3 -> switches back to EN
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      expect(lc.current.value, SupportedLocale.enUS);
      expect(find.text('English'), findsOneWidget);
      expect(find.text('Log In'), findsOneWidget);
    });

    testWidgets('RegisterView renders language switcher card and toggles dynamically between VI and EN', (tester) async {
      tester.view.physicalSize = const Size(1200, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      Get.reset();
      final cache = FakeLocaleCache('vi-VN');
      final lc = Get.put(LocaleController(cache: cache), permanent: true);
      lc.current.value = SupportedLocale.viVN;
      Get.locale = const Locale('vi', 'VN');

      final authCtrl = Get.put(AuthController(), permanent: true);

      await tester.pumpWidget(GetMaterialApp(
        translations: AppTranslations(),
        locale: const Locale('vi', 'VN'),
        fallbackLocale: const Locale('vi', 'VN'),
        home: const RegisterView(),
      ));
      await tester.pumpAndSettle();

      // Step 1 initial Vietnamese labels
      expect(find.text('Tạo Tài Khoản Mới'), findsOneWidget);
      expect(find.text('Họ và tên'), findsOneWidget);
      expect(find.text('Tiếp tục'), findsOneWidget);
      expect(find.text('Đã có tài khoản?'), findsOneWidget);
      expect(find.byKey(const Key('auth_language_switcher')), findsOneWidget);
      expect(find.text('Tiếng Việt'), findsOneWidget);

      // Tap switcher card on RegisterView -> switches to English
      await tester.ensureVisible(find.byKey(const Key('auth_language_switcher')));
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      expect(lc.current.value, SupportedLocale.enUS);
      expect(find.text('English'), findsOneWidget);
      expect(find.text('Create New Account'), findsOneWidget);
      expect(find.text('Full Name'), findsOneWidget);
      expect(find.text('Continue'), findsOneWidget);
      expect(find.text('Already have an account?'), findsOneWidget);

      // Move to Step 2 in English
      authCtrl.registerStep.value = 2;
      await tester.pumpAndSettle();

      expect(find.text('Set Up Company'), findsOneWidget);
      expect(find.text('Create New'), findsOneWidget);
      expect(find.text('Join'), findsOneWidget);
      expect(find.text('Company / Organization Name'), findsOneWidget);
      expect(find.text('Initialize'), findsOneWidget);
      expect(find.text('Back to step 1'), findsOneWidget);

      // Tap switcher card on RegisterView Step 2 -> switches back to Vietnamese
      await tester.ensureVisible(find.byKey(const Key('auth_language_switcher')));
      await tester.tap(find.byKey(const Key('auth_language_switcher')));
      await tester.pumpAndSettle();

      expect(lc.current.value, SupportedLocale.viVN);
      expect(find.text('Tiếng Việt'), findsOneWidget);
      expect(find.text('Thiết Lập Công Ty'), findsOneWidget);
      expect(find.text('Tạo mới'), findsOneWidget);
      expect(find.text('Tham gia'), findsOneWidget);
      expect(find.text('Tên công ty / Tổ chức'), findsOneWidget);
      expect(find.text('Khởi tạo'), findsOneWidget);
      expect(find.text('Quay lại bước 1'), findsOneWidget);
    });
  });
}
