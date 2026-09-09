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
  // Founder Trial R1 — sidebar giữ đúng 5 module: Founder Trial (Chiến lược),
  // CRM, Marketing Pilot, Tài chính, Cài đặt (+ Command Center là entrypoint).
  // Mọi module legacy chỉ còn route PLANNED placeholder, không hiện trên sidebar.
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
        ),
      ],
    ),
    DashboardNavGroup(
      title: 'Đội ngũ AI & Nghiệp vụ',
      titleKey: L10nKey.navGroupAi,
      groupIcon: Icons.groups_outlined,
      items: [
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
      ],
    ),
    DashboardNavGroup(
      title: 'Tài chính',
      titleKey: L10nKey.moduleFinance,
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
      ],
    ),
    DashboardNavGroup(
      title: 'Cài đặt',
      titleKey: L10nKey.navSettings,
      groupIcon: Icons.settings_outlined,
      items: [
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
