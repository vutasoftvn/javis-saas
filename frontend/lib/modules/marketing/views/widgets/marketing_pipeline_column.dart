import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import 'marketing_common.dart';

/// Cột quy trình 6 bước Marketing OS khép kín ở bên trái.
class MarketingPipelineColumn extends GetView<MarketingController> {
  const MarketingPipelineColumn({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final selectedNode = controller.selectedFlowNode.value;
      final selectedProjectId = controller.selectedProjectId.value;
      final selectedProj = controller.projects.firstWhereOrNull((p) => p['id']?.toString() == selectedProjectId);

      return SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Pipeline Card
            MarketingCard(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      gradient: AppTheme.primaryGradient,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.account_tree_rounded, color: Color(0xFF04070E), size: 18),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          selectedProj != null ? (selectedProj['title']?.toString() ?? 'Dự án') : 'Pipeline Marketing OS',
                          style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.bold, color: Colors.white),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        const Text(
                          'Chu trình tự động 6 bước khép kín',
                          style: TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                        ),
                      ],
                    ),
                  ),
                  const MarketingChip(
                    label: 'Tự động',
                    color: AppTheme.success,
                    icon: Icons.sync_rounded,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),

            // 6 Interactive Pipeline Nodes
            _buildPipelineNodeCard(
              step: 1,
              nodeKey: 'trigger',
              title: '1. Founder Giao việc & Kích hoạt',
              subtitle: 'Nhận brief, intent & lập mục tiêu OKR',
              badge: '${controller.objectives.length} mục tiêu',
              icon: Icons.flag_circle_rounded,
              accentColor: Colors.purpleAccent,
              isSelected: selectedNode == 'trigger',
            ),
            _buildPipelineConnector(),

            _buildPipelineNodeCard(
              step: 2,
              nodeKey: 'context',
              title: '2. Bối cảnh & Canvas Dự án',
              subtitle: 'ICP, Jobs-to-be-done, Value Prop & Offer',
              badge: 'Ground Truth',
              icon: Icons.psychology_rounded,
              accentColor: Colors.blueAccent,
              isSelected: selectedNode == 'context',
            ),
            _buildPipelineConnector(),

            _buildPipelineNodeCard(
              step: 3,
              nodeKey: 'content',
              title: '3. AI Thực thi & Chiến dịch',
              subtitle: 'Kế hoạch bài viết, video, ad copy & skills',
              badge: '${controller.campaigns.length} chiến dịch',
              icon: Icons.auto_awesome_rounded,
              accentColor: AppTheme.primaryLight,
              isSelected: selectedNode == 'content',
            ),
            _buildPipelineConnector(),

            _buildPipelineNodeCard(
              step: 4,
              nodeKey: 'governance',
              title: '4. Gate Phê duyệt An toàn',
              subtitle: 'Human-in-the-loop: Kiểm soát xuất bản & chi tiêu',
              badge: '${controller.pendingApprovals.length} chờ duyệt',
              badgeColor: controller.pendingApprovals.isNotEmpty ? Colors.deepOrangeAccent : null,
              icon: Icons.security_rounded,
              accentColor: controller.pendingApprovals.isNotEmpty ? Colors.deepOrangeAccent : Colors.amberAccent,
              isSelected: selectedNode == 'governance',
            ),
            _buildPipelineConnector(),

            _buildPipelineNodeCard(
              step: 5,
              nodeKey: 'leadgen',
              title: '5. Thu thập Khách hàng & CRM',
              subtitle: 'Landing page, Form UTM ➔ Sales Leads CRM',
              badge: '${controller.funnel['leads_count'] ?? 0} leads',
              icon: Icons.filter_alt_rounded,
              accentColor: Colors.tealAccent,
              isSelected: selectedNode == 'leadgen',
            ),
            _buildPipelineConnector(),

            _buildPipelineNodeCard(
              step: 6,
              nodeKey: 'learning',
              title: '6. Đo lường & Vòng lặp Học hỏi',
              subtitle: 'Analytics CAC/LTV, A/B test & Playbooks',
              badge: '${controller.learnings.length} bài học',
              icon: Icons.insights_rounded,
              accentColor: Colors.deepOrangeAccent,
              isSelected: selectedNode == 'learning',
            ),
            const SizedBox(height: 16),
          ],
        ),
      );
    });
  }

  Widget _buildPipelineConnector() {
    return Center(
      child: Container(
        height: 14,
        width: 2,
        margin: const EdgeInsets.symmetric(vertical: 2),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AppTheme.primary.withValues(alpha: 0.8),
              AppTheme.primary.withValues(alpha: 0.2),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPipelineNodeCard({
    required int step,
    required String nodeKey,
    required String title,
    required String subtitle,
    required String badge,
    Color? badgeColor,
    required IconData icon,
    required Color accentColor,
    required bool isSelected,
  }) {
    return InkWell(
      onTap: () => controller.selectFlowNode(nodeKey),
      borderRadius: BorderRadius.circular(12),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? accentColor.withValues(alpha: 0.12) : AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? accentColor : AppTheme.borderDark,
            width: isSelected ? 1.5 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: accentColor.withValues(alpha: 0.25),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: accentColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: accentColor.withValues(alpha: 0.4)),
              ),
              child: Center(
                child: Text(
                  '$step',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: accentColor),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.bold,
                      color: isSelected ? accentColor : Colors.white,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            MarketingChip(label: badge, color: badgeColor ?? accentColor),
          ],
        ),
      ),
    );
  }
}
