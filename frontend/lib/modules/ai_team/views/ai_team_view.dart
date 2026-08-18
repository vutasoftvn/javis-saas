import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/ai_team_controller.dart';
import '../widgets/ai_team_agent_studio_dialog.dart';
import '../widgets/ai_team_agents_grid.dart';
import '../widgets/ai_team_approval_banner.dart';
import '../widgets/ai_team_filter_bar.dart';
import '../widgets/ai_team_kpi_row.dart';
import '../widgets/ai_team_skill_tool_hub_dialog.dart';
import '../widgets/ai_team_work_products_section.dart';

/// Control Plane tổng quan Đội ngũ Nhân sự AI (COSA Workforce)
class AiTeamView extends StatelessWidget {
  const AiTeamView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<AiTeamController>()) Get.put(AiTeamController());
    final controller = Get.find<AiTeamController>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 1. Floating Top Bar
        Obx(() {
          final totalCount = controller.agents.length;
          final customCount =
              controller.agents.where((a) => a['is_system'] == false).length;

          return JavisFloatingAppBar(
            title: 'Tổng quan Đội ngũ AI (Workforce Control Plane)',
            subtitle:
                'Quản trị $totalCount Nhân sự AI ($customCount tùy biến), phân quyền kỹ năng & kiểm soát rủi ro',
            icon: Icons.groups_rounded,
            actions: [
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF818CF8),
                  side: const BorderSide(color: Color(0xFF6366F1), width: 1.2),
                  backgroundColor: const Color(0xFF6366F1).withValues(alpha: 0.1),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                onPressed: () =>
                    AiTeamSkillToolHubDialog.show(context, controller),
                icon: const Icon(Icons.hub_rounded, size: 16),
                label: const Text('Kho Kỹ năng & Tools',
                    style:
                        TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.black,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                ),
                onPressed: () =>
                    AiTeamAgentStudioDialog.show(context, controller),
                icon: const Icon(Icons.person_add_alt_1_rounded, size: 16),
                label: const Text('+ Thêm Nhân sự AI',
                    style:
                        TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: controller.loading.value
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: AppTheme.primary),
                      )
                    : const Icon(Icons.refresh, color: AppTheme.primary),
                tooltip: 'Làm mới toàn bộ dữ liệu',
                onPressed: controller.loading.value ? null : controller.load,
              ),
            ],
          );
        }),
        const SizedBox(height: 10),

        // 2. Main Dashboard Body
        Expanded(
          child: Obx(() {
            if (controller.loading.value &&
                controller.dashboardSummary.value == null) {
              return const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: AppTheme.primary),
                    SizedBox(height: 16),
                    Text('Đang đồng bộ Control Plane...',
                        style: TextStyle(color: AppTheme.textMutedDark)),
                  ],
                ),
              );
            }

            final summary = controller.dashboardSummary.value ?? {};
            final financials =
                summary['financials'] as Map<String, dynamic>? ?? {};
            final governance =
                summary['governance'] as Map<String, dynamic>? ?? {};
            final workforce =
                summary['workforce'] as Map<String, dynamic>? ?? {};
            final health =
                workforce['health_status'] as Map<String, dynamic>? ?? {};

            return RefreshIndicator(
              onRefresh: controller.load,
              color: AppTheme.primary,
              backgroundColor: AppTheme.surfaceDark,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.only(bottom: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Section 1: KPI Stats Row
                    AiTeamKpiRow(
                      workforce: workforce,
                      health: health,
                      financials: financials,
                      governance: governance,
                    ),
                    const SizedBox(height: 12),

                    // Section 2: Pending Approval Banner
                    if (controller.pendingApprovals.isNotEmpty) ...[
                      AiTeamApprovalBanner(controller: controller),
                      const SizedBox(height: 12),
                    ],

                    // Section 3: Department & Type Filter Bar
                    AiTeamFilterBar(controller: controller),
                    const SizedBox(height: 12),

                    // Section 4: Workforce Agents Grid
                    AiTeamAgentsGrid(controller: controller),
                    const SizedBox(height: 20),

                    // Section 5: Work Products Section
                    if (controller.workProducts.isNotEmpty)
                      AiTeamWorkProductsSection(controller: controller),
                  ],
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}
