import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/backup_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class BackupView extends GetView<BackupController> {
  const BackupView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<BackupController>()) {
      Get.put(BackupController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const JavisFloatingAppBar(
          title: 'Sao lưu & Phục hồi',
          subtitle: 'Quản lý các bản sao lưu dữ liệu và khôi phục hệ thống',
          icon: Icons.backup_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator());
            }
            return const Center(
              child: Text(
                'Hệ thống sao lưu dữ liệu đã sẵn sàng',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
              ),
            );
          }),
        ),
      ],
    );
  }
}
