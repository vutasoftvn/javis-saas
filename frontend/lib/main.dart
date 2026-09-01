import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:get/get.dart';
import 'core/theme/app_theme.dart';
import 'core/routing/app_pages.dart';
import 'core/routing/app_routes.dart';
import './modules/auth/services/auth_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  await AuthService.init();

  // Xac thuc token cache truoc khi quyet dinh route dau tien - tranh vao
  // thang man hinh hub voi 1 token da het han/khong hop le (chi check
  // "co token hay khong" truoc day gay ra vao duoc dashboard demo du chua
  // dang nhap that). Neu khong xac dinh duoc (loi mang) van cho vao hub,
  // HubAuthMixin.ensureAuthenticated se xac thuc lai va tu dang xuat neu can.
  var startAuthenticated = AuthService.isAuthenticated;
  if (startAuthenticated) {
    final valid = await AuthService.validateCachedToken();
    if (valid == false) {
      await AuthService().logout();
      startAuthenticated = false;
    }
  }

  runApp(MyApp(hasToken: startAuthenticated));
}

class MyApp extends StatelessWidget {
  final bool hasToken;
  const MyApp({super.key, required this.hasToken});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      title: 'COSA - Hệ điều hành doanh nghiệp AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme, // We only use dark theme for now
      initialRoute: hasToken ? AppRoutes.hub : AppRoutes.login,
      getPages: AppPages.routes,
      locale: const Locale('vi', 'VN'),
      fallbackLocale: const Locale('vi', 'VN'),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('vi', 'VN'),
        Locale('en', 'US'),
      ],
    );
  }
}

