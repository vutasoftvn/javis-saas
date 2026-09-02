import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'app_routes.dart';
import '../../modules/auth/services/auth_service.dart';

class AuthMiddleware extends GetMiddleware {
  @override
  int? get priority => 1;

  @override
  RouteSettings? redirect(String? route) {
    if (!AuthService.isAuthenticated) {
      return const RouteSettings(name: AppRoutes.login);
    }
    return null;
  }

  @override
  Future<GetNavConfig?> redirectDelegate(GetNavConfig route) async {
    if (!AuthService.isAuthenticated) {
      return GetNavConfig.fromRoute(AppRoutes.login);
    }
    return await super.redirectDelegate(route);
  }
}

/// Task 4 — Workspace Picker chỉ có ý nghĩa khi đến từ một login flow thật
/// (route argument mang `platformToken` + danh sách `workspaces` vừa
/// sync-from-platform). Deep-link trực tiếp, hot-restart mất `Get.arguments`,
/// hay điều hướng lại trang này bằng tay đều khiến picker render "chết"
/// (không dữ liệu, mọi thao tác chọn workspace đều lỗi `platformToken`
/// rỗng). Middleware này bắt đúng trường hợp đó ở tầng routing, quay lại
/// Login (nơi flow login sẽ tự tạo lại `platformToken` + danh sách
/// workspaces hợp lệ) thay vì render UI chết.
class WorkspacePickerGuardMiddleware extends GetMiddleware {
  @override
  int? get priority => 2;

  @override
  RouteSettings? redirect(String? route) {
    if (!_hasValidPickerArguments(Get.arguments)) {
      return const RouteSettings(name: AppRoutes.login);
    }
    return null;
  }

  static bool _hasValidPickerArguments(Object? arguments) {
    if (arguments is! Map) return false;
    final token = arguments['platformToken'];
    final workspaces = arguments['workspaces'];
    return token is String &&
        token.isNotEmpty &&
        workspaces is List<WorkspaceSummary> &&
        workspaces.isNotEmpty;
  }
}
