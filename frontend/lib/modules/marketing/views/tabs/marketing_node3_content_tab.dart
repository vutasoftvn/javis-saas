import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

/// Node 3: AI Thực thi & Chiến dịch (Campaigns, Loops, Skill Registry)
class MarketingNode3ContentTab extends GetView<MarketingController> {
  const MarketingNode3ContentTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MarketingSubTabBar(
            current: controller.contentSubTab.value,
            items: const [
              {'key': 'campaigns', 'label': 'Chiến dịch & Nội dung', 'icon': Icons.campaign_rounded},
              {'key': 'skills', 'label': 'Kho kỹ năng AI (Skill Registry)', 'icon': Icons.auto_awesome_rounded},
              {'key': 'loops', 'label': 'Vòng lặp tăng trưởng', 'icon': Icons.sync_rounded},
            ],
            onSelect: (k) => controller.contentSubTab.value = k,
          ),
          const SizedBox(height: 10),
          Expanded(
            child: _buildSubTabContent(context, controller.contentSubTab.value),
          ),
        ],
      );
    });
  }

  Widget _buildSubTabContent(BuildContext context, String currentTab) {
    switch (currentTab) {
      case 'skills':
        return _buildSkillsTab(context);
      case 'loops':
        return _buildLoopsTab(context);
      case 'campaigns':
      default:
        return _buildCampaignsTab(context);
    }
  }

  // ==========================================
  // Tab: Chiến dịch & Nội dung
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
        MarketingTabActionBar(
          title: 'Danh mục chiến dịch (${campaigns.length})',
          actionLabel: 'Tạo chiến dịch',
          onAction: () => showCampaignForm(context, controller),
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
                          child: Text(
                            c['name']?.toString() ?? '',
                            style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14.5),
                          ),
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
                          onPressed: () => confirmMarketingDelete(
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
                    child: Text(
                      campaign['name']?.toString() ?? '',
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
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
                                        child: Text(
                                          a['title']?.toString() ?? '',
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                                        ),
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
                                  child: Text(
                                    e['hypothesis']?.toString() ?? '',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 12.5, color: Colors.white70),
                                  ),
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
  // Tab: Vòng lặp Tăng trưởng (§18 Marketing Loops)
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
        MarketingTabActionBar(
          title: 'Vòng lặp Marketing khép kín (${loops.length})',
          actionLabel: 'Tạo vòng lặp',
          onAction: () => showLoopForm(context, controller),
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
                          onPressed: () => confirmMarketingDelete(
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
  // Tab: Kho Kỹ năng AI (Skill Registry)
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

    final selectedSkill = controller.selectedSkill.value;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            children: [
              const MarketingCard(
                child: MarketingSectionHeader(
                  title: 'Kho năng lực',
                  description:
                      'Định tuyến theo năng lực, không theo tên kho skill. Mỗi năng lực có một nhà cung cấp chính '
                      'và một phương án dự phòng. Bấm vào card để xem chi tiết cấu hình và nhật ký thực thi.',
                ),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 380,
                    mainAxisExtent: 180,
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
                    final isSelected = selectedSkill != null && selectedSkill['capability_id'] == capId;

                    return InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () => controller.selectSkill(sk),
                      child: MarketingCard(
                        borderColor: isSelected
                            ? AppTheme.primary
                            : (requiresApproval ? Colors.amber.withValues(alpha: 0.25) : null),
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
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13.5,
                                          color: isSelected ? AppTheme.primaryLight : Colors.white,
                                        ),
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
                                Text(
                                  capId,
                                  style: const TextStyle(
                                      fontSize: 11, color: AppTheme.primaryLight, fontFamily: 'monospace'),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  sk['description']?.toString() ?? '',
                                  style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark, height: 1.4),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.center,
                              children: [
                                Expanded(
                                  child: Wrap(
                                    spacing: 6,
                                    runSpacing: 4,
                                    children: [
                                      MarketingChip(
                                          label: 'Chính: ${primary['source'] ?? '—'}', color: AppTheme.primaryLight),
                                      if (fallback != null && fallback['source'] != null)
                                        MarketingChip(label: 'Dự phòng: ${fallback['source']}', color: Colors.white70),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Material(
                                  color: requiresApproval ? Colors.amber.shade800 : AppTheme.primary,
                                  borderRadius: BorderRadius.circular(8),
                                  child: InkWell(
                                    borderRadius: BorderRadius.circular(8),
                                    onTap: () => _confirmExecuteSkill(
                                        context, capId, sk['title']?.toString() ?? capId, requiresApproval),
                                    child: Tooltip(
                                      message: requiresApproval ? 'Gửi yêu cầu duyệt' : 'Chạy năng lực',
                                      child: Padding(
                                        padding: const EdgeInsets.all(7),
                                        child: Icon(
                                          requiresApproval ? Icons.how_to_reg_rounded : Icons.play_arrow_rounded,
                                          color: const Color(0xFF04070E),
                                          size: 18,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
        if (selectedSkill != null) ...[
          const SizedBox(width: 14),
          SizedBox(
            width: 380,
            child: _buildSkillDetailSidebar(context, selectedSkill),
          ),
        ],
      ],
    );
  }

  Widget _buildSkillDetailSidebar(BuildContext context, Map<String, dynamic> sk) {
    final capId = sk['capability_id']?.toString() ?? '';
    final title = sk['title']?.toString() ?? capId;
    final description = sk['description']?.toString() ?? '';
    final primary = (sk['primary'] as Map<String, dynamic>?) ?? const {};
    final fallback = sk['fallback'] as Map<String, dynamic>?;
    final perms = (sk['permissions'] as Map<String, dynamic>?) ?? const {};
    final requiresApproval = perms['external_write'] == true || perms['spend'] == true;

    final capabilityExecutions = controller.skillExecutions
        .where((e) => (e as Map<String, dynamic>)['capability_id'] == capId)
        .toList();

    return MarketingCard(
      padding: const EdgeInsets.all(16),
      borderColor: AppTheme.primary.withValues(alpha: 0.35),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: (requiresApproval ? Colors.amber : AppTheme.primary).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: (requiresApproval ? Colors.amber : AppTheme.primary).withValues(alpha: 0.35),
                  ),
                ),
                child: Icon(
                  requiresApproval ? Icons.security_rounded : Icons.auto_awesome_rounded,
                  color: requiresApproval ? Colors.amberAccent : AppTheme.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5, color: Colors.white),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      capId,
                      style: const TextStyle(fontSize: 11, color: AppTheme.primaryLight, fontFamily: 'monospace'),
                    ),
                  ],
                ),
              ),
              IconButton(
                tooltip: 'Đóng chi tiết',
                icon: const Icon(Icons.close_rounded, size: 18, color: Colors.white70),
                onPressed: () => controller.selectSkill(null),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Action Button
          ElevatedButton.icon(
            onPressed: () => _confirmExecuteSkill(context, capId, title, requiresApproval),
            icon: Icon(requiresApproval ? Icons.how_to_reg_outlined : Icons.play_arrow_rounded, size: 16),
            label: Text(
              requiresApproval ? 'Gửi yêu cầu duyệt năng lực' : 'Chạy năng lực này',
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: requiresApproval ? Colors.amber.shade800 : AppTheme.primary,
              foregroundColor: const Color(0xFF04070E),
              padding: const EdgeInsets.symmetric(vertical: 10),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
            ),
          ),
          const SizedBox(height: 12),
          const Divider(color: Colors.white12, height: 1),
          const SizedBox(height: 12),

          // Scrollable Body
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Description
                  const Text('Mô tả & Mục tiêu năng lực',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 6),
                  Text(
                    description.isNotEmpty ? description : 'Chưa có mô tả chi tiết cho năng lực này.',
                    style: const TextStyle(fontSize: 12.5, color: Colors.white70, height: 1.45),
                  ),
                  const SizedBox(height: 14),

                  // Routing Details
                  const Text('Định tuyến nhà cung cấp',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.star_rounded, size: 14, color: AppTheme.primaryLight),
                            SizedBox(width: 6),
                            Text('Nhà cung cấp chính (Primary)',
                                style: TextStyle(
                                    fontSize: 11.5, fontWeight: FontWeight.bold, color: AppTheme.primaryLight)),
                          ],
                        ),
                        const SizedBox(height: 6),
                        _buildRoutingInfoRow('Nguồn (Source):', primary['source']?.toString() ?? '—'),
                        _buildRoutingInfoRow('Gói kỹ năng (Skill):', primary['skill']?.toString() ?? '—'),
                        _buildRoutingInfoRow('Loại (Type):', primary['type']?.toString() ?? '—'),
                        if (fallback != null && fallback.isNotEmpty) ...[
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 8),
                            child: Divider(color: Colors.white10, height: 1),
                          ),
                          const Row(
                            children: [
                              Icon(Icons.backup_table_rounded, size: 14, color: Colors.white70),
                              SizedBox(width: 6),
                              Text('Phương án dự phòng (Fallback)',
                                  style:
                                      TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Colors.white70)),
                            ],
                          ),
                          const SizedBox(height: 6),
                          _buildRoutingInfoRow('Nguồn (Source):', fallback['source']?.toString() ?? '—'),
                          _buildRoutingInfoRow('Gói kỹ năng (Skill):', fallback['skill']?.toString() ?? '—'),
                          _buildRoutingInfoRow('Loại (Type):', fallback['type']?.toString() ?? '—'),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Permissions & Safety Governance
                  const Text('Phân quyền & Ranh giới an toàn',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildPermissionItem(
                          icon: Icons.edit_note_rounded,
                          title: 'Tác động môi trường ngoài (External Write)',
                          allowed: perms['external_write'] == true,
                          hint: perms['external_write'] == true
                              ? 'Cần duyệt trước khi xuất bản/gửi tin'
                              : 'Chỉ đọc & tạo nháp nội bộ',
                        ),
                        const SizedBox(height: 8),
                        _buildPermissionItem(
                          icon: Icons.payments_outlined,
                          title: 'Chi tiêu ngân sách (Spend Budget)',
                          allowed: perms['spend'] == true,
                          hint: perms['spend'] == true
                              ? 'Cần duyệt tài chính trước khi chi tiêu'
                              : 'Không phát sinh chi phí ngân sách',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Execution History for this capability
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Lịch sử thực thi năng lực',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                      MarketingChip(
                        label: '${capabilityExecutions.length} lượt',
                        color: capabilityExecutions.isNotEmpty ? AppTheme.primaryLight : AppTheme.textMutedDark,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (capabilityExecutions.isEmpty)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                      ),
                      child: const Text(
                        'Chưa có nhật ký chạy nào cho năng lực này.',
                        style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                        textAlign: TextAlign.center,
                      ),
                    )
                  else
                    ...capabilityExecutions.map((raw) {
                      final e = raw as Map<String, dynamic>;
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceDark,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  formatDate(e['created_at']?.toString()),
                                  style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                                ),
                                MarketingChip(
                                  label: e['status'] == 'simulated' ? 'Mô phỏng' : (e['status']?.toString() ?? ''),
                                  color: e['status'] == 'simulated' ? AppTheme.primaryLight : AppTheme.success,
                                ),
                              ],
                            ),
                            if (e['requested_by_agent'] != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                'Yêu cầu bởi: ${e['requested_by_agent']}',
                                style: const TextStyle(fontSize: 11.5, color: Colors.white70),
                              ),
                            ],
                          ],
                        ),
                      );
                    }),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRoutingInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(label, style: const TextStyle(fontSize: 11.5, color: AppTheme.textMutedDark)),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                  fontSize: 11.5, color: Colors.white, fontWeight: FontWeight.w500, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPermissionItem({
    required IconData icon,
    required String title,
    required bool allowed,
    required String hint,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: allowed ? Colors.amberAccent : AppTheme.success),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: const TextStyle(fontSize: 11.5, color: Colors.white70, fontWeight: FontWeight.w500)),
              const SizedBox(height: 2),
              Text(hint, style: TextStyle(fontSize: 11, color: allowed ? Colors.amberAccent : AppTheme.textMutedDark)),
            ],
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
                        child: Text(
                          e['capability_id']?.toString() ?? '',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11.5, color: Colors.white70, fontFamily: 'monospace'),
                        ),
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
        title: Text(
          requiresApproval ? 'Gửi yêu cầu phê duyệt' : 'Chạy năng lực',
          style: const TextStyle(color: Colors.white, fontSize: 16),
        ),
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
}
