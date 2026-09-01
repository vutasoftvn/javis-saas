import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import 'okrs/widgets/okr_objective_card.dart';
import 'okrs/dialogs/okr_dialogs.dart';

class OkrsView extends GetView<StrategyController> {
  const OkrsView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Top Floating AppBar Card
          CosaFloatingAppBar(
            title: 'Mục tiêu & Kết quả Then chốt (OKRs)',
            subtitle: 'Theo dõi và đo lường tiến độ mục tiêu doanh nghiệp theo thời gian thực.',
            actions: [
              OutlinedButton.icon(
                onPressed: () => OkrDialogs.showCreateCycleDialog(context, controller),
                icon: const Icon(Icons.cached_rounded, size: 16),
                label: const Text('Chu kỳ OKR'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              Obx(() => OutlinedButton.icon(
                onPressed: controller.isGeneratingAi.value
                    ? null
                    : () => OkrDialogs.showAiOkrModal(context, controller),
                icon: controller.isGeneratingAi.value
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(color: AppTheme.primary, strokeWidth: 2),
                      )
                    : const Icon(Icons.auto_awesome_rounded, size: 16, color: AppTheme.primary),
                label: Text(
                  controller.isGeneratingAi.value ? 'Đang sinh AI...' : 'Tạo tự động AI',
                  style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppTheme.primary),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              )),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => OkrDialogs.showCreateObjectiveDialog(context, controller),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Thêm Objective'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
            ],
          ),

          // 2. OKR Content Body
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(
                  child: CircularProgressIndicator(color: AppTheme.primaryLight),
                );
              }

              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (controller.objectives.isNotEmpty)
                      Column(
                        children: controller.objectives
                            .map((obj) => OkrObjectiveCard(controller: controller, obj: obj))
                            .toList(),
                      ),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }
}
