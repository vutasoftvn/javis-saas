import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'marketing_common.dart';

class MarketingKpiHeader extends StatelessWidget {
  final Map<String, dynamic> summary;
  final int totalCampaigns;

  const MarketingKpiHeader({
    super.key,
    required this.summary,
    required this.totalCampaigns,
  });

  @override
  Widget build(BuildContext context) {
    final hasExecutionData = summary['has_execution_data'] == true;

    return Row(
      children: [
        _buildKpiCard(
          'Điểm thực thi 12 tuần',
          hasExecutionData ? formatPercent(summary['execution_score_pct']) : '—',
          Icons.speed_rounded,
          Colors.blueAccent,
          hint: hasExecutionData
              ? '${summary['commitments_completed'] ?? 0}/${summary['total_commitments'] ?? 0} cam kết hoàn thành'
              : 'Chưa có chu kỳ 12 tuần nào',
        ),
        const SizedBox(width: 12),
        _buildKpiCard(
          'Chiến dịch đang chạy',
          '${summary['active_campaigns_count'] ?? 0}',
          Icons.campaign_outlined,
          Colors.purpleAccent,
          hint: 'Tổng $totalCampaigns chiến dịch',
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
    );
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
