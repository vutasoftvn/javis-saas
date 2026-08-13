import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import 'tabs/foundation_tab.dart';
import 'tabs/okrs_tab.dart';
import 'tabs/project_roadmap_tab.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';

import '../controllers/foundation_controller.dart';
import '../controllers/project_orchestration_controller.dart';

class StrategyView extends GetView<StrategyController> {
  const StrategyView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }
    final foundationController = Get.isRegistered<FoundationController>()
        ? Get.find<FoundationController>()
        : Get.put(FoundationController());
    if (!Get.isRegistered<ProjectOrchestrationController>()) {
      Get.put(ProjectOrchestrationController());
    }

    return DefaultTabController(
      length: 3,
      child: Container(
        color: Colors.transparent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. Top Floating AppBar Card
            JavisFloatingAppBar(
              title: 'Chu kỳ & Chiến lược OKRs',
              subtitle: 'Điều chỉnh việc thực thi của nhóm với chu kỳ mục tiêu và nền tảng của công ty.',
              actions: [
                OutlinedButton.icon(
                  onPressed: () => OkrsTab.showCreateCycleDialog(context, controller),
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
                  onPressed: controller.isGeneratingAi.value ? null : () => OkrsTab.showAiOkrModal(context, controller),
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
                  onPressed: () => OkrsTab.showCreateObjectiveDialog(context, controller),
                  icon: const Icon(Icons.add_rounded, size: 16),
                  label: const Text('Thêm Objective'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: () => FoundationTab.showCreateCanvasDialog(context, foundationController),
                  icon: const Icon(Icons.add_rounded, size: 16),
                  label: const Text('Tạo Strategy'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(100),
                    ),
                  ),
                ),
              ],
            ),

            // 2. Separate Tab Navigation Bar (Ultra-Compact Pill, Tight Width, Centered)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Center(
                child: IntrinsicWidth(
                  child: Container(
                    height: 38,
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(color: AppTheme.borderDark),
                    ),
                    child: TabBar(
                      isScrollable: true,
                      tabAlignment: TabAlignment.center,
                      indicatorSize: TabBarIndicatorSize.tab,
                      indicator: BoxDecoration(
                        color: AppTheme.primary,
                        borderRadius: BorderRadius.circular(100),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.primary.withValues(alpha: 0.4),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      labelColor: const Color(0xFF04070E),
                      unselectedLabelColor: AppTheme.textMutedDark,
                      labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      unselectedLabelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.normal),
                      dividerColor: Colors.transparent,
                      padding: EdgeInsets.zero,
                      labelPadding: const EdgeInsets.symmetric(horizontal: 16),
                      tabs: const [
                        Tab(height: 32, child: Center(child: Text('Chu kỳ & OKRs'))),
                        Tab(height: 32, child: Center(child: Text('Nền tảng Doanh nghiệp'))),
                        Tab(height: 32, child: Center(child: Text('Project & MVP Roadmap'))),
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // 3. Tab Views Content Body
            const Expanded(
              child: TabBarView(
                children: [
                  OkrsTab(),
                  FoundationTab(),
                  ProjectRoadmapTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

