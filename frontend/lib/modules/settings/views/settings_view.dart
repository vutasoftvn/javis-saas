import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/settings_controller.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../../../core/localization/app_translations.dart';
import 'widgets/ai_gateway_settings_card.dart';
import 'widgets/module_visibility_settings_card.dart';
import 'widgets/workspace_orientation_settings_card.dart';
import 'widgets/permissions_panel.dart';
import 'model_provider_settings_view.dart';

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
        CosaFloatingAppBar(
          title: L10nKey.settingsTitle.tr,
          subtitle: L10nKey.settingsSubtitle.tr,
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
                  WorkspaceOrientationSettingsCard(),
                  SizedBox(height: 12),
                  ModuleVisibilitySettingsCard(),
                  SizedBox(height: 12),
                  AiGatewaySettingsCard(),
                  SizedBox(height: 12),
                  ModelProviderSettingsView(),
                  SizedBox(height: 12),
                  PermissionsPanel(),
                ],
              ),
            );
          }),
        ),
      ],
    );
  }
}


