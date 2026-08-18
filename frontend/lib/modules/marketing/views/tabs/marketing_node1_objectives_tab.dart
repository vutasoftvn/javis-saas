import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/criticality_meter.dart';
import '../widgets/epistemic_badge.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

/// Node 1: Founder Giao việc & Kích hoạt (OKRs & Giả định/Rủi ro)
class MarketingNode1ObjectivesTab extends GetView<MarketingController> {
  const MarketingNode1ObjectivesTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final objectives = controller.objectives;
      final assumptions = controller.assumptions;
      final summary = controller.assumptionsSummary;

      return DefaultTabController(
        length: 2,
        child: Column(
          children: [
            Container(
              height: 38,
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: TabBar(
                indicator: BoxDecoration(
                  color: AppTheme.primary,
                  borderRadius: BorderRadius.circular(7),
                ),
                indicatorSize: TabBarIndicatorSize.tab,
                dividerColor: Colors.transparent,
                padding: EdgeInsets.zero,
                labelPadding: EdgeInsets.zero,
                labelColor: const Color(0xFF04070E),
                unselectedLabelColor: AppTheme.textMutedDark,
                labelStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
                unselectedLabelStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500),
                tabs: [
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.flag_rounded, size: 14),
                        const SizedBox(width: 8),
                        Text('Mục tiêu OKRs (${objectives.length})'),
                      ],
                    ),
                  ),
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.lightbulb_outline_rounded, size: 14),
                        const SizedBox(width: 8),
                        Text('Giả định & Rủi ro (${assumptions.length})'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: TabBarView(
                children: [
                  _buildOkrsSubTab(context, objectives),
                  _buildAssumptionsSubTab(context, assumptions, summary),
                ],
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildOkrsSubTab(BuildContext context, List<dynamic> objectives) {
    if (objectives.isEmpty) {
      return MarketingEmpty(
        icon: Icons.flag_outlined,
        title: 'Chưa có mục tiêu Marketing nào',
        subtitle:
            'Mục tiêu Marketing nên bắt nguồn từ mục tiêu chiến lược của công ty, ví dụ "MRR +30%" sẽ dẫn tới "300 lead đủ điều kiện trong 12 tuần".',
        action: ElevatedButton.icon(
          onPressed: () => showObjectiveForm(context, controller),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Thêm mục tiêu'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      );
    }

    return Column(
      children: [
        MarketingTabActionBar(
          title: 'Mục tiêu Marketing (${objectives.length})',
          actionLabel: 'Thêm mục tiêu',
          onAction: () => showObjectiveForm(context, controller),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: objectives.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final o = objectives[index] as Map<String, dynamic>;
              final progress = (o['progress_pct'] is num) ? (o['progress_pct'] as num).toDouble() : 0.0;
              return MarketingCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            o['title']?.toString() ?? '',
                            style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14.5),
                          ),
                        ),
                        MarketingChip(
                          label: o['status'] == 'active' ? 'Đang theo dõi' : (o['status']?.toString() ?? '—'),
                          color: o['status'] == 'active' ? AppTheme.success : AppTheme.textMutedDark,
                        ),
                        IconButton(
                          tooltip: 'Sửa',
                          icon: const Icon(Icons.edit_outlined, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => showObjectiveForm(context, controller, existing: o),
                        ),
                        IconButton(
                          tooltip: 'Xoá',
                          icon: const Icon(Icons.delete_outline, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => confirmMarketingDelete(
                            context,
                            'Xoá mục tiêu?',
                            o['title']?.toString() ?? '',
                            () => controller.deleteObjective(o['id'].toString()),
                          ),
                        ),
                      ],
                    ),
                    if ((o['description']?.toString() ?? '').isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        o['description'].toString(),
                        style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.4),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Text('Chỉ số: ${o['target_metric']}',
                            style: const TextStyle(fontSize: 12.5, color: AppTheme.primaryLight)),
                        const Spacer(),
                        Text(
                          '${formatNumber(o['current_value'], decimals: 1)} / ${formatNumber(o['target_value'], decimals: 1)} ${o['unit'] ?? ''}',
                          style: const TextStyle(fontSize: 12.5, color: Colors.white70),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          formatPercent(progress),
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    MarketingProgressBar(percent: progress),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildAssumptionsSubTab(BuildContext context, List<dynamic> assumptions, Map<String, dynamic> summary) {
    final criticalUntested = summary['critical_untested_count'] ?? 0;

    return Column(
      children: [
        // Summary & Actions Bar
        Row(
          children: [
            Expanded(
              child: Text(
                'Danh mục Giả định Trọng yếu (${assumptions.length}) · $criticalUntested rủi ro cao chưa đo',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white),
              ),
            ),
            OutlinedButton.icon(
              onPressed: () => showExtractAssumptionsDialog(context, controller),
              icon: const Icon(Icons.auto_awesome_rounded, size: 15, color: AppTheme.primaryLight),
              label: const Text('✨ AI Trích xuất Giả định'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.primaryLight,
                side: BorderSide(color: AppTheme.primaryLight.withValues(alpha: 0.5)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () => showCreateAssumptionDialog(context, controller),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Thêm Giả định'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        if (assumptions.isEmpty)
          Expanded(
            child: MarketingEmpty(
              icon: Icons.lightbulb_outline_rounded,
              title: 'Chưa có Giả định nào được khai báo',
              subtitle: 'Mọi chiến dịch marketing đều bắt đầu từ các giả định chưa được kiểm chứng. '
                  'Hãy dùng nút "AI Trích xuất Giả định" để phân tích brief hoặc tự thêm giả định.',
              action: ElevatedButton.icon(
                onPressed: () => showExtractAssumptionsDialog(context, controller),
                icon: const Icon(Icons.auto_awesome_rounded, size: 18),
                label: const Text('AI Trích xuất Giả định'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                ),
              ),
            ),
          )
        else
          Expanded(
            child: ListView.separated(
              itemCount: assumptions.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final a = assumptions[index] as Map<String, dynamic>;
                final statement = a['statement']?.toString() ?? '';
                final category = a['category']?.toString() ?? 'customer';
                final status = a['status']?.toString() ?? 'untested';
                final criticality = (a['criticality'] is num) ? (a['criticality'] as num).toInt() : 9;
                final impact = (a['impact'] is num) ? (a['impact'] as num).toInt() : 3;
                final uncertainty = (a['uncertainty'] is num) ? (a['uncertainty'] as num).toInt() : 3;
                final evidenceCount = a['evidence_count'] ??
                    (a['supporting_evidence_ids'] is List ? (a['supporting_evidence_ids'] as List).length : 0);

                return MarketingCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    MarketingChip(label: category.toUpperCase(), color: Colors.blueGrey),
                                    const SizedBox(width: 8),
                                    EpistemicBadge(status: status, isCompact: true),
                                    const SizedBox(width: 8),
                                    CriticalityMeter(
                                        score: criticality, impact: impact, uncertainty: uncertainty, showFormula: true),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  statement,
                                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13.5),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            tooltip: 'Ghi nhận Bằng chứng (Evidence)',
                            icon: const Icon(Icons.add_task_rounded, size: 18, color: AppTheme.primaryLight),
                            onPressed: () => showAddEvidenceDialog(context, controller, a['id'].toString()),
                          ),
                          IconButton(
                            tooltip: 'Sửa',
                            icon: const Icon(Icons.edit_outlined, size: 17, color: AppTheme.textMutedDark),
                            onPressed: () => showCreateAssumptionDialog(context, controller, existing: a),
                          ),
                          IconButton(
                            tooltip: 'Xoá',
                            icon: const Icon(Icons.delete_outline, size: 17, color: AppTheme.textMutedDark),
                            onPressed: () => confirmMarketingDelete(
                              context,
                              'Xoá giả định?',
                              statement,
                              () => controller.deleteAssumption(a['id'].toString()),
                            ),
                          ),
                        ],
                      ),
                      if ((a['rationale']?.toString() ?? '').isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Căn cứ: ${a['rationale']}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                        ),
                      ],
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(Icons.inventory_2_outlined, size: 13, color: AppTheme.textMutedDark),
                          const SizedBox(width: 4),
                          Text(
                            '$evidenceCount bằng chứng liên kết',
                            style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                          ),
                          const Spacer(),
                          if (criticality >= 15 && status == 'untested')
                            const Text(
                              '⚠️ Cần thử nghiệm trước khi scale (§30)',
                              style: TextStyle(fontSize: 11.5, color: AppTheme.error, fontWeight: FontWeight.w600),
                            ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
      ],
    );
  }
}
