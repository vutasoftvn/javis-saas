import 'package:flutter/material.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../data/models/stage_model.dart';

import 'package:get/get.dart';

class DashboardNavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final String? labelKey;
  final int index;
  final String? flagKey;
  final String? moduleKey;

  const DashboardNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    this.labelKey,
    required this.index,
    this.flagKey,
    this.moduleKey,
  });

  String get localizedLabel {
    if (labelKey != null) {
      final translated = labelKey!.tr;
      if (translated != labelKey) {
        return translated;
      }
    }
    return label;
  }
}

class DashboardNavGroup {
  final String title;
  final String? titleKey;
  final IconData groupIcon;
  final List<DashboardNavItem> items;

  const DashboardNavGroup({
    required this.title,
    this.titleKey,
    required this.groupIcon,
    required this.items,
  });

  String get localizedTitle {
    if (titleKey != null) {
      final translated = titleKey!.tr;
      if (translated != titleKey) {
        return translated;
      }
    }
    return title;
  }
}

class DashboardNavConfig {
  static const List<DashboardNavGroup> coreNavGroups = [
    DashboardNavGroup(
      title: 'Hội thoại & Trung tâm',
      titleKey: L10nKey.navGroupConversation,
      groupIcon: Icons.psychology_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.psychology_outlined,
          selectedIcon: Icons.psychology,
          label: 'COSA Command Center',
          labelKey: L10nKey.navCommandCenter,
          index: 0,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Chu kỳ & Chiến lược',
      titleKey: L10nKey.navGroupCycle,
      groupIcon: Icons.flag_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.lightbulb_outline,
          selectedIcon: Icons.lightbulb,
          label: 'Chiến lược',
          labelKey: L10nKey.navStrategy,
          index: 3,
          flagKey: 'strategy_module',
        ),
        DashboardNavItem(
          icon: Icons.rocket_launch_outlined,
          selectedIcon: Icons.rocket_launch,
          label: 'Dự án',
          labelKey: L10nKey.navProjects,
          index: 29,
        ),
        DashboardNavItem(
          icon: Icons.track_changes_outlined,
          selectedIcon: Icons.track_changes,
          label: 'OKRs',
          labelKey: L10nKey.navOkrs,
          index: 27,
        ),
        DashboardNavItem(
          icon: Icons.calendar_month_outlined,
          selectedIcon: Icons.calendar_month,
          label: 'Kế hoạch 12WY',
          labelKey: L10nKey.navTwelveWy,
          index: 28,
        ),
        DashboardNavItem(
          icon: Icons.account_balance_outlined,
          selectedIcon: Icons.account_balance,
          label: 'Nguồn lực & Tài trợ',
          labelKey: L10nKey.navFunding,
          index: 32,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Công việc & Vận hành',
      titleKey: L10nKey.navGroupOperations,
      groupIcon: Icons.work_outline,
      items: [
        DashboardNavItem(
          icon: Icons.check_box_outline_blank,
          selectedIcon: Icons.check_box,
          label: 'Nhiệm vụ',
          labelKey: L10nKey.moduleTasks,
          index: 1,
        ),
        DashboardNavItem(
          icon: Icons.fact_check_outlined,
          selectedIcon: Icons.fact_check,
          label: 'Phê duyệt',
          labelKey: L10nKey.navApprovals,
          index: 6,
        ),
        DashboardNavItem(
          icon: Icons.notification_important_outlined,
          selectedIcon: Icons.notification_important,
          label: 'Cần bạn xử lý',
          labelKey: L10nKey.navNeedsYou,
          index: 24,
          flagKey: 'needs_you_queue_v13_1',
        ),
        DashboardNavItem(
          icon: Icons.block_outlined,
          selectedIcon: Icons.block,
          label: 'Công việc tắc nghẽn',
          labelKey: L10nKey.navBlockedWork,
          index: 25,
          flagKey: 'structured_blocker_v13_1',
        ),
        DashboardNavItem(
          icon: Icons.visibility_outlined,
          selectedIcon: Icons.visibility,
          label: 'Giám sát công việc',
          labelKey: L10nKey.navWorkInspector,
          index: 26,
          flagKey: 'work_inspector_v13_1',
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Đội ngũ AI & Nghiệp vụ',
      titleKey: L10nKey.navGroupAi,
      groupIcon: Icons.groups_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.groups_outlined,
          selectedIcon: Icons.groups,
          label: 'Đội ngũ AI Agents',
          labelKey: L10nKey.navAiAgents,
          index: 7,
        ),
        DashboardNavItem(
          icon: Icons.gavel_outlined,
          selectedIcon: Icons.gavel,
          label: 'Pháp lý',
          labelKey: L10nKey.moduleLegal,
          moduleKey: 'legal',
          index: 22,
        ),
        DashboardNavItem(
          icon: Icons.campaign_outlined,
          selectedIcon: Icons.campaign,
          label: 'Marketing & Lead Gen',
          labelKey: L10nKey.navMarketing,
          index: 17,
        ),
        DashboardNavItem(
          icon: Icons.point_of_sale_rounded,
          selectedIcon: Icons.point_of_sale,
          label: 'Bán hàng & CRM',
          labelKey: L10nKey.moduleCrm,
          moduleKey: 'crm',
          index: 23,
        ),
        DashboardNavItem(
          icon: Icons.psychology_outlined,
          selectedIcon: Icons.psychology,
          label: 'Kỹ năng AI (Skill Registry)',
          labelKey: L10nKey.navSkillRegistry,
          index: 33,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Tài chính & Tri thức',
      titleKey: L10nKey.navGroupFinanceVault,
      groupIcon: Icons.account_balance_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.account_balance_wallet_outlined,
          selectedIcon: Icons.account_balance_wallet,
          label: 'Tài chính',
          labelKey: L10nKey.moduleFinance,
          moduleKey: 'finance',
          index: 21,
        ),
        DashboardNavItem(
          icon: Icons.folder_open,
          selectedIcon: Icons.folder,
          label: 'Kho tri thức',
          labelKey: L10nKey.navVault,
          index: 2,
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Tổ chức & Cài đặt',
      titleKey: L10nKey.navGroupOrganization,
      groupIcon: Icons.settings_outlined,
      items: [
        DashboardNavItem(
          icon: Icons.corporate_fare_outlined,
          selectedIcon: Icons.corporate_fare,
          label: 'Sơ đồ tổ chức',
          labelKey: L10nKey.navOrgChart,
          index: 19,
          flagKey: 'advanced_org_chart_v13',
        ),
        DashboardNavItem(
          icon: Icons.account_tree_outlined,
          selectedIcon: Icons.account_tree,
          label: 'Quy trình',
          labelKey: L10nKey.navWorkflows,
          index: 5,
        ),
        DashboardNavItem(
          icon: Icons.tune_rounded,
          selectedIcon: Icons.tune,
          label: 'Quản trị Template',
          labelKey: L10nKey.navTemplates,
          index: 30,
        ),
        DashboardNavItem(
          icon: Icons.settings_outlined,
          selectedIcon: Icons.settings,
          label: 'Cài đặt',
          labelKey: L10nKey.navSettings,
          index: 13,
        ),
      ],
    ),
  ];

  static const DashboardNavGroup experimentalGroup = DashboardNavGroup(
    title: 'Tính năng thử nghiệm',
    titleKey: L10nKey.navGroupExperimental,
    groupIcon: Icons.science_outlined,
    items: [
      DashboardNavItem(
        icon: Icons.account_tree_outlined,
        selectedIcon: Icons.account_tree,
        label: 'Quy trình nâng cao',
        labelKey: L10nKey.navAdvancedWorkflows,
        index: 5,
      ),
      DashboardNavItem(
        icon: Icons.corporate_fare_outlined,
        selectedIcon: Icons.corporate_fare,
        label: 'Sơ đồ tổ chức chi tiết',
        labelKey: L10nKey.navAdvancedOrgChart,
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
      if (item.index == index) return item.localizedLabel;
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
