import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/foundation_controller.dart';
import 'tabs/foundation_tab.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

class StrategyFoundationView extends GetView<FoundationController> {
  const StrategyFoundationView({super.key});

  @override
  Widget build(BuildContext context) {
    final foundationController = Get.isRegistered<FoundationController>()
        ? Get.find<FoundationController>()
        : Get.put(FoundationController());

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CosaFloatingAppBar(
            title: L10nKey.strategyFoundationTitle.tr,
            subtitle: L10nKey.strategyFoundationSubtitle.tr,
            actions: [
              ElevatedButton.icon(
                onPressed: () => FoundationTab.showCreateCanvasDialog(context, foundationController),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: Text(L10nKey.strategyFoundationCreate.tr),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(100),
                  ),
                ),
              ),
            ],
          ),
          const Expanded(
            child: FoundationTab(),
          ),
        ],
      ),
    );
  }
}
