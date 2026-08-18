import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import 'marketing_common.dart';

/// Header KPI & Banner Dự án đang kích hoạt
class MarketingKpiHeader extends GetView<MarketingController> {
  const MarketingKpiHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final summary = controller.cockpitSummary;
      final hasExecutionData = summary['has_execution_data'] == true;
      final selectedProjectId = controller.selectedProjectId.value;
      final selectedProj = controller.projects.firstWhereOrNull((p) => p['id']?.toString() == selectedProjectId);

      return Column(
        children: [
          if (selectedProj != null) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.rocket_launch_rounded, size: 16, color: AppTheme.primaryLight),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text.rich(
                      TextSpan(
                        children: [
                          const TextSpan(
                            text: 'Dự án đang kích hoạt: ',
                            style: TextStyle(fontSize: 12.5, color: Colors.white70),
                          ),
                          TextSpan(
                            text: selectedProj['title']?.toString() ?? 'Dự án',
                            style: const TextStyle(
                                fontSize: 12.5, fontWeight: FontWeight.bold, color: AppTheme.primaryLight),
                          ),
                          if (selectedProj['phase'] != null)
                            TextSpan(
                              text: ' • Giai đoạn: ${selectedProj['phase']}',
                              style: const TextStyle(fontSize: 12, color: Colors.amberAccent),
                            ),
                        ],
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
          Row(
            children: [
              _buildKpiCard(
                'Điểm thực thi chu kỳ',
                hasExecutionData ? formatPercent(summary['execution_score_pct']) : '—',
                Icons.speed_rounded,
                Colors.blueAccent,
                hint: hasExecutionData
                    ? '${summary['commitments_completed'] ?? 0}/${summary['total_commitments'] ?? 0} cam kết hoàn thành'
                    : 'Chưa có chu kỳ nào',
              ),
              const SizedBox(width: 12),
              _buildKpiCard(
                'Chiến dịch đang chạy',
                '${summary['active_campaigns_count'] ?? 0}',
                Icons.campaign_outlined,
                Colors.purpleAccent,
                hint: 'Tổng ${controller.campaigns.length} chiến dịch',
              ),
              const SizedBox(width: 12),
              _buildKpiCard(
                'Thử nghiệm đang chạy',
                '${summary['running_experiments_count'] ?? 0}',
                Icons.science_outlined,
                Colors.amberAccent,
                hint: 'Nhịp học ${summary['experiment_velocity_per_week'] ?? 0}/tuần',
              ),
              const SizedBox(width: 12),
              _buildKpiCard(
                'Chờ phê duyệt',
                '${summary['pending_approvals_count'] ?? 0}',
                Icons.approval_rounded,
                Colors.deepOrangeAccent,
                hint: 'Hành động ra bên ngoài cần người duyệt',
              ),
            ],
          ),
        ],
      );
    });
  }

  Widget _buildKpiCard(String title, String value, IconData icon, Color color, {String? hint}) {
    return Expanded(
      child: MarketingCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Icon(icon, color: color, size: 20),
              ],
            ),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
            if (hint != null) ...[
              const SizedBox(height: 4),
              Text(
                hint,
                style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
