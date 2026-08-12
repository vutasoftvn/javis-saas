import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import 'core/theme/app_theme.dart';
import 'core/routing/app_pages.dart';
import 'core/routing/app_routes.dart';
import 'data/services/auth_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  await AuthService.init();

  runApp(MyApp(hasToken: AuthService.isAuthenticated));
}

class MyApp extends StatelessWidget {
  final bool hasToken;
  const MyApp({super.key, required this.hasToken});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      title: 'COSA Brain',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme, // We only use dark theme for now
      initialRoute: hasToken ? AppRoutes.hub : AppRoutes.login,
      getPages: AppPages.routes,
    );
  }
}

