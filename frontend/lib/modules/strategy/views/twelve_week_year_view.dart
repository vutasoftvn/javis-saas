import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../widgets/twelve_wy/twelve_wy_cycle_header.dart';
import '../widgets/twelve_wy/twelve_wy_empty_state.dart';
import '../widgets/twelve_wy/twelve_wy_plan_card.dart';
import '../widgets/twelve_wy/twelve_wy_governance_dialog.dart';
import '../widgets/twelve_wy/twelve_wy_modals.dart';
import '../widgets/okrs/okr_dialogs.dart';

class TwelveWeekYearView extends GetView<StrategyController> {
  const TwelveWeekYearView({super.key});

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
            title: 'Kế hoạch Thực thi 12 Tuần (12WY)',
            subtitle: 'Stage-Gate Governance, Weekly Mission, phân bổ năng lực Founder & AI Delegation theo mô hình 12 Week Year.',
            actions: [
              OutlinedButton.icon(
                onPressed: () => TwelveWyModals.showWeek13TransitionDialog(context, controller),
                icon: const Icon(Icons.celebration_rounded, size: 16, color: Colors.pinkAccent),
                label: const Text('Tuần 13 & Kỷ Niệm', style: TextStyle(color: Colors.pinkAccent, fontSize: 13)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: Colors.pink.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: () => TwelveWyModals.showCompileCycleDialog(context, controller),
                icon: const Icon(Icons.bolt_rounded, size: 16, color: Colors.amberAccent),
                label: const Text('Compile V10', style: TextStyle(color: Colors.amberAccent, fontSize: 13)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: Colors.amber.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: () => TwelveWyGovernanceDialog.showCycleGovernanceDialog(context, controller),
                icon: const Icon(Icons.shield_outlined, size: 16, color: AppTheme.primaryLight),
                label: const Text('13-Week Stages & Gate', style: TextStyle(color: AppTheme.primaryLight, fontSize: 13)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => TwelveWyModals.showCreateWeeklyPlanDialog(context, controller),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Thêm Tuần mới'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.secondary,
                  foregroundColor: const Color(0xFF04070E),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
            ],
          ),

          // 2. 12WY Content Body
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(
                  child: CircularProgressIndicator(color: AppTheme.secondaryLight),
                );
              }

              final activeCycle = controller.twelveWeekCycles.isNotEmpty
                  ? controller.twelveWeekCycles.first as Map<String, dynamic>
                  : null;

              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (activeCycle != null)
                      TwelveWyCycleHeader(cycle: activeCycle),

                    if (controller.weeklyPlans.isEmpty)
                      TwelveWyEmptyState(onCreatePlan: () => TwelveWyModals.showCreateWeeklyPlanDialog(context, controller))
                    else
                      Column(
                        children: controller.weeklyPlans
                            .map((plan) => TwelveWyPlanCard(
                                  plan: plan,
                                  controller: controller,
                                  onReview: () => TwelveWyModals.showWeeklyReviewDialog(context, controller, plan),
                                  onCompile: () => controller.compileWeeklyPlan(plan['id']?.toString() ?? ''),
                                  onMission: () => TwelveWyModals.showEditWeeklyMissionDialog(context, controller, plan),
                                  onAddCommitment: () => OkrDialogs.showCreateCommitmentDialog(context, controller, plan['id']?.toString() ?? ''),
                                ))
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
