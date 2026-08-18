import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/settings_controller.dart';
import '../../../core/widgets/floating_app_bar.dart';
import 'widgets/ai_gateway_settings_card.dart';

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
          subtitle: 'Cấu hình tài khoản, AI Gateway & tối ưu hóa chi phí',
          icon: Icons.settings_rounded,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator());
            }
            return SingleChildScrollView(
              padding: const EdgeInsets.only(top: 8, bottom: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: const [
                  AiGatewaySettingsCard(),
                ],
              ),
            );
          }),
        ),
      ],
    );
  }
}

