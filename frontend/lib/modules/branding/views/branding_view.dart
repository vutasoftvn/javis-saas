import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/branding_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class BrandingView extends GetView<BrandingController> {
  const BrandingView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<BrandingController>()) {
      Get.put(BrandingController());
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const JavisFloatingAppBar(
          title: 'Thương hiệu & Giao diện',
          subtitle: 'Tùy chỉnh nhận diện thương hiệu, màu sắc và logo',
          icon: Icons.palette_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator());
            }
            return const Center(
              child: Text(
                'Quản lý Thương hiệu đã sẵn sàng',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
              ),
            );
          }),
        ),
      ],
    );
  }
}
