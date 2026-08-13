import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/settings_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class SettingsView extends GetView<SettingsController> {
  const SettingsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<SettingsController>()) {
      Get.put(SettingsController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const JavisFloatingAppBar(
          title: 'Cài đặt hệ thống',
          subtitle: 'Cấu hình tài khoản, workspace và tùy chỉnh trải nghiệm',
          icon: Icons.settings_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator());
            }
            return const Center(
              child: Text(
                'Cài đặt hệ thống đã sẵn sàng',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
              ),
            );
          }),
        ),
      ],
    );
  }
}
