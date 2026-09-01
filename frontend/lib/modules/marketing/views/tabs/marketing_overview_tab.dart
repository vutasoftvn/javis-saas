import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';

class MarketingOverviewTab extends StatelessWidget {
  const MarketingOverviewTab({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<MarketingController>();

    return Obx(() {
      final summary = controller.cockpitSummary;
      final analytics = controller.analytics;
      final anomalies = (analytics['anomalies'] as List<dynamic>?) ?? const [];
      final bottleneck = controller.funnel['bottleneck'];

      return SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            MarketingCard(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const MarketingSectionHeader(
                    title: 'Khung quản trị Marketing khép kín',
                    description:
                        'COSA giữ chiến lược, bối cảnh, bộ nhớ và quyền hạn. Các bộ kỹ năng bên ngoài chỉ đóng vai '
                        'nhà cung cấp năng lực; Python lo phần định lượng; con người giữ quyền phê duyệt.',
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      _buildStatPill('Mục tiêu Marketing', '${summary['marketing_objectives_count'] ?? 0}', Icons.flag_outlined),
                      _buildStatPill('Bài học đã ghi', '${summary['learnings_count'] ?? 0}', Icons.psychology_outlined),
                      _buildStatPill('Chỉ số theo dõi', '${controller.metrics.length}', Icons.insights_outlined),
                      _buildStatPill('Năng lực khả dụng', '${controller.skills.length}', Icons.auto_awesome_outlined),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _buildScorecardCard(summary),
            const SizedBox(height: 12),
            if (bottleneck is Map)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: MarketingCard(
                  borderColor: Colors.amberAccent.withValues(alpha: 0.35),
                  child: Row(
                    children: [
                      const Icon(Icons.filter_alt_outlined, color: Colors.amberAccent, size: 22),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Nút thắt của phễu',
                                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                            const SizedBox(height: 4),
                            Text(
                              'Bước "${bottleneck['stage_label']}" chỉ giữ lại ${formatPercent(bottleneck['step_conversion_pct'])} '
                              'so với bước trước. Đây là nơi nên ưu tiên thử nghiệm tối ưu.',
                              style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5, height: 1.45),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            if (anomalies.isNotEmpty) _buildAnomalyCard(anomalies),
          ],
        ),
      );
    });
  }

  Widget _buildStatPill(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppTheme.primaryLight),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark)),
          const SizedBox(width: 8),
          Text(value, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.bold, color: Colors.white)),
        ],
      ),
    );
  }

  Widget _buildScorecardCard(Map<String, dynamic> summary) {
    final hasData = summary['has_execution_data'] == true;
    final cycle = summary['cycle'];

    return MarketingCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          MarketingSectionHeader(
            title: 'Bảng điểm 12 tuần',
            description: cycle is Map
                ? 'Chu kỳ: ${cycle['theme'] ?? 'Không đặt tên'} · ${formatDate(cycle['start_date']?.toString())} → ${formatDate(cycle['end_date']?.toString())}'
                : 'Chưa gắn với chu kỳ 12 tuần nào trong module Chiến lược.',
          ),
          const SizedBox(height: 16),
          if (!hasData)
            const Text(
              'Chưa có cam kết tuần nào để chấm điểm thực thi. Hãy tạo chu kỳ 12 tuần và cam kết hàng tuần '
              'ở module Chiến lược & OKRs; điểm số sẽ được tính từ dữ liệu thật thay vì ước lượng.',
              style: TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.5),
            )
          else ...[
            _buildScoreRow('Điểm thực thi', summary['execution_score_pct'], Colors.blueAccent),
            const SizedBox(height: 14),
            _buildScoreRow('Điểm KPI kết quả', summary['lag_kpi_score_pct'], AppTheme.secondary),
            const SizedBox(height: 14),
            Row(
              children: [
                const Text('Nhịp thử nghiệm', style: TextStyle(fontSize: 13, color: Colors.white)),
                const Spacer(),
                Text(
                  '${summary['experiment_velocity_per_week'] ?? 0} thử nghiệm/tuần · tuần thứ ${summary['weeks_elapsed'] ?? 0}',
                  style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildScoreRow(String label, dynamic value, Color color) {
    final percent = (value is num) ? value.toDouble() : 0.0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(label, style: const TextStyle(fontSize: 13, color: Colors.white)),
            const Spacer(),
            Text(formatPercent(percent),
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color)),
          ],
        ),
        const SizedBox(height: 6),
        MarketingProgressBar(percent: percent, color: color),
      ],
    );
  }

  Widget _buildAnomalyCard(List<dynamic> anomalies) {
    return MarketingCard(
      borderColor: AppTheme.accent.withValues(alpha: 0.3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const MarketingSectionHeader(
            title: 'Cảnh báo biến động chỉ số',
            description: 'Chỉ số lệch từ 20% so với lần ghi nhận trước - đầu vào để chẩn đoán và điều chỉnh.',
          ),
          const SizedBox(height: 12),
          ...anomalies.map((a) {
            final up = a['direction'] == 'up';
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Icon(up ? Icons.trending_up : Icons.trending_down,
                      color: up ? Colors.greenAccent : AppTheme.accent, size: 18),
                  const SizedBox(width: 8),
                  Text('${a['metric_name']}', style: const TextStyle(color: Colors.white, fontSize: 13)),
                  const Spacer(),
                  Text(
                    '${a['current_value']} (${up ? '+' : ''}${formatPercent(a['change_pct'])})',
                    style: TextStyle(
                        color: up ? Colors.greenAccent : AppTheme.accent,
                        fontSize: 12.5,
                        fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
