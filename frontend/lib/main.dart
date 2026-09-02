import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:get/get.dart';
import 'core/theme/app_theme.dart';
import 'core/routing/app_pages.dart';
import 'core/routing/app_routes.dart';
import 'core/services/secure_storage_service.dart';
import 'core/session/session_binding.dart';
import 'core/session/session_controller.dart';
import './modules/auth/services/auth_service.dart';
import './modules/remote_access/controllers/remote_access_controller.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Task 4 — SessionController đăng ký permanent TRƯỚC khi quyết định
  // initial route: mọi trang sau (workspace picker, hub, ...) đều cần
  // `Get.find<SessionController>()` sẵn có bất kể bootstrap bên dưới thành
  // công hay lỗi. Việc `Get.put` một GetxController thuần không có I/O nên
  // không nằm trong try/catch của bootstrap.
  final sessionController = Get.put(SessionController(), permanent: true);
  // Task 5 — phải đăng ký TRƯỚC `activateWorkspace(...)` bên dưới: commit
  // của SessionController chỉ đồng bộ RemoteAccessController khi nó ĐÃ được
  // đăng ký (`Get.isRegistered` guard trong `_commit`) — nếu đăng ký muộn
  // hơn (vd. chỉ trong SessionBinding của GetMaterialApp), lần activate đầu
  // tiên lúc bootstrap sẽ bị bỏ lỡ, RuntimeAppChrome không nhận state ban đầu.
  Get.put(RemoteAccessController(), permanent: true);

  var initialRoute = AppRoutes.login;
  try {
    await AuthService.init();

    // Xac thuc token cache truoc khi quyet dinh route dau tien - tranh vao
    // thang man hinh hub voi 1 token da het han/khong hop le (chi check
    // "co token hay khong" truoc day gay ra vao duoc dashboard demo du chua
    // dang nhap that).
    var startAuthenticated = AuthService.isAuthenticated;
    if (startAuthenticated) {
      final valid = await AuthService.validateCachedToken();
      if (valid == false) {
        await AuthService().logout();
        startAuthenticated = false;
      }
    }

    // Task 4 review carry-forward — trước đây main() chỉ dựa
    // `AuthService.isAuthenticated` (cache token) để chọn Hub, KHÔNG verify
    // lại workspace context qua SessionController. Giờ bootstrap gọi
    // `activateWorkspace` thật (verify identity + session-context) và chỉ
    // vào Hub khi `sessionController.active` thực sự được set — không suy
    // diễn từ việc "có token cache" nữa.
    if (startAuthenticated) {
      final workspaceId = await SecureStorageService.read('workspace_id');
      if (workspaceId != null && workspaceId.isNotEmpty) {
        await sessionController.activateWorkspace(workspaceId);
      }
    }

    initialRoute =
        sessionController.active.value != null ? AppRoutes.hub : AppRoutes.login;
  } catch (e, stackTrace) {
    // Task 2 review carry-forward — một lỗi Keychain/Keystore thật (hoặc bất
    // kỳ lỗi nào khác) trong lúc bootstrap session KHÔNG được phép làm
    // crash app trước khi `runApp()` từng được gọi: luôn có một nhánh lỗi
    // rõ ràng (Login) thay vì một exception không bắt được chặn đứng toàn
    // bộ app ở màn hình trắng.
    debugPrint(
      '[main] Session bootstrap failed — routing to Login instead of crashing: $e\n$stackTrace',
    );
    initialRoute = AppRoutes.login;
  }

  runApp(MyApp(initialRoute: initialRoute));
}

class MyApp extends StatelessWidget {
  final String initialRoute;
  const MyApp({super.key, required this.initialRoute});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      title: 'COSA - Hệ điều hành doanh nghiệp AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme, // We only use dark theme for now
      initialRoute: initialRoute,
      initialBinding: SessionBinding(),
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

