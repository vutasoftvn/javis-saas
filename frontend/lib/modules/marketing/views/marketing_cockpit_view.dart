import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/marketing_controller.dart';
import 'widgets/marketing_common.dart';
import 'widgets/marketing_forms.dart';

/// Marketing Cockpit - màn hình điều khiển vòng lặp khép kín của Marketing OS.
///
/// Toàn bộ nhãn hiển thị bằng tiếng Việt; chỉ giữ nguyên mã capability kiểu
/// `marketing.cro` vì đó là định danh kỹ thuật dùng chung với Skill Registry.
class MarketingCockpitView extends GetView<MarketingController> {
  const MarketingCockpitView({super.key});

  static const List<String> _tabLabels = [
    'Tổng quan',
    'Bối cảnh & Canvas',
    'Mục tiêu & Kế hoạch',
    'Phễu khách hàng',
    'Chiến dịch',
    'Vòng lặp tăng trưởng',
    'Thử nghiệm',
    'Chỉ số & Phân bổ',
    'Bài học & Quyết định',
    'Kho kỹ năng',
    'Phê duyệt',
  ];

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: _tabLabels.length,
      child: Column(
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
              return Column(
                children: [
                  _buildKpiHeader(),
                  const SizedBox(height: 12),
                  _buildPillTabBar(),
                  const SizedBox(height: 12),
                  Expanded(
                    child: TabBarView(
                      children: [
                        _buildOverviewTab(context),
                        _buildContextTab(context),
                        _buildObjectivesTab(context),
                        _buildFunnelTab(),
                        _buildCampaignsTab(context),
                        _buildLoopsTab(context),
                        _buildExperimentsTab(context),
                        _buildMetricsTab(context),
                        _buildLearningsTab(context),
                        _buildSkillsTab(context),
                        _buildApprovalsTab(context),
                      ],
                    ),
                  ),
                ],
              );
            }),
          ),
        ],
      ),
    );
  }


  Widget _buildFloatingAppBar(BuildContext context) {
    return JavisFloatingAppBar(
      title: 'Trung tâm điều hành Marketing',
      subtitle: 'Vòng lặp khép kín: Chiến lược → Thực thi → Đo lường → Học hỏi',
      icon: Icons.campaign_rounded,
      actions: [
        Obx(
          () => controller.isSubmitting.value
              ? const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12),
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
  // KPI header
  // ==========================================

  Widget _buildKpiHeader() {
    final summary = controller.cockpitSummary;
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

  Widget _buildPillTabBar() {
    return Container(
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
              color: AppTheme.primary.withValues(alpha: 0.35),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        labelColor: const Color(0xFF04070E),
        unselectedLabelColor: AppTheme.textMutedDark,
        labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
        unselectedLabelStyle: const TextStyle(fontSize: 13),
        dividerColor: Colors.transparent,
        padding: EdgeInsets.zero,
        labelPadding: const EdgeInsets.symmetric(horizontal: 14),
        tabs: _tabLabels.map((label) => Tab(height: 32, child: Center(child: Text(label)))).toList(),
      ),
    );
  }

  // ==========================================
  // Tab 1: Tổng quan
  // ==========================================

  Widget _buildOverviewTab(BuildContext context) {
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
                      'Javis giữ chiến lược, bối cảnh, bộ nhớ và quyền hạn. Các bộ kỹ năng bên ngoài chỉ đóng vai '
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
          const SizedBox(height: 12),
          _buildPendingApprovalPreview(context),
        ],
      ),
    );
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
                      size: 16, color: up ? Colors.orangeAccent : AppTheme.accent),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${a['metric_name']}: ${formatNumber(a['previous_value'], decimals: 2)} → ${formatNumber(a['current_value'], decimals: 2)}',
                      style: const TextStyle(fontSize: 12.5, color: Colors.white70),
                    ),
                  ),
                  MarketingChip(
                    label: '${up ? '+' : ''}${formatNumber(a['change_pct'], decimals: 1)}%',
                    color: up ? Colors.orangeAccent : AppTheme.accent,
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildPendingApprovalPreview(BuildContext context) {
    final approvals = controller.pendingApprovals;
    return MarketingCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const MarketingSectionHeader(
            title: 'Hành động đang chờ bạn duyệt',
            description: 'Xuất bản nội dung, chi ngân sách, đổi giá hay dừng chiến dịch đều cần con người quyết định.',
          ),
          const SizedBox(height: 12),
          if (approvals.isEmpty)
            const Text('Không có hành động nào đang chờ.',
                style: TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark))
          else
            ...approvals.take(3).map((a) => _buildApprovalRow(context, a as Map<String, dynamic>)),
        ],
      ),
    );
  }

  // ==========================================
  // Tab 2: Bối cảnh & Canvas Chiến lược (§7, §10, §11, §12)
  // ==========================================

  Widget _buildContextTab(BuildContext context) {
    final ctx = controller.marketingContext;
    final research = controller.customerResearch;
    final pm = controller.productMarketing;
    final offer = controller.offerArchitecture;

    String read(dynamic value) {
      if (value == null) return 'Chưa cấu hình';
      if (value is Map) {
        if (value['summary'] != null) return value['summary'].toString();
        if (value.isEmpty) return 'Chưa cấu hình';
        return value.entries.map((e) => '${e.key}: ${e.value}').join('\n');
      }
      if (value is List) {
        return value.isEmpty ? 'Chưa cấu hình' : value.map((e) => '• $e').join('\n');
      }
      final str = value.toString().trim();
      return str.isEmpty ? 'Chưa cấu hình' : str;
    }

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Customer Research Canvas (§10)
          MarketingCard(
            padding: const EdgeInsets.all(20),
            borderColor: Colors.blueAccent.withValues(alpha: 0.3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarketingSectionHeader(
                  title: '1. Nghiên cứu Khách hàng (Customer Research Canvas §10)',
                  description:
                      'Phân tích sâu ICP, Jobs-to-be-Done, rào cản và phân loại rõ Sự thật (FACT) vs Giả thuyết (HYPOTHESIS).',
                  action: ElevatedButton.icon(
                    onPressed: () => showCustomerResearchForm(context, controller),
                    icon: const Icon(Icons.edit_outlined, size: 16),
                    label: const Text('Cập nhật nghiên cứu'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                MarketingKeyValue(label: 'Phân khúc khách hàng mục tiêu', value: read(research['segments'])),
                MarketingKeyValue(label: 'Việc cần làm (Jobs-to-be-Done)', value: read(research['jtbd'])),
                MarketingKeyValue(label: 'Nỗi đau & Rào cản mua hàng', value: read(research['pains'])),
                MarketingKeyValue(label: 'Sự thật đã kiểm chứng (FACTS)', value: read(research['facts'])),
                MarketingKeyValue(label: 'Giả thuyết cần kiểm định (HYPOTHESES)', value: read(research['hypotheses'])),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 2. Product Marketing & Positioning (§11)
          MarketingCard(
            padding: const EdgeInsets.all(20),
            borderColor: Colors.purpleAccent.withValues(alpha: 0.3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarketingSectionHeader(
                  title: '2. Định vị Sản phẩm (Product Marketing Canvas §11)',
                  description:
                      'Xác định rõ Ngành hàng (Category), các giải pháp thay thế, điểm khác biệt độc bản và thông điệp.',
                  action: ElevatedButton.icon(
                    onPressed: () => showProductMarketingForm(context, controller),
                    icon: const Icon(Icons.edit_outlined, size: 16),
                    label: const Text('Cập nhật định vị'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                MarketingKeyValue(label: 'Ngành hàng (Category)', value: read(pm['category'] ?? ctx['category'])),
                MarketingKeyValue(label: 'Giải pháp thay thế hiện có', value: read(pm['alternatives'])),
                MarketingKeyValue(label: 'Điểm khác biệt độc bản (Differentiators)', value: read(pm['differentiators'])),
                MarketingKeyValue(label: 'Tuyên bố định vị (Positioning Statement)', value: read(pm['positioning_statement'] ?? ctx['positioning'])),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 3. Offer Architecture (§12)
          MarketingCard(
            padding: const EdgeInsets.all(20),
            borderColor: Colors.amberAccent.withValues(alpha: 0.3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarketingSectionHeader(
                  title: '3. Kiến trúc Ưu đãi (Offer Architecture Canvas §12)',
                  description:
                      'Thiết kế gói giá trị không thể chối từ: Core Offer + Value + Proof + Bonus + Guarantee + Urgency + CTA.',
                  action: ElevatedButton.icon(
                    onPressed: () => showOfferArchitectureForm(context, controller),
                    icon: const Icon(Icons.edit_outlined, size: 16),
                    label: const Text('Thiết kế ưu đãi'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                MarketingKeyValue(label: 'Ưu đãi cốt lõi (Core Offer)', value: read(offer['core_offer'])),
                MarketingKeyValue(label: 'Giá trị mang lại (Value)', value: read(offer['value'])),
                MarketingKeyValue(label: 'Bảo chứng & Bằng chứng (Proof)', value: read(offer['proof'])),
                MarketingKeyValue(label: 'Quà tặng kèm (Bonus / Add-ons)', value: read(offer['bonus'])),
                MarketingKeyValue(label: 'Cam kết đảo ngược rủi ro (Risk Reversal / Guarantee)', value: read(offer['guarantee'])),
                MarketingKeyValue(label: 'Yếu tố thúc đẩy (Urgency / Scarcity)', value: read(offer['urgency'])),
                MarketingKeyValue(label: 'Lời kêu gọi hành động (Call to Action)', value: read(offer['cta'])),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 4. Bối cảnh chung & Ràng buộc
          MarketingCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarketingSectionHeader(
                  title: '4. Bối cảnh Thương hiệu & Ràng buộc',
                  description:
                      'Giọng điệu thương hiệu, chính sách giá, danh sách đối thủ và các quy định ràng buộc.',
                  action: ElevatedButton.icon(
                    onPressed: () => showContextForm(context, controller),
                    icon: const Icon(Icons.edit_outlined, size: 16),
                    label: const Text('Sửa bối cảnh'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: const Color(0xFF04070E),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                MarketingKeyValue(label: 'Chân dung khách hàng lý tưởng (ICP tóm tắt)', value: read(ctx['icp'])),
                MarketingKeyValue(label: 'Tuyên ngôn giá trị', value: read(ctx['value_proposition'])),
                MarketingKeyValue(label: 'Giọng điệu thương hiệu', value: read(ctx['brand_voice'])),
                MarketingKeyValue(label: 'Chính sách giá', value: read(ctx['pricing'])),
                MarketingKeyValue(label: 'Đối thủ cạnh tranh', value: read(ctx['competitors'])),
                MarketingKeyValue(label: 'Ràng buộc vận hành', value: read(ctx['constraints'])),
                const SizedBox(height: 6),
                Text(
                  'Cập nhật lần cuối: ${formatDate(ctx['updated_at']?.toString())}',
                  style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }


  // ==========================================
  // Tab 3: Mục tiêu
  // ==========================================

  Widget _buildObjectivesTab(BuildContext context) {
    final objectives = controller.objectives;

    if (objectives.isEmpty) {
      return MarketingEmpty(
        icon: Icons.flag_outlined,
        title: 'Chưa có mục tiêu Marketing nào',
        subtitle: 'Mục tiêu Marketing nên bắt nguồn từ mục tiêu chiến lược của công ty, ví dụ "MRR +30%" '
            'sẽ dẫn tới "300 lead đủ điều kiện trong 12 tuần".',
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
        _buildTabActionBar(
          'Mục tiêu Marketing (${objectives.length})',
          'Thêm mục tiêu',
          () => showObjectiveForm(context, controller),
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
                          onPressed: () => _confirmDelete(
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
                      Text(o['description'].toString(),
                          style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.4)),
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
                        Text(formatPercent(progress),
                            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.white)),
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

  // ==========================================
  // Tab 4: Phễu khách hàng
  // ==========================================

  Widget _buildFunnelTab() {
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
                          child: Text('${entry.key + 1}',
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryLight)),
                        ),
                        const SizedBox(width: 12),
                        // Cột nội dung có thể bị bóp hẹp khi cửa sổ nhỏ - nhãn và số liệu
                        // phải co được, nếu không hàng này tràn ngang (RenderFlex overflow).
                        Flexible(
                          child: Text(stage['label']?.toString() ?? '',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white)),
                        ),
                        const SizedBox(width: 10),
                        if (isBottleneck)
                          const MarketingChip(label: 'Nút thắt', color: Colors.amberAccent, icon: Icons.warning_amber_rounded),
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
                    Text(stage['goal']?.toString() ?? '',
                        style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.4)),
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

  // ==========================================
  // Tab 5: Chiến dịch
  // ==========================================

  Widget _buildCampaignsTab(BuildContext context) {
    final campaigns = controller.campaigns;

    if (campaigns.isEmpty) {
      return MarketingEmpty(
        icon: Icons.campaign_outlined,
        title: 'Chưa có chiến dịch nào',
        subtitle: 'Mục tiêu Marketing không tự chạy - nó sinh ra danh mục chiến dịch gắn với từng bước phễu.',
        action: ElevatedButton.icon(
          onPressed: () => showCampaignForm(context, controller),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Tạo chiến dịch'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      );
    }

    return Column(
      children: [
        _buildTabActionBar(
          'Danh mục chiến dịch (${campaigns.length})',
          'Tạo chiến dịch',
          () => showCampaignForm(context, controller),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: campaigns.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final c = campaigns[index] as Map<String, dynamic>;
              final status = c['status']?.toString();
              final channels = (c['channels'] as List<dynamic>?) ?? const [];
              return MarketingCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(c['name']?.toString() ?? '',
                              style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14.5)),
                        ),
                        MarketingChip(
                          label: MarketingLabels.campaign(status),
                          color: MarketingLabels.campaignColor(status),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        MarketingChip(
                          label: c['funnel_stage_label']?.toString() ?? '',
                          color: AppTheme.primaryLight,
                          icon: Icons.filter_alt_outlined,
                        ),
                        MarketingChip(
                          label: 'Ngân sách ${formatNumber(c['budget'])}',
                          color: Colors.white70,
                          icon: Icons.account_balance_wallet_outlined,
                        ),
                        if ((c['owner']?.toString() ?? '').isNotEmpty)
                          MarketingChip(
                            label: c['owner'].toString(),
                            color: Colors.white70,
                            icon: Icons.person_outline,
                          ),
                        ...channels.map((ch) => MarketingChip(label: ch.toString(), color: AppTheme.secondaryLight)),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        TextButton.icon(
                          onPressed: () => _showCampaignDetail(context, c),
                          icon: const Icon(Icons.open_in_new, size: 15),
                          label: const Text('Chi tiết', style: TextStyle(fontSize: 12.5)),
                          style: TextButton.styleFrom(foregroundColor: AppTheme.primaryLight),
                        ),
                        TextButton.icon(
                          onPressed: () => showCampaignForm(context, controller, existing: c),
                          icon: const Icon(Icons.edit_outlined, size: 15),
                          label: const Text('Sửa', style: TextStyle(fontSize: 12.5)),
                          style: TextButton.styleFrom(foregroundColor: AppTheme.textMutedDark),
                        ),
                        const Spacer(),
                        if (status == 'draft' || status == 'paused')
                          TextButton.icon(
                            onPressed: () => controller.changeCampaignStatus(c['id'].toString(), 'active'),
                            icon: const Icon(Icons.play_arrow_rounded, size: 16),
                            label: const Text('Đề nghị kích hoạt', style: TextStyle(fontSize: 12.5)),
                            style: TextButton.styleFrom(foregroundColor: AppTheme.success),
                          ),
                        if (status == 'active')
                          TextButton.icon(
                            onPressed: () => controller.changeCampaignStatus(c['id'].toString(), 'paused'),
                            icon: const Icon(Icons.pause_rounded, size: 16),
                            label: const Text('Đề nghị tạm dừng', style: TextStyle(fontSize: 12.5)),
                            style: TextButton.styleFrom(foregroundColor: Colors.orangeAccent),
                          ),
                        IconButton(
                          tooltip: 'Xoá chiến dịch',
                          icon: const Icon(Icons.delete_outline, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => _confirmDelete(
                            context,
                            'Xoá chiến dịch?',
                            c['name']?.toString() ?? '',
                            () => controller.deleteCampaign(c['id'].toString()),
                          ),
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

  Future<void> _showCampaignDetail(BuildContext context, Map<String, dynamic> campaign) async {
    final detail = await controller.loadCampaignDetail(campaign['id'].toString());
    final assets = (detail['assets'] as List<dynamic>?) ?? const [];
    final experiments = (detail['experiments'] as List<dynamic>?) ?? const [];
    if (!context.mounted) return;

    Get.dialog<void>(
      Dialog(
        backgroundColor: kMarketingCardColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        child: Container(
          width: 640,
          constraints: const BoxConstraints(maxHeight: 640),
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(campaign['name']?.toString() ?? '',
                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Colors.white)),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: AppTheme.textMutedDark),
                    onPressed: () => Get.back<void>(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const MarketingSectionHeader(title: 'Nội dung của chiến dịch'),
                      const SizedBox(height: 10),
                      if (assets.isEmpty)
                        const Text('Chưa có nội dung nào.',
                            style: TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark))
                      else
                        ...assets.map((raw) {
                          final a = raw as Map<String, dynamic>;
                          final assetStatus = a['approval_status']?.toString();
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: MarketingCard(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(a['title']?.toString() ?? '',
                                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                                      ),
                                      MarketingChip(
                                        label: MarketingLabels.asset(assetStatus),
                                        color: MarketingLabels.assetColor(assetStatus),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    a['content']?.toString() ?? '',
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.4),
                                  ),
                                  if (assetStatus == 'draft') ...[
                                    const SizedBox(height: 8),
                                    Align(
                                      alignment: Alignment.centerRight,
                                      child: TextButton.icon(
                                        onPressed: () {
                                          Get.back<void>();
                                          controller.requestAssetApproval(a['id'].toString());
                                        },
                                        icon: const Icon(Icons.send_outlined, size: 15),
                                        label: const Text('Gửi duyệt xuất bản', style: TextStyle(fontSize: 12.5)),
                                        style: TextButton.styleFrom(foregroundColor: AppTheme.primaryLight),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        }),
                      const SizedBox(height: 16),
                      const MarketingSectionHeader(title: 'Thử nghiệm gắn với chiến dịch'),
                      const SizedBox(height: 10),
                      if (experiments.isEmpty)
                        const Text('Chưa có thử nghiệm nào.',
                            style: TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark))
                      else
                        ...experiments.map((raw) {
                          final e = raw as Map<String, dynamic>;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(e['hypothesis']?.toString() ?? '',
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 12.5, color: Colors.white70)),
                                ),
                                const SizedBox(width: 8),
                                MarketingChip(
                                  label: MarketingLabels.experiment(e['status']?.toString()),
                                  color: MarketingLabels.experimentColor(e['status']?.toString()),
                                ),
                              ],
                            ),
                          );
                        }),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Get.back<void>();
                    showAssetForm(context, controller, campaign['id'].toString());
                  },
                  icon: const Icon(Icons.add, size: 17),
                  label: const Text('Thêm nội dung'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: const Color(0xFF04070E),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ==========================================
  // Tab 6: Vòng lặp Tăng trưởng (§18 Marketing Loops)
  // ==========================================

  Widget _buildLoopsTab(BuildContext context) {
    final loops = controller.loops;

    if (loops.isEmpty) {
      return MarketingEmpty(
        icon: Icons.loop_rounded,
        title: 'Chưa có vòng lặp tăng trưởng nào',
        subtitle:
            'Marketing OS v2 chuyển từ chiến dịch tuyến tính sang 4 Vòng lặp khép kín: Content Loop, Paid Ads Loop, Conversion Loop, Retention Loop (§18).',
        action: ElevatedButton.icon(
          onPressed: () => showLoopForm(context, controller),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Tạo vòng lặp mới'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      );
    }

    return Column(
      children: [
        _buildTabActionBar(
          'Vòng lặp Marketing khép kín (${loops.length})',
          'Tạo vòng lặp',
          () => showLoopForm(context, controller),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: loops.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final loop = loops[index] as Map<String, dynamic>;
              final status = loop['status']?.toString() ?? 'active';
              final loopType = loop['loop_type']?.toString() ?? 'content';
              final lastRun = loop['last_run_at']?.toString();

              Color loopColor;
              String loopTypeLabel;
              switch (loopType) {
                case 'content':
                  loopColor = Colors.blueAccent;
                  loopTypeLabel = 'Content Loop';
                  break;
                case 'paid_ads':
                  loopColor = Colors.purpleAccent;
                  loopTypeLabel = 'Paid Ads Loop';
                  break;
                case 'conversion':
                  loopColor = Colors.amberAccent;
                  loopTypeLabel = 'Conversion Loop';
                  break;
                case 'retention':
                  loopColor = AppTheme.success;
                  loopTypeLabel = 'Retention Loop';
                  break;
                default:
                  loopColor = AppTheme.primaryLight;
                  loopTypeLabel = loopType;
              }

              return MarketingCard(
                borderColor: loopColor.withValues(alpha: 0.3),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.sync_rounded, color: loopColor, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            loop['name']?.toString() ?? '',
                            style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14.5),
                          ),
                        ),
                        MarketingChip(label: loopTypeLabel, color: loopColor),
                        const SizedBox(width: 6),
                        MarketingChip(
                          label: status == 'active' ? 'Đang chạy' : 'Tạm dừng',
                          color: status == 'active' ? AppTheme.success : AppTheme.textMutedDark,
                        ),
                      ],
                    ),
                    if ((loop['description']?.toString() ?? '').isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        loop['description'].toString(),
                        style: const TextStyle(fontSize: 12.5, color: Colors.white70, height: 1.4),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Text(
                          'Tần suất: ${loop['loop_config']?['frequency'] ?? 'Hàng tuần'} · '
                          'Chạy gần nhất: ${lastRun != null ? formatDate(lastRun) : 'Chưa chạy lần nào'}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                        ),
                        const Spacer(),
                        ElevatedButton.icon(
                          onPressed: () => controller.triggerLoop(loop['id'].toString()),
                          icon: const Icon(Icons.play_arrow_rounded, size: 16),
                          label: const Text('Kích hoạt chu kỳ', style: TextStyle(fontSize: 12)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: loopColor,
                            foregroundColor: const Color(0xFF04070E),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          ),
                        ),
                        const SizedBox(width: 6),
                        IconButton(
                          tooltip: 'Sửa',
                          icon: const Icon(Icons.edit_outlined, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => showLoopForm(context, controller, existing: loop),
                        ),
                        IconButton(
                          tooltip: 'Xoá',
                          icon: const Icon(Icons.delete_outline, size: 17, color: AppTheme.textMutedDark),
                          onPressed: () => _confirmDelete(
                            context,
                            'Xoá vòng lặp?',
                            loop['name']?.toString() ?? '',
                            () => controller.deleteLoop(loop['id'].toString()),
                          ),
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

  // ==========================================
  // Tab 7: Thử nghiệm
  // ==========================================

  Widget _buildExperimentsTab(BuildContext context) {

    final experiments = controller.experiments;

    if (experiments.isEmpty) {
      return MarketingEmpty(
        icon: Icons.science_outlined,
        title: 'Chưa có thử nghiệm nào',
        subtitle: 'Marketing OS chuyển từ "AI đưa lời khuyên" sang "AI đề xuất giả thuyết → đo lường → quyết định".',
        action: ElevatedButton.icon(
          onPressed: () => showExperimentForm(context, controller),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Tạo thử nghiệm'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
        ),
      );
    }

    return Column(
      children: [
        _buildTabActionBar(
          'Thử nghiệm (${experiments.length})',
          'Tạo thử nghiệm',
          () => showExperimentForm(context, controller),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: experiments.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final e = experiments[index] as Map<String, dynamic>;
              final status = e['status']?.toString();
              final evaluation = e['evaluation'];
              return MarketingCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
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
                    Text(
                      'Chỉ số: ${e['metric']} · nền ${formatNumber(e['baseline_value'], decimals: 2)} → kỳ vọng ${formatNumber(e['target_value'], decimals: 2)} · cỡ mẫu ${formatNumber(e['sample_size'])}',
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
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
          Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.primaryLight, fontWeight: FontWeight.w600)),
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
  // Tab 8: Chỉ số & Phân bổ (§14, §28)
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
                          const Text('Đóng góp theo kênh:', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
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
                        description: 'Không dùng AI để tính KPI. Mọi con số dưới đây là kết quả tính toán tất định '
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
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13.5)),
                                  const SizedBox(height: 3),
                                  Text(
                                    '${MarketingLabels.metricCategory[m['category']] ?? m['category']} · cập nhật ${formatDate(m['updated_at']?.toString())}',
                                    style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                                  ),
                                ],
                              ),
                            ),
                            Text(formatNumber(m['current_value'], decimals: 2),
                                style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                            const SizedBox(width: 10),
                            MarketingChip(
                              label: '${change > 0 ? '+' : ''}${formatNumber(change, decimals: 1)}%',
                              color: change > 0 ? AppTheme.success : (change < 0 ? AppTheme.accent : AppTheme.textMutedDark),
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

  // ==========================================
  // Tab 9: Bài học & Quyết định (§15, §53)
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
                        description: 'Lưu vết ngữ cảnh, lý do ra quyết định và bài học thực tế để phòng tránh thiên kiến nhận thức.',
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
                                    Expanded(
                                      child: Text(
                                        d['title']?.toString() ?? '',
                                        style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13.5),
                                      ),
                                    ),
                                    Text(
                                      formatDate(d['created_at']?.toString()),
                                      style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                MarketingKeyValue(label: 'Quyết định', value: d['decision']?.toString() ?? '—'),
                                if ((d['reason']?.toString() ?? '').isNotEmpty)
                                  MarketingKeyValue(label: 'Lý do', value: d['reason'].toString()),
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
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13.5, height: 1.4)),
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
  // Tab 9: Kho kỹ năng
  // ==========================================

  Widget _buildSkillsTab(BuildContext context) {
    final skills = controller.skills;
    final executions = controller.skillExecutions;

    if (skills.isEmpty) {
      return const MarketingEmpty(
        icon: Icons.auto_awesome_outlined,
        title: 'Kho năng lực trống',
        subtitle: 'Chưa nạp được danh mục năng lực từ Skill Registry.',
      );
    }

    return Column(
      children: [
        MarketingCard(
          child: MarketingSectionHeader(
            title: 'Kho năng lực (${skills.length})',
            description: 'Định tuyến theo năng lực, không theo tên kho skill. Mỗi năng lực có một nhà cung cấp chính '
                'và một phương án dự phòng. Runtime thi hành chưa được đấu nối nên kết quả hiện là mô phỏng có ghi log.',
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: GridView.builder(
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 400,
              mainAxisExtent: 214,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: skills.length + (executions.isEmpty ? 0 : 1),
            itemBuilder: (context, index) {
              if (index == skills.length) {
                return _buildExecutionLogCard(executions);
              }
              final sk = skills[index] as Map<String, dynamic>;
              final capId = sk['capability_id']?.toString() ?? '';
              final primary = (sk['primary'] as Map<String, dynamic>?) ?? const {};
              final fallback = sk['fallback'] as Map<String, dynamic>?;
              final perms = (sk['permissions'] as Map<String, dynamic>?) ?? const {};
              final requiresApproval = perms['external_write'] == true || perms['spend'] == true;

              return MarketingCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                sk['title']?.toString() ?? capId,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5, color: Colors.white),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 6),
                            MarketingChip(
                              label: requiresApproval ? 'Cần duyệt' : 'Tự động',
                              color: requiresApproval ? Colors.amberAccent : AppTheme.success,
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(capId,
                            style: const TextStyle(fontSize: 11, color: AppTheme.primaryLight, fontFamily: 'monospace')),
                        const SizedBox(height: 6),
                        Text(
                          sk['description']?.toString() ?? '',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark, height: 1.4),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [
                            MarketingChip(label: 'Chính: ${primary['source'] ?? '—'}', color: AppTheme.primaryLight),
                            if (fallback != null && fallback['source'] != null)
                              MarketingChip(label: 'Dự phòng: ${fallback['source']}', color: Colors.white70),
                          ],
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: () => _confirmExecuteSkill(context, capId, sk['title']?.toString() ?? capId, requiresApproval),
                            icon: Icon(requiresApproval ? Icons.how_to_reg_outlined : Icons.play_arrow_rounded, size: 16),
                            label: Text(requiresApproval ? 'Gửi yêu cầu duyệt' : 'Chạy năng lực',
                                style: const TextStyle(fontSize: 12)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: requiresApproval ? Colors.amber.shade800 : AppTheme.primary,
                              foregroundColor: const Color(0xFF04070E),
                              padding: const EdgeInsets.symmetric(vertical: 9),
                            ),
                          ),
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

  Widget _buildExecutionLogCard(List<dynamic> executions) {
    return MarketingCard(
      borderColor: AppTheme.primary.withValues(alpha: 0.25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Nhật ký chạy năng lực',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5, color: Colors.white)),
          const SizedBox(height: 8),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: executions.take(6).map((raw) {
                final e = raw as Map<String, dynamic>;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(e['capability_id']?.toString() ?? '',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 11.5, color: Colors.white70, fontFamily: 'monospace')),
                      ),
                      MarketingChip(
                        label: e['status'] == 'simulated' ? 'Mô phỏng' : (e['status']?.toString() ?? ''),
                        color: AppTheme.textMutedDark,
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  void _confirmExecuteSkill(BuildContext context, String capabilityId, String title, bool requiresApproval) {
    Get.dialog<void>(
      AlertDialog(
        backgroundColor: kMarketingCardColor,
        title: Text(requiresApproval ? 'Gửi yêu cầu phê duyệt' : 'Chạy năng lực',
            style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: Text(
          requiresApproval
              ? 'Năng lực "$title" có tác động ra bên ngoài (xuất bản hoặc chi tiền) nên sẽ được đưa vào hàng đợi '
                  'phê duyệt thay vì chạy ngay.'
              : 'Chạy năng lực "$title"? Hệ thống sẽ nạp gói bối cảnh tối thiểu và ghi lại lần chạy này.',
          style: const TextStyle(color: AppTheme.textMutedDark, height: 1.45),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back<void>(),
            child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: const Color(0xFF04070E),
            ),
            onPressed: () async {
              Get.back<void>();
              final result = await controller.executeSkill(capabilityId, {'title': title});
              final status = result['status']?.toString();
              if (status == null) return;
              Get.snackbar(
                status == 'pending_approval' ? 'Đã đưa vào hàng đợi duyệt' : 'Đã định tuyến năng lực',
                status == 'pending_approval'
                    ? 'Hành động cần người phê duyệt trước khi thực thi.'
                    : (result['result']?['message']?.toString() ?? 'Đã ghi nhận lần chạy.'),
                snackPosition: SnackPosition.BOTTOM,
                duration: const Duration(seconds: 5),
              );
            },
            child: Text(requiresApproval ? 'Gửi duyệt' : 'Chạy'),
          ),
        ],
      ),
    );
  }

  // ==========================================
  // Tab 10: Phê duyệt
  // ==========================================

  Widget _buildApprovalsTab(BuildContext context) {
    final approvals = controller.pendingApprovals;

    if (approvals.isEmpty) {
      return const MarketingEmpty(
        icon: Icons.verified_outlined,
        title: 'Không có hành động nào chờ duyệt',
        subtitle: 'Nghiên cứu, soạn nháp, phân tích và đề xuất được chạy tự động. Xuất bản nội dung, gửi email hàng '
            'loạt, chi ngân sách hay đổi giá luôn dừng lại ở đây để bạn quyết định.',
      );
    }

    return Column(
      children: [
        MarketingCard(
          child: MarketingSectionHeader(
            title: 'Hàng đợi phê duyệt (${approvals.length})',
            description: 'Sau khi bạn phê duyệt, hành động mới được thực thi và ghi vào nhật ký.',
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.separated(
            itemCount: approvals.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) => _buildApprovalRow(context, approvals[index] as Map<String, dynamic>),
          ),
        ),
      ],
    );
  }

  Widget _buildApprovalRow(BuildContext context, Map<String, dynamic> a) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: MarketingCard(
        borderColor: Colors.amberAccent.withValues(alpha: 0.3),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(a['title']?.toString() ?? 'Hành động cần phê duyệt',
                      style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13.5)),
                  const SizedBox(height: 5),
                  Text(
                    'Loại: ${a['action_type']} · Đề xuất bởi: ${a['requested_by_agent'] ?? '—'} · ${formatDate(a['created_at']?.toString())}',
                    style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark),
                  ),
                ],
              ),
            ),
            TextButton.icon(
              onPressed: () => showApprovalReviewDialog(context, controller, a, approve: true),
              icon: const Icon(Icons.check_circle_outline, size: 16),
              label: const Text('Duyệt', style: TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(foregroundColor: AppTheme.success),
            ),
            TextButton.icon(
              onPressed: () => showApprovalReviewDialog(context, controller, a, approve: false),
              icon: const Icon(Icons.cancel_outlined, size: 16),
              label: const Text('Từ chối', style: TextStyle(fontSize: 12.5)),
              style: TextButton.styleFrom(foregroundColor: AppTheme.accent),
            ),
          ],
        ),
      ),
    );
  }

  // ==========================================
  // Tiện ích chung
  // ==========================================

  Widget _buildTabActionBar(String title, String actionLabel, VoidCallback onAction) {
    return MarketingCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(title,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
          ),
          ElevatedButton.icon(
            onPressed: onAction,
            icon: const Icon(Icons.add, size: 17),
            label: Text(actionLabel, style: const TextStyle(fontSize: 12.5)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: const Color(0xFF04070E),
            ),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(BuildContext context, String title, String name, VoidCallback onConfirm) {
    Get.dialog<void>(
      AlertDialog(
        backgroundColor: kMarketingCardColor,
        title: Text(title, style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: Text('Bạn chắc chắn muốn xoá "$name"? Thao tác này không thể hoàn tác.',
            style: const TextStyle(color: AppTheme.textMutedDark, height: 1.45)),
        actions: [
          TextButton(
            onPressed: () => Get.back<void>(),
            child: const Text('Huỷ', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accent),
            onPressed: () {
              Get.back<void>();
              onConfirm();
            },
            child: const Text('Xoá'),
          ),
        ],
      ),
    );
  }
}
