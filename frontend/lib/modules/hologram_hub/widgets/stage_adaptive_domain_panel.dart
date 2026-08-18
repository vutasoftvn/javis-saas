import 'package:flutter/material.dart';
import '../../../data/models/stage_model.dart';

class StageAdaptiveDomainPanel extends StatelessWidget {
  final ProjectStage stage;
  final Function(int tabIndex, int subTabIndex) onNavigate;
  final VoidCallback? onOpenRoster;

  const StageAdaptiveDomainPanel({
    super.key,
    required this.stage,
    required this.onNavigate,
    this.onOpenRoster,
  });

  List<_DomainShortcutItem> _getShortcutsForStage() {
    switch (stage) {
      case ProjectStage.s0Explore:
      case ProjectStage.s1ProblemValidation:
        return [
          _DomainShortcutItem(
            title: 'Trục Bằng Chứng & Giả Định',
            subtitle: 'Evidence Ladder (E0-E4)',
            icon: Icons.hub_outlined,
            color: const Color(0xFF6366F1),
            tabIndex: 3,
            subTabIndex: 1, // Tab 2: Evidence Backbone
          ),
          _DomainShortcutItem(
            title: 'Phỏng Vấn & ICP Discovery',
            subtitle: 'Xác thực nỗi đau khách hàng',
            icon: Icons.record_voice_over_outlined,
            color: const Color(0xFF38BDF8),
            tabIndex: 3,
            subTabIndex: 1,
          ),
          _DomainShortcutItem(
            title: 'Lăng Kính Chiến Lược Sơ Bộ',
            subtitle: 'PESTEL-lite & Tín hiệu thị trường',
            icon: Icons.lens_blur_outlined,
            color: const Color(0xFFA855F7),
            tabIndex: 3,
            subTabIndex: 0,
          ),
        ];

      case ProjectStage.s2SolutionValidation:
        return [
          _DomainShortcutItem(
            title: 'Đặc Tả MVP & Value Prop',
            subtitle: 'Kiểm chứng giải pháp tối thiểu',
            icon: Icons.lightbulb_outline,
            color: const Color(0xFFA855F7),
            tabIndex: 3,
            subTabIndex: 1,
          ),
          _DomainShortcutItem(
            title: 'Thử Nghiệm Giá & WTP',
            subtitle: 'Willingness-to-pay Testing',
            icon: Icons.price_check_outlined,
            color: const Color(0xFFF59E0B),
            tabIndex: 3,
            subTabIndex: 1,
          ),
          _DomainShortcutItem(
            title: 'Bộ Nhớ Quyết Định Pivot',
            subtitle: 'Ghi nhận bài học kiểm chứng',
            icon: Icons.history_edu_outlined,
            color: const Color(0xFF06B6D4),
            tabIndex: 3,
            subTabIndex: 2,
          ),
        ];

      case ProjectStage.s3BusinessValidation:
        return [
          _DomainShortcutItem(
            title: 'Unit Economics & Doanh Thu',
            subtitle: 'CAC, LTV, Margin & Payback',
            icon: Icons.monetization_on_outlined,
            color: const Color(0xFFF59E0B),
            tabIndex: 21, // Finance module
            subTabIndex: 0,
          ),
          _DomainShortcutItem(
            title: 'Bằng Chứng Bán Hàng (Paid Pilot)',
            subtitle: 'Sales Validation & Khách hàng trả tiền',
            icon: Icons.point_of_sale_rounded,
            color: const Color(0xFF10B981),
            tabIndex: 23, // Sales module
            subTabIndex: 0,
          ),
          _DomainShortcutItem(
            title: 'Tùy Chọn Chiến Lược TOWS',
            subtitle: 'Xây dựng phương án kinh doanh',
            icon: Icons.alt_route_outlined,
            color: const Color(0xFF38BDF8),
            tabIndex: 3,
            subTabIndex: 0,
          ),
        ];

      case ProjectStage.s4GoToMarket:
        return [
          _DomainShortcutItem(
            title: 'Kênh Marketing & Chiến Dịch',
            subtitle: 'Beachhead Channel Matrix',
            icon: Icons.campaign_outlined,
            color: const Color(0xFF06B6D4),
            tabIndex: 17, // Marketing module
            subTabIndex: 0,
          ),
          _DomainShortcutItem(
            title: 'Phễu Bán Hàng & CRM Pipeline',
            subtitle: 'Lead -> Deal Conversion',
            icon: Icons.filter_alt_outlined,
            color: const Color(0xFF38BDF8),
            tabIndex: 23, // Sales CRM module
            subTabIndex: 0,
          ),
          _DomainShortcutItem(
            title: 'Đội Ngũ AI GTM Phối Hợp',
            subtitle: 'Outreach & Content Workforce',
            icon: Icons.groups_outlined,
            color: const Color(0xFF8B5CF6),
            tabIndex: 20, // AI team overview
            subTabIndex: 0,
          ),
        ];

      case ProjectStage.s5OperateGrowth:
      case ProjectStage.s6ScaleGovern:
        return [
          _DomainShortcutItem(
            title: 'Scoreboard & Kế Hoạch 12WY',
            subtitle: 'Vòng lặp thực thi tuần hoàn',
            icon: Icons.calendar_month_outlined,
            color: const Color(0xFF10B981),
            tabIndex: 28, // 12WY module
            subTabIndex: 0,
          ),
          _DomainShortcutItem(
            title: 'Mục Tiêu Chiến Lược OKRs',
            subtitle: 'Theo dõi Key Results quý',
            icon: Icons.track_changes_outlined,
            color: const Color(0xFF38BDF8),
            tabIndex: 27, // OKRs module
            subTabIndex: 0,
          ),
          _DomainShortcutItem(
            title: 'Sức Khỏe Doanh Nghiệp (BSC)',
            subtitle: '4 Góc nhìn chiến lược',
            icon: Icons.monitor_heart_outlined,
            color: const Color(0xFFEC4899),
            tabIndex: 3,
            subTabIndex: 0,
          ),
        ];
    }
  }

  @override
  Widget build(BuildContext context) {
    final shortcuts = _getShortcutsForStage();

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E).withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: stage.primaryColor.withValues(alpha: 0.25),
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(
                  Icons.auto_awesome_mosaic_outlined,
                  size: 15,
                  color: stage.primaryColor,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Nghiệp Vụ Ưu Tiên (${stage.code})',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12.5,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.2,
                    ),
                  ),
                ),
                if (onOpenRoster != null)
                  InkWell(
                    onTap: onOpenRoster,
                    borderRadius: BorderRadius.circular(6),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.smart_toy_outlined, size: 12, color: stage.primaryColor),
                          const SizedBox(width: 4),
                          Text(
                            'AI Roster',
                            style: TextStyle(
                              color: stage.primaryColor,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            for (int i = 0; i < shortcuts.length; i++)
              _buildShortcutTile(shortcuts[i], i),
          ],
        ),
      ),
    );
  }

  Widget _buildShortcutTile(_DomainShortcutItem item, int index) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => onNavigate(item.tabIndex, item.subTabIndex),
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.03),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: item.color.withValues(alpha: 0.2),
                width: 0.8,
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: item.color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(item.icon, color: item.color, size: 14),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 1),
                      Text(
                        item.subtitle,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 10,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 4),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 10,
                  color: item.color.withValues(alpha: 0.8),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DomainShortcutItem {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final int tabIndex;
  final int subTabIndex;

  const _DomainShortcutItem({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.tabIndex,
    required this.subTabIndex,
  });
}
