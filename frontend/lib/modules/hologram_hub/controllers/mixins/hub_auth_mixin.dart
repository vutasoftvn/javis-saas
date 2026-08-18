import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../data/services/auth_service.dart';

mixin HubAuthMixin on GetxController {
  // ── Abstract service getter ──────────────────────────────────────────────
  AuthService get authService;

  // ── Observables ──────────────────────────────────────────────────────────
  final currentTime = ''.obs;
  final currentDate = ''.obs;
  final userName = 'Dzu Nguyen'.obs;
  final userRole = 'Founder Mode'.obs;

  // ── Public API ───────────────────────────────────────────────────────────

  Future<void> ensureAuthenticated() async {
    if (!AuthService.isAuthenticated) {
      await authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }
    final me = await authService.getMe();
    if (me == null) {
      debugPrint(
        '[HologramHub] Token không hợp lệ hoặc đã hết hạn -> Tự động chuyển về màn Đăng nhập',
      );
      await authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }
    if (me['display_name'] != null &&
        (me['display_name'] as String).isNotEmpty) {
      userName.value = me['display_name'] as String;
    }
    if (me['role'] != null) {
      userRole.value =
          me['role'] == 'admin' ? 'Founder Mode' : (me['role'] as String);
    }
  }

  Future<void> logout() async {
    await authService.logout();
    Get.offAllNamed(AppRoutes.login);
  }

  void updateClock() {
    final now = DateTime.now();
    final hour = now.hour.toString().padLeft(2, '0');
    final minute = now.minute.toString().padLeft(2, '0');
    currentTime.value = '$hour:$minute';

    const weekdays = [
      'Thứ 2',
      'Thứ 3',
      'Thứ 4',
      'Thứ 5',
      'Thứ 6',
      'Thứ 7',
      'Chủ nhật',
    ];
    final weekday = weekdays[now.weekday - 1];
    currentDate.value = '$weekday, ${now.day} tháng ${now.month}, ${now.year}';
  }

  // 3 Operating Modes: 'founder', 'operator', 'developer'
  final operatingMode = 'founder'.obs;

  void setOperatingMode(String mode) {
    operatingMode.value = mode;
    userRole.value = mode == 'developer'
        ? 'Developer Mode'
        : (mode == 'operator' ? 'Operator Mode' : 'Founder Mode');
  }
}
