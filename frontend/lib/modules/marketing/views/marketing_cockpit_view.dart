import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../controllers/marketing_controller.dart';
import 'tabs/marketing_node1_objectives_tab.dart';
import 'tabs/marketing_node2_context_tab.dart';
import 'tabs/marketing_node3_content_tab.dart';
import 'tabs/marketing_node4_approvals_tab.dart';
import 'tabs/marketing_node5_funnel_tab.dart';
import 'tabs/marketing_node6_learning_tab.dart';
import 'widgets/marketing_common.dart';
import 'widgets/marketing_kpi_header.dart';
import 'widgets/marketing_pipeline_column.dart';

/// Marketing Cockpit - Màn hình điều khiển vòng lặp khép kín của Marketing OS.
///
/// Toàn bộ nhãn hiển thị bằng tiếng Việt; chỉ giữ nguyên mã capability kiểu
/// `marketing.cro` vì đó là định danh kỹ thuật dùng chung với Skill Registry.
class MarketingCockpitView extends GetView<MarketingController> {
  const MarketingCockpitView({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildFloatingAppBar(context),
        const SizedBox(height: 12),
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight));
            }
            if (controller.errorMessage.value.isNotEmpty) {
              return _buildErrorState();
            }
            if (controller.projects.isEmpty) {
              return _buildNoProjectState(context);
            }
            return Column(
              children: [
                const MarketingKpiHeader(),
                const SizedBox(height: 12),
                Expanded(
                  child: _buildTwoColumnWorkstation(context),
                ),
              ],
            );
          }),
        ),
      ],
    );
  }

  Widget _buildFloatingAppBar(BuildContext context) {
    return JavisFloatingAppBar(
      title: 'Trung tâm điều hành Marketing',
      subtitle: 'Vòng lặp khép kín: Chiến lược → Thực thi → Đo lường → Học hỏi',
      icon: Icons.campaign_rounded,
      actions: [
        // Project Selector Dropdown (luôn là 1 dự án cụ thể)
        Obx(() {
          final projects = controller.projects;
          final currentProjectId = controller.selectedProjectId.value;

          if (projects.isEmpty) {
            return const SizedBox.shrink();
          }

          final selectedValue =
              (currentProjectId != null && projects.any((p) => p['id']?.toString() == currentProjectId))
                  ? currentProjectId
                  : projects.first['id']?.toString();

          return Container(
            height: 38,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppTheme.primary.withValues(alpha: 0.6),
              ),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: selectedValue,
                icon: const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white70, size: 18),
                dropdownColor: kMarketingCardColor,
                borderRadius: BorderRadius.circular(12),
                style: const TextStyle(fontSize: 12.5, color: Colors.white),
                items: projects.map((p) {
                  final pId = p['id']?.toString() ?? '';
                  final title = p['title']?.toString() ?? 'Dự án';
                  return DropdownMenuItem<String>(
                    value: pId,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.rocket_launch_outlined, size: 15, color: Colors.amberAccent),
                        const SizedBox(width: 8),
                        Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) controller.selectProject(val);
                },
              ),
            ),
          );
        }),
        const SizedBox(width: 8),
        Obx(
          () => controller.isSubmitting.value
              ? const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primaryLight),
                  ),
                )
              : const SizedBox.shrink(),
        ),
        Container(
          decoration: const BoxDecoration(color: AppTheme.primary, shape: BoxShape.circle),
          child: IconButton(
            tooltip: 'Tải lại dữ liệu',
            icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
            onPressed: controller.loadAllData,
          ),
        ),
      ],
    );
  }

  Widget _buildNoProjectState(BuildContext context) {
    return Center(
      child: Container(
        margin: const EdgeInsets.all(24),
        padding: const EdgeInsets.all(32),
        constraints: const BoxConstraints(maxWidth: 520),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.rocket_launch_outlined, color: AppTheme.primaryLight, size: 36),
            ),
            const SizedBox(height: 18),
            const Text(
              'Chưa có Dự án nào trong không gian làm việc',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Marketing OS vận hành dựa trên bối cảnh và mục tiêu của từng dự án cụ thể. Vui lòng tạo dự án mới để bắt đầu thiết lập cỗ máy tiếp thị tự trị.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => Get.find<DashboardController>().changePage(29, 0),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Tạo Dự án mới'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Container(
        margin: const EdgeInsets.all(24),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: kMarketingCardColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.accent.withValues(alpha: 0.3)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded, size: 46, color: AppTheme.accent),
            const SizedBox(height: 12),
            const Text(
              'Không tải được dữ liệu Marketing OS',
              style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: 460,
              child: Text(
                controller.errorMessage.value,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.5),
              ),
            ),
            const SizedBox(height: 18),
            ElevatedButton.icon(
              onPressed: controller.loadAllData,
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Thử lại'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ==========================================
  // Layout 2 Cột: Flow Pipeline (Trái) + Workstation (Phải)
  // ==========================================

  Widget _buildTwoColumnWorkstation(BuildContext context) {
    return Obx(() {
      final selectedNode = controller.selectedFlowNode.value;

      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Cột 1: 6 Flow Pipeline Nodes
          const SizedBox(
            width: 330,
            child: MarketingPipelineColumn(),
          ),
          const SizedBox(width: 14),

          // Cột 2: Active Workstation Content Area
          Expanded(
            child: _buildActiveWorkstation(context, selectedNode),
          ),
        ],
      );
    });
  }

  Widget _buildActiveWorkstation(BuildContext context, String selectedNode) {
    switch (selectedNode) {
      case 'trigger':
        return const MarketingNode1ObjectivesTab();
      case 'context':
        return const MarketingNode2ContextTab();
      case 'content':
        return const MarketingNode3ContentTab();
      case 'governance':
        return const MarketingNode4ApprovalsTab();
      case 'leadgen':
        return const MarketingNode5FunnelTab();
      case 'learning':
      default:
        return const MarketingNode6LearningTab();
    }
  }
}
