import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../dialogs/complete_experiment_dialog.dart';
import '../dialogs/experiment_designer_dialog.dart';
import '../dialogs/scale_warning_dialog.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

/// Node 6: Đo lường & Vòng lặp Học hỏi (Learnings/Playbooks/Decisions, Experiments, Metrics)
class MarketingNode6LearningTab extends GetView<MarketingController> {
  const MarketingNode6LearningTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MarketingSubTabBar(
            current: controller.learningSubTab.value,
            items: const [
              {'key': 'overview', 'label': 'Bài học & Playbooks', 'icon': Icons.psychology_rounded},
              {'key': 'experiments', 'label': 'Thử nghiệm kiểm chứng', 'icon': Icons.science_rounded},
              {'key': 'metrics', 'label': 'Chỉ số & Phân bổ', 'icon': Icons.insights_rounded},
            ],
            onSelect: (k) => controller.learningSubTab.value = k,
          ),
          const SizedBox(height: 10),
          Expanded(
            child: _buildSubTabContent(context, controller.learningSubTab.value),
          ),
        ],
      );
    });
  }

  Widget _buildSubTabContent(BuildContext context, String currentTab) {
    switch (currentTab) {
      case 'experiments':
        return _buildExperimentsTab(context);
      case 'metrics':
        return _buildMetricsTab(context);
      case 'overview':
      default:
        return _buildLearningsTab(context);
    }
  }

  // ==========================================
  // SubTab: Bài học & Quyết định (§15, §53)
  // ==========================================

  Widget _buildLearningsTab(BuildContext context) {
    final learnings = controller.learnings;
    final playbooks = controller.playbooks;
    final decisions = controller.decisions;

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Bài học (${learnings.length}) · Quyết định (${decisions.length})',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            OutlinedButton.icon(
              onPressed: () => showDecisionForm(context, controller),
              icon: const Icon(Icons.history_edu_outlined, size: 16),
              label: const Text('Ghi nhật ký quyết định (§53)'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.amberAccent,
                side: const BorderSide(color: Colors.amberAccent),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () => showLearningForm(context, controller),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Ghi bài học'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView(
            children: [
              // 1. Nhật ký Quyết định (Decision Journal §53)
              if (decisions.isNotEmpty) ...[
                MarketingCard(
                  borderColor: Colors.amberAccent.withValues(alpha: 0.3),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const MarketingSectionHeader(
                        title: 'Nhật ký Quyết định Chiến lược (Decision Journal §53)',
                        description:
                            'Lưu vết ngữ cảnh, lý do ra quyết định và bài học thực tế để phòng tránh thiên kiến nhận thức.',
                      ),
                      const SizedBox(height: 12),
                      ...decisions.map((raw) {
                        final d = raw as Map<String, dynamic>;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.03),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    if (d['decision_id'] != null) ...[
                                      MarketingChip(label: d['decision_id'].toString(), color: Colors.amberAccent),
                                      const SizedBox(width: 8),
                                    ],
                                    Expanded(
                                      child: Text(
                                        d['title']?.toString() ?? d['question']?.toString() ?? 'Quyết định chiến lược',
                                        style: const TextStyle(
                                            fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13.5),
                                      ),
                                    ),
                                    Text(
                                      formatDate(d['created_at']?.toString()),
                                      style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                                    ),
                                  ],
                                ),
                                if ((d['question']?.toString() ?? '').isNotEmpty && d['title'] != d['question']) ...[
                                  const SizedBox(height: 6),
                                  Text('❓ Câu hỏi: ${d['question']}',
                                      style: const TextStyle(fontSize: 12.5, color: Colors.white70)),
                                ],
                                const SizedBox(height: 6),
                                MarketingKeyValue(label: '👉 Quyết định', value: d['decision']?.toString() ?? '—'),
                                if ((d['reason']?.toString() ?? '').isNotEmpty)
                                  MarketingKeyValue(label: '💡 Căn cứ / Lý do', value: d['reason'].toString()),
                                if ((d['next_action']?.toString() ?? '').isNotEmpty)
                                  MarketingKeyValue(
                                      label: '🚀 Hành động tiếp theo', value: d['next_action'].toString()),
                                if ((d['actual_outcome']?.toString() ?? '').isNotEmpty)
                                  MarketingKeyValue(label: 'Kết quả thực tế', value: d['actual_outcome'].toString()),
                                if ((d['learning']?.toString() ?? '').isNotEmpty)
                                  MarketingKeyValue(label: 'Bài học rút ra', value: d['learning'].toString()),
                              ],
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
              ],

              if (playbooks.isNotEmpty) ...[
                MarketingCard(
                  borderColor: AppTheme.secondary.withValues(alpha: 0.3),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const MarketingSectionHeader(
                        title: 'Luật tái sử dụng đã kiểm chứng',
                        description: 'Bài học đã chốt thành quy tắc vận hành - dùng lại cho các chiến dịch sau.',
                      ),
                      const SizedBox(height: 12),
                      ...playbooks.map((raw) {
                        final p = raw as Map<String, dynamic>;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.rule, size: 15, color: AppTheme.secondaryLight),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(p['rule']?.toString() ?? '',
                                    style: const TextStyle(fontSize: 12.5, color: Colors.white70, height: 1.4)),
                              ),
                              MarketingChip(
                                label: 'Tin cậy ${MarketingLabels.confidence[p['confidence']] ?? p['confidence']}',
                                color: AppTheme.secondaryLight,
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],

              ...learnings.map((raw) {
                final l = raw as Map<String, dynamic>;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: MarketingCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(l['learning']?.toString() ?? '',
                                  style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13.5,
                                      height: 1.4)),
                            ),
                            MarketingChip(
                              label: 'Tin cậy ${MarketingLabels.confidence[l['confidence']] ?? l['confidence']}',
                              color: l['confidence'] == 'high' ? AppTheme.success : AppTheme.textMutedDark,
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        MarketingKeyValue(label: 'Quan sát', value: l['observation']?.toString() ?? '—'),
                        MarketingKeyValue(label: 'Hành động', value: l['action']?.toString() ?? '—'),
                        MarketingKeyValue(label: 'Kết quả', value: l['result']?.toString() ?? '—'),
                        Text('Ghi nhận ${formatDate(l['created_at']?.toString())}',
                            style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark)),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
      ],
    );
  }

  // ==========================================
  // SubTab: Thử nghiệm (§27)
  // ==========================================

  Widget _buildExperimentsTab(BuildContext context) {
    final experiments = controller.experiments;

    void openAIDesigner() {
      Get.dialog<void>(
        ExperimentDesignerDialog(
          assumptions: controller.assumptions,
          onAIDesign: (asmId) => controller.designSmallestExperimentAI(asmId),
          onSave: (data) async {
            // Check scale warning if assumption is selected
            if (data['assumption_id'] != null) {
              final warning = await controller.checkScaleWarning(data['assumption_id'].toString());
              if (warning['should_warn'] == true && context.mounted) {
                Get.dialog<void>(
                  ScaleWarningDialog(
                    title: warning['warning_title'] ?? 'Cảnh báo Quy mô',
                    message: warning['message'] ?? '',
                    recommendation: warning['recommendation'] ?? '',
                    recommendedAction: warning['recommended_action'] ?? '',
                    onValidateFirst: () {
                      Get.back<void>();
                      controller.createExperiment(data);
                    },
                    onContinueAnyway: () {
                      Get.back<void>();
                      controller.createExperiment(data);
                    },
                  ),
                );
                return;
              }
            }
            controller.createExperiment(data);
          },
        ),
      );
    }

    if (experiments.isEmpty) {
      return MarketingEmpty(
        icon: Icons.science_outlined,
        title: 'Chưa có thử nghiệm nào',
        subtitle:
            'Marketing OS chuyển từ "AI đưa lời khuyên" sang "AI đề xuất giả thuyết → đo lường → quyết định" (§27).',
        action: ElevatedButton.icon(
          onPressed: openAIDesigner,
          icon: const Icon(Icons.auto_awesome_rounded, size: 18),
          label: const Text('✨ AI Thiết kế Thử nghiệm Tối thiểu'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      );
    }

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Thử nghiệm Kiểm chứng (${experiments.length})',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            OutlinedButton.icon(
              onPressed: openAIDesigner,
              icon: const Icon(Icons.auto_awesome_rounded, size: 15, color: AppTheme.primaryLight),
              label: const Text('✨ AI Thiết kế Thử nghiệm Nhỏ nhất'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.primaryLight,
                side: BorderSide(color: AppTheme.primaryLight.withValues(alpha: 0.5)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () => showExperimentForm(context, controller),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Tạo thủ công'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: experiments.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final e = experiments[index] as Map<String, dynamic>;
              final status = e['status']?.toString() ?? 'running';
              final evaluation = e['evaluation'];
              final method = e['method']?.toString() ?? 'ab_test';
              final threshold = e['success_threshold']?.toString();
              final timebox = e['timebox_days']?.toString();

              return MarketingCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        MarketingChip(label: method.toUpperCase(), color: Colors.indigoAccent),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(e['hypothesis']?.toString() ?? '',
                              style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14)),
                        ),
                        MarketingChip(
                          label: MarketingLabels.experiment(status),
                          color: MarketingLabels.experimentColor(status),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (e['variant_a'] != null || e['variant_b'] != null) ...[
                      Row(
                        children: [
                          Expanded(
                            child: _buildVariantBox('Phương án A (đối chứng)', e['variant_a']?.toString() ?? ''),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _buildVariantBox('Phương án B (thử nghiệm)', e['variant_b']?.toString() ?? ''),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                    ],
                    Row(
                      children: [
                        Text(
                          'Chỉ số: ${e['metric'] ?? 'conversion_rate'}'
                          '${threshold != null ? ' · Ngưỡng: $threshold' : ''}'
                          '${timebox != null ? ' · Thời hạn: ${timebox}d' : ''}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                        ),
                      ],
                    ),
                    if (evaluation is Map) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.04),
                          borderRadius: BorderRadius.circular(9),
                        ),
                        child: Text(
                          'Kết quả kiểm định: chênh lệch ${evaluation['uplift_pct']}% · z = ${evaluation['z_score']} · '
                          'p = ${evaluation['p_value']} · ${evaluation['statistically_significant'] == true ? 'có ý nghĩa thống kê' : 'chưa có ý nghĩa thống kê'}',
                          style: const TextStyle(fontSize: 12, color: Colors.white70, height: 1.4),
                        ),
                      ),
                    ],
                    if ((e['learning']?.toString() ?? '').isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text('Bài học: ${e['learning']}',
                          style: const TextStyle(fontSize: 12.5, color: AppTheme.secondaryLight, height: 1.4)),
                    ],
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        ElevatedButton.icon(
                          onPressed: () {
                            Get.dialog<void>(
                              CompleteExperimentDialog(
                                experiment: e,
                                onComplete: (conclusion, learning, observations) {
                                  controller.completeValidationExperiment(
                                    e['id'].toString(),
                                    conclusion,
                                    learning,
                                    observations,
                                  );
                                },
                              ),
                            );
                          },
                          icon: const Icon(Icons.check_circle_outline_rounded, size: 15),
                          label: const Text('Hoàn tất & Ghi nhận Evidence', style: TextStyle(fontSize: 12)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.success,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          ),
                        ),
                        const SizedBox(width: 8),
                        TextButton.icon(
                          onPressed: () => showExperimentEvaluateForm(context, controller, e),
                          icon: const Icon(Icons.calculate_outlined, size: 15),
                          label: const Text('Đánh giá', style: TextStyle(fontSize: 12.5)),
                          style: TextButton.styleFrom(foregroundColor: AppTheme.primaryLight),
                        ),
                        TextButton.icon(
                          onPressed: () => showExperimentDecisionForm(context, controller, e),
                          icon: const Icon(Icons.gavel_outlined, size: 15),
                          label: const Text('Chốt quyết định', style: TextStyle(fontSize: 12.5)),
                          style: TextButton.styleFrom(foregroundColor: AppTheme.secondaryLight),
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

  Widget _buildVariantBox(String label, String content) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 11, color: AppTheme.primaryLight, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(content,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12.5, color: Colors.white70, height: 1.35)),
        ],
      ),
    );
  }

  // ==========================================
  // SubTab: Chỉ số & Phân bổ (§14, §28)
  // ==========================================

  Widget _buildMetricsTab(BuildContext context) {
    final analytics = controller.analytics;
    final derived = (analytics['derived'] as Map<String, dynamic>?) ?? const {};
    final missing = (analytics['missing_inputs'] as List<dynamic>?) ?? const [];
    final metrics = controller.metrics;
    final attribution = controller.attributionResult;

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Chỉ số Marketing (${metrics.length})',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            OutlinedButton.icon(
              onPressed: () => showAttributionDialog(context, controller),
              icon: const Icon(Icons.pie_chart_outline_rounded, size: 16),
              label: const Text('Phân tích phân bổ (§28)'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.purpleAccent,
                side: const BorderSide(color: Colors.purpleAccent),
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () => showMetricForm(context, controller),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Ghi nhận chỉ số'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Card kết quả phân bổ nếu có
                if (attribution.isNotEmpty) ...[
                  MarketingCard(
                    borderColor: Colors.purpleAccent.withValues(alpha: 0.4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.auto_graph_rounded, color: Colors.purpleAccent, size: 20),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text(
                                'Kết quả Phân bổ Đa chạm (Attribution Engine §28)',
                                style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14),
                              ),
                            ),
                            MarketingChip(
                              label: 'Mô hình: ${attribution['model_type'] ?? ''}',
                              color: Colors.purpleAccent,
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        if (attribution['channel_attribution'] is Map) ...[
                          const Text('Đóng góp theo kênh:',
                              style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                          const SizedBox(height: 6),
                          ...(attribution['channel_attribution'] as Map).entries.map((e) {
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 2),
                              child: Row(
                                children: [
                                  Text(e.key.toString(), style: const TextStyle(fontSize: 13, color: Colors.white70)),
                                  const Spacer(),
                                  Text('\$${formatNumber(e.value, decimals: 2)}',
                                      style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.purpleAccent)),
                                ],
                              ),
                            );
                          }),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                ],

                MarketingCard(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const MarketingSectionHeader(
                        title: 'Chỉ số suy ra (tính bằng Python)',
                        description:
                            'Không dùng AI để tính KPI. Mọi con số dưới đây là kết quả tính toán tất định '
                            'từ các chỉ số bạn đã ghi nhận.',
                      ),
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: [
                          _buildDerivedTile('CTR', derived['ctr'], '%'),
                          _buildDerivedTile('CPC', derived['cpc'], ''),
                          _buildDerivedTile('CPL', derived['cpl'], ''),
                          _buildDerivedTile('CAC', derived['cac'], ''),
                          _buildDerivedTile('Tỷ lệ chuyển đổi', derived['cvr'], '%'),
                          _buildDerivedTile('ROAS', derived['roas'], 'x'),
                          _buildDerivedTile('ARPU', derived['arpu'], ''),
                          _buildDerivedTile('LTV', derived['ltv'], ''),
                          _buildDerivedTile('LTV/CAC', derived['ltv_cac_ratio'], 'x'),
                          _buildDerivedTile('Hoàn vốn', derived['payback_months'], ' tháng'),
                        ],
                      ),
                      if (missing.isNotEmpty) ...[
                        const SizedBox(height: 14),
                        Text(
                          'Chưa có dữ liệu đầu vào: ${missing.join(', ')}. Các chỉ số phụ thuộc sẽ hiển thị 0 cho tới khi được ghi nhận.',
                          style: const TextStyle(fontSize: 12, color: Colors.amberAccent, height: 1.45),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (metrics.isEmpty)
                  const MarketingCard(
                    child: Text(
                      'Chưa có chỉ số nào được ghi nhận. Hãy nhập các chỉ số nền như ad_spend, revenue, '
                      'new_customers, active_customers, churn_rate để hệ thống tính CAC, LTV, ROAS và phát hiện bất thường.',
                      style: TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.5),
                    ),
                  )
                else
                  ...metrics.map((raw) {
                    final m = raw as Map<String, dynamic>;
                    final change = (m['change_pct'] is num) ? (m['change_pct'] as num).toDouble() : 0.0;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: MarketingCard(
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(m['metric_name']?.toString() ?? '',
                                      style: const TextStyle(
                                          color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13.5)),
                                  const SizedBox(height: 3),
                                  Text(
                                    '${MarketingLabels.metricCategory[m['category']] ?? m['category']} · cập nhật ${formatDate(m['updated_at']?.toString())}',
                                    style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                                  ),
                                ],
                              ),
                            ),
                            Text(formatNumber(m['current_value'], decimals: 2),
                                style:
                                    const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                            const SizedBox(width: 10),
                            MarketingChip(
                              label: '${change > 0 ? '+' : ''}${formatNumber(change, decimals: 1)}%',
                              color: change > 0
                                  ? AppTheme.success
                                  : (change < 0 ? AppTheme.accent : AppTheme.textMutedDark),
                            ),
                            IconButton(
                              tooltip: 'Cập nhật giá trị',
                              icon: const Icon(Icons.edit_outlined, size: 17, color: AppTheme.textMutedDark),
                              onPressed: () => showMetricForm(context, controller, existing: m),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDerivedTile(String label, dynamic value, String suffix) {
    return Container(
      width: 168,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark)),
          const SizedBox(height: 6),
          Text('${formatNumber(value, decimals: 2)}$suffix',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
        ],
      ),
    );
  }
}
