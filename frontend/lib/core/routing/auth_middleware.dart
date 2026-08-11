import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'app_routes.dart';
import '../../data/services/auth_service.dart';

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
