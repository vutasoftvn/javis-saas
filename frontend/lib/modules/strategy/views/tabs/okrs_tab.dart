import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../widgets/okrs/okr_objective_card.dart';
import '../../widgets/okrs/okr_plan_card.dart';
import '../../widgets/okrs/okr_dialogs.dart';

class OkrsTab extends GetView<StrategyController> {
  const OkrsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(
          child: CircularProgressIndicator(color: AppTheme.primaryLight),
        );
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Objectives List
            if (controller.objectives.isNotEmpty)
              Column(
                children: controller.objectives
                    .map((obj) => OkrObjectiveCard(obj: obj, controller: controller))
                    .toList(),
              ),

            if (controller.objectives.isNotEmpty && controller.weeklyPlans.isNotEmpty)
              const SizedBox(height: 48),

            // Weekly Plans & Commitments List
            if (controller.weeklyPlans.isNotEmpty)
              Column(
                children: controller.weeklyPlans
                    .map((plan) => OkrPlanCard(plan: plan, controller: controller))
                    .toList(),
              ),
          ],
        ),
      );
    });
  }

  static void showCreateObjectiveDialog(BuildContext context, StrategyController controller) {
    OkrDialogs.showCreateObjectiveDialog(context, controller);
  }

  static void showCreateCycleDialog(BuildContext context, StrategyController controller) {
    OkrDialogs.showCreateCycleDialog(context, controller);
  }
}
