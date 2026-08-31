import 'package:flutter/material.dart';
import '../../../../data/models/stage_model.dart';

class DashboardNavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final int index;
  final String? flagKey;

  const DashboardNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.index,
    this.flagKey,
  });
}

class DashboardNavGroup {
  final String title;
  final IconData groupIcon;
  final List<DashboardNavItem> items;

  const DashboardNavGroup({
    required this.title,
    required this.groupIcon,
    required this.items,
  });
}

class DashboardNavConfig {
  static const List<DashboardNavGroup> coreNavGroups = [
    DashboardNavGroup(
      title: 'Hội thoại & Trung tâm',
      groupIcon: Icons.psychology_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.psychology_outlined,
          selectedIcon: Icons.psychology,
          label: 'COSA Command Center',
          index: 0,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Chu kỳ & Chiến lược',
      groupIcon: Icons.flag_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.lightbulb_outline,
          selectedIcon: Icons.lightbulb,
          label: 'Chiến lược',
          index: 3,
          flagKey: 'strategy_module',
        ),
        DashboardNavItem(
          icon: Icons.rocket_launch_outlined,
          selectedIcon: Icons.rocket_launch,
          label: 'Dự án',
          index: 29,
        ),
        DashboardNavItem(
          icon: Icons.track_changes_outlined,
          selectedIcon: Icons.track_changes,
          label: 'OKRs',
          index: 27,
        ),
        DashboardNavItem(
          icon: Icons.calendar_month_outlined,
          selectedIcon: Icons.calendar_month,
          label: 'Kế hoạch 12WY',
          index: 28,
        ),
        DashboardNavItem(
          icon: Icons.account_balance_outlined,
          selectedIcon: Icons.account_balance,
          label: 'Nguồn lực & Tài trợ',
          index: 32,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Công việc & Vận hành',
      groupIcon: Icons.work_outline,
      items: [
        DashboardNavItem(
          icon: Icons.check_box_outline_blank,
          selectedIcon: Icons.check_box,
          label: 'Nhiệm vụ',
          index: 1,
        ),
        DashboardNavItem(
          icon: Icons.fact_check_outlined,
          selectedIcon: Icons.fact_check,
          label: 'Phê duyệt',
          index: 6,
        ),
        DashboardNavItem(
          icon: Icons.notification_important_outlined,
          selectedIcon: Icons.notification_important,
          label: 'Cần bạn xử lý',
          index: 24,
          flagKey: 'needs_you_queue_v13_1',
        ),
        DashboardNavItem(
          icon: Icons.block_outlined,
          selectedIcon: Icons.block,
          label: 'Công việc tắc nghẽn',
          index: 25,
          flagKey: 'structured_blocker_v13_1',
        ),
        DashboardNavItem(
          icon: Icons.visibility_outlined,
          selectedIcon: Icons.visibility,
          label: 'Giám sát công việc',
          index: 26,
          flagKey: 'work_inspector_v13_1',
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Đội ngũ AI & Nghiệp vụ',
      groupIcon: Icons.groups_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.groups_outlined,
          selectedIcon: Icons.groups,
          label: 'Đội ngũ AI Agents',
          index: 7,
        ),
        DashboardNavItem(
          icon: Icons.gavel_outlined,
          selectedIcon: Icons.gavel,
          label: 'Pháp lý & Hợp đồng AI',
          index: 22,
        ),
        DashboardNavItem(
          icon: Icons.campaign_outlined,
          selectedIcon: Icons.campaign,
          label: 'Marketing & Lead Gen',
          index: 17,
        ),
        DashboardNavItem(
          icon: Icons.point_of_sale_rounded,
          selectedIcon: Icons.point_of_sale,
          label: 'Bán hàng & CRM',
          index: 23,
        ),
        DashboardNavItem(
          icon: Icons.psychology_outlined,
          selectedIcon: Icons.psychology,
          label: 'Kỹ năng AI (Skill Registry)',
          index: 33,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Tài chính & Tri thức',
      groupIcon: Icons.account_balance_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.account_balance_wallet_outlined,
          selectedIcon: Icons.account_balance_wallet,
          label: 'Kế toán & Tài chính',
          index: 21,
        ),
        DashboardNavItem(
          icon: Icons.folder_open,
          selectedIcon: Icons.folder,
          label: 'Kho tri thức',
          index: 2,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Tổ chức & Cài đặt',
      groupIcon: Icons.settings_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.corporate_fare_outlined,
          selectedIcon: Icons.corporate_fare,
          label: 'Sơ đồ tổ chức',
          index: 19,
          flagKey: 'advanced_org_chart_v13',
        ),
        DashboardNavItem(
          icon: Icons.account_tree_outlined,
          selectedIcon: Icons.account_tree,
          label: 'Quy trình',
          index: 5,
        ),
        DashboardNavItem(
          icon: Icons.tune_rounded,
          selectedIcon: Icons.tune,
          label: 'Quản trị Template',
          index: 30,
        ),
        DashboardNavItem(
          icon: Icons.settings_outlined,
          selectedIcon: Icons.settings,
          label: 'Cài đặt',
          index: 13,
        ),
      ],
    ),
  ];

  static const DashboardNavGroup experimentalGroup = DashboardNavGroup(
    title: 'Tính năng thử nghiệm',
    groupIcon: Icons.science_outlined,
    items: [
      DashboardNavItem(
        icon: Icons.account_tree_outlined,
        selectedIcon: Icons.account_tree,
        label: 'Quy trình nâng cao',
        index: 5,
      ),
      DashboardNavItem(
        icon: Icons.corporate_fare_outlined,
        selectedIcon: Icons.corporate_fare,
        label: 'Sơ đồ tổ chức chi tiết',
        index: 19,
        flagKey: 'advanced_org_chart_v13',
      ),
    ],
  );

  static final List<DashboardNavItem> allNavItems = [
    ...coreNavGroups,
    experimentalGroup,
  ].expand((g) => g.items).toList();

  static String getPageTitle(int index) {
    for (final item in allNavItems) {
      if (item.index == index) return item.label;
    }
    return 'COSA OS';
  }

  static bool isItemRecommendedForStage(int index, ProjectStage stage) {
    switch (stage) {
      case ProjectStage.p0Discovery:
      case ProjectStage.p1ProblemValidation:
        return [0, 3, 29, 2, 1, 6].contains(index);
      case ProjectStage.p2SolutionValidation:
        return [0, 3, 29, 31, 2, 1, 6].contains(index);
      case ProjectStage.p3BuildValidate:
        return [0, 3, 29, 21, 23, 1, 6, 2].contains(index);
      case ProjectStage.p4GoToMarket:
        return [0, 17, 23, 20, 28, 3, 29, 1, 6, 2].contains(index);
      case ProjectStage.p5OperateGrowth:
      case ProjectStage.p6ScaleGovern:
        return true;
    }
  }
}
