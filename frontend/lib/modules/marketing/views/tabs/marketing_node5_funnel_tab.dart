import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../dialogs/extract_interview_dialog.dart';
import '../widgets/marketing_common.dart';

/// Node 5: Thu thập Khách hàng & CRM (Phễu 8 Giai đoạn & Evidence Store)
class MarketingNode5FunnelTab extends GetView<MarketingController> {
  const MarketingNode5FunnelTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final interviews = controller.customerInterviews;

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
                  const Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.filter_alt_rounded, size: 14),
                        SizedBox(width: 8),
                        Text('Phễu 8 Giai đoạn'),
                      ],
                    ),
                  ),
                  Tab(
                    height: 32,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.record_voice_over_rounded, size: 14),
                        const SizedBox(width: 8),
                        Text('Customer Evidence Store (${interviews.length})'),
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
                  _buildFunnelStagesView(),
                  _buildCustomerEvidenceStoreView(context, interviews),
                ],
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildCustomerEvidenceStoreView(BuildContext context, List<dynamic> interviews) {
    void openExtractDialog() {
      Get.dialog<void>(
        ExtractInterviewDialog(
          onExtract: (transcript, name, segment, saveToDb) {
            controller.extractInterviewAI(transcript, customerName: name, segment: segment, saveToDb: saveToDb);
          },
        ),
      );
    }

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Customer Evidence Store (§33 - §35) · ${interviews.length} cuộc phỏng vấn',
                style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            ElevatedButton.icon(
              onPressed: openExtractDialog,
              icon: const Icon(Icons.auto_awesome_rounded, size: 16),
              label: const Text('✨ AI Trích xuất Phỏng vấn'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.tealAccent.shade700,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (interviews.isEmpty)
          Expanded(
            child: MarketingEmpty(
              icon: Icons.record_voice_over_rounded,
              title: 'Chưa có ghi chú phỏng vấn khách hàng nào',
              subtitle: 'Nhập transcript cuộc gọi, phỏng vấn sâu hoặc phản hồi CSKH để AI tự động trích xuất '
                  'Pain Signals, Objections, Giá trị sẵn sàng trả và tự động liên kết Bằng chứng vào Giả định (§35).',
              action: ElevatedButton.icon(
                onPressed: openExtractDialog,
                icon: const Icon(Icons.auto_awesome_rounded, size: 18),
                label: const Text('AI Trích xuất Phỏng vấn'),
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
              itemCount: interviews.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final iv = interviews[index] as Map<String, dynamic>;
                final name = iv['customer_name']?.toString() ?? 'Khách hàng';
                final segment = iv['segment']?.toString() ?? 'ICP';
                final date = formatDate(iv['interview_date']?.toString());
                final quotes = (iv['quote_snippets'] as List<dynamic>?) ?? const [];
                final pains = (iv['pain_signals'] as List<dynamic>?) ?? const [];
                final objections = (iv['objection_signals'] as List<dynamic>?) ?? const [];
                final wtp = iv['willingness_to_pay_signals'];

                return MarketingCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: Colors.tealAccent.withValues(alpha: 0.2),
                            child: const Icon(Icons.person, size: 16, color: Colors.tealAccent),
                          ),
                          const SizedBox(width: 8),
                          Text(name,
                              style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13.5)),
                          const SizedBox(width: 8),
                          MarketingChip(label: segment, color: Colors.tealAccent),
                          const Spacer(),
                          Text(date, style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark)),
                        ],
                      ),
                      if (quotes.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        ...quotes.take(2).map((q) => Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Text(
                                '“$q”',
                                style:
                                    const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: Colors.white70),
                              ),
                            )),
                      ],
                      if (pains.isNotEmpty || objections.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          runSpacing: 4,
                          children: [
                            ...pains.map((p) => MarketingChip(label: '🔴 Pain: $p', color: Colors.redAccent)),
                            ...objections.map((o) => MarketingChip(label: '⚠️ Rào cản: $o', color: Colors.amberAccent)),
                            if (wtp != null) MarketingChip(label: '💵 WTP: $wtp', color: AppTheme.success),
                          ],
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          ),
      ],
    );
  }

  Widget _buildFunnelStagesView() {
    final stages = (controller.funnel['stages'] as List<dynamic>?) ?? const [];
    final bottleneck = controller.funnel['bottleneck'];
    final hasMetricData = controller.funnel['has_metric_data'] == true;
    final unmeasured = (controller.funnel['unmeasured_stages'] as List<dynamic>?) ?? const [];

    if (stages.isEmpty) {
      return const MarketingEmpty(
        icon: Icons.filter_alt_outlined,
        title: 'Chưa tải được phễu khách hàng',
        subtitle: 'Hãy thử tải lại dữ liệu.',
      );
    }

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MarketingCard(
            child: MarketingSectionHeader(
              title: 'Phễu 8 giai đoạn',
              description: hasMetricData
                  ? 'Tỷ lệ giữ lại chỉ tính giữa các bước đã có số đo; bước chưa gắn chỉ số được bỏ qua khi nối '
                      'chuỗi để không tạo ra nút thắt giả.'
                  : 'Chưa có chỉ số nào được ghi nhận nên phễu chỉ hiển thị cấu trúc và chiến dịch. '
                      'Hãy nhập chỉ số ở tab "Chỉ số" để hệ thống tính tỷ lệ chuyển đổi thật.',
            ),
          ),
          if (unmeasured.isNotEmpty) ...[
            const SizedBox(height: 10),
            MarketingCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.help_outline, size: 16, color: Colors.amberAccent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Chưa có số liệu cho bước: ${unmeasured.join(', ')}. Đây là khoảng trống đo lường, '
                      'cần bổ sung chỉ số chứ không phải vấn đề chuyển đổi.',
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark, height: 1.4),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          ...stages.asMap().entries.map((entry) {
            final stage = entry.value as Map<String, dynamic>;
            final isBottleneck = bottleneck is Map && bottleneck['stage_key'] == stage['key'];
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: MarketingCard(
                borderColor: isBottleneck ? Colors.amberAccent.withValues(alpha: 0.4) : null,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 26,
                          height: 26,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            '${entry.key + 1}',
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryLight),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Flexible(
                          child: Text(
                            stage['label']?.toString() ?? '',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                        ),
                        const SizedBox(width: 10),
                        if (isBottleneck)
                          const MarketingChip(
                              label: 'Nút thắt', color: Colors.amberAccent, icon: Icons.warning_amber_rounded),
                        const Spacer(),
                        Flexible(
                          child: Text(
                            stage['value'] == null
                                ? 'Chưa có số liệu'
                                : '${formatNumber(stage['value'])} · giữ lại ${formatPercent(stage['step_conversion_pct'])}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            textAlign: TextAlign.end,
                            style: TextStyle(
                              fontSize: 12,
                              color: stage['value'] == null ? Colors.white24 : AppTheme.textMutedDark,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      stage['goal']?.toString() ?? '',
                      style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.4),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        MarketingChip(
                          label: '${stage['campaign_count'] ?? 0} chiến dịch',
                          color: AppTheme.primaryLight,
                          icon: Icons.campaign_outlined,
                        ),
                        MarketingChip(
                          label: '${stage['experiment_count'] ?? 0} thử nghiệm',
                          color: AppTheme.secondaryLight,
                          icon: Icons.science_outlined,
                        ),
                        MarketingChip(
                          label: 'Ngân sách ${formatNumber(stage['budget'])}',
                          color: Colors.white70,
                          icon: Icons.account_balance_wallet_outlined,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
