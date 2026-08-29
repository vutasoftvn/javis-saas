import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/modules/marketing/controllers/marketing_controller.dart';
import 'package:frontend/modules/marketing/views/widgets/marketing_common.dart';
import 'package:frontend/modules/marketing/views/widgets/marketing_forms.dart';

class MarketingCampaignsSubtab extends StatelessWidget {
  final MarketingController controller;

  const MarketingCampaignsSubtab({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
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
}
