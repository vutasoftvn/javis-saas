import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/routing/app_routes.dart';
import '../../hologram_hub/views/hologram_hub_view.dart';
import '../../tasks/views/tasks_view.dart';
import '../../vault/views/vault_view.dart';
import '../../strategy/views/strategy_view.dart';
import '../../strategy/views/okrs_view.dart';
import '../../strategy/views/twelve_week_year_view.dart';
import '../../strategy/views/project_roadmap_view.dart';
import '../../strategy/views/project_funding_view.dart';
import '../../strategy/views/template_library_view.dart';
import '../../workflows/views/workflows_view.dart';
import '../../approvals/views/approvals_view.dart';
import '../../agents/views/agents_view.dart';
import '../../settings/views/settings_view.dart';
import '../../skills/views/skill_registry_view.dart';
import '../../marketing/views/marketing_cockpit_view.dart';
import '../../organization/views/organization_view.dart';
import '../../finance/views/finance_view.dart';
import '../../legal/views/legal_view.dart';
import '../../sales/views/sales_view.dart';
import '../../workspace_runtime/views/needs_you_view.dart';
import '../../workspace_runtime/views/blocked_work_view.dart';
import '../../workspace_runtime/views/work_inspector_view.dart';
import '../../../core/services/feature_flags_controller.dart';
import '../../../shared/widgets/feature_not_enabled_view.dart';
import '../../../data/models/stage_model.dart';
import '../../../shared/widgets/stage_badge.dart';
import 'widgets/floating_voice_hologram.dart';

class _NavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final int index;
  final String? flagKey;

  const _NavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.index,
    this.flagKey,
  });
}

class _NavGroup {
  final String title;
  final IconData groupIcon;
  final List<_NavItem> items;

  const _NavGroup({
    required this.title,
    required this.groupIcon,
    required this.items,
  });
}

class DashboardView extends GetView<DashboardController> {
  const DashboardView({super.key});

  static const List<_NavGroup> _coreNavGroups = [
    _NavGroup(
      title: 'Hội thoại & Trung tâm',
      groupIcon: Icons.psychology_outlined,
      items: [
        _NavItem(icon: Icons.psychology_outlined, selectedIcon: Icons.psychology, label: 'COSA Command Center', index: 0),
      ],
    ),
    _NavGroup(
      title: 'Chu kỳ & Chiến lược', groupIcon: Icons.flag_outlined,
      items: [
        _NavItem(icon: Icons.lightbulb_outline, selectedIcon: Icons.lightbulb, label: 'Chiến lược', index: 3, flagKey: 'strategy_module'),
        _NavItem(icon: Icons.rocket_launch_outlined, selectedIcon: Icons.rocket_launch, label: 'Dự án', index: 29),
        _NavItem(icon: Icons.track_changes_outlined, selectedIcon: Icons.track_changes, label: 'OKRs', index: 27),
        _NavItem(icon: Icons.calendar_month_outlined, selectedIcon: Icons.calendar_month, label: 'Kế hoạch 12WY', index: 28),
        _NavItem(icon: Icons.account_balance_outlined, selectedIcon: Icons.account_balance, label: 'Nguồn lực & Tài trợ', index: 32),
      ],
    ),
    _NavGroup(
      title: 'Công việc & Vận hành', groupIcon: Icons.work_outline,
      items: [
        _NavItem(icon: Icons.check_box_outline_blank, selectedIcon: Icons.check_box, label: 'Nhiệm vụ', index: 1),
        _NavItem(icon: Icons.fact_check_outlined, selectedIcon: Icons.fact_check, label: 'Phê duyệt', index: 6),
        _NavItem(icon: Icons.notification_important_outlined, selectedIcon: Icons.notification_important, label: 'Cần bạn xử lý', index: 24, flagKey: 'needs_you_queue_v13_1'),
        _NavItem(icon: Icons.block_outlined, selectedIcon: Icons.block, label: 'Công việc tắc nghẽn', index: 25, flagKey: 'structured_blocker_v13_1'),
        _NavItem(icon: Icons.visibility_outlined, selectedIcon: Icons.visibility, label: 'Giám sát công việc', index: 26, flagKey: 'work_inspector_v13_1'),
      ],
    ),
    _NavGroup(
      title: 'Đội ngũ AI & Nghiệp vụ', groupIcon: Icons.groups_outlined,
      items: [
        _NavItem(icon: Icons.groups_outlined, selectedIcon: Icons.groups, label: 'Đội ngũ AI Agents', index: 7),
        _NavItem(icon: Icons.gavel_outlined, selectedIcon: Icons.gavel, label: 'Pháp lý & Hợp đồng AI', index: 22),
        _NavItem(icon: Icons.campaign_outlined, selectedIcon: Icons.campaign, label: 'Marketing & Lead Gen', index: 17),
        _NavItem(icon: Icons.point_of_sale_rounded, selectedIcon: Icons.point_of_sale, label: 'Bán hàng & CRM', index: 23),
        _NavItem(icon: Icons.psychology_outlined, selectedIcon: Icons.psychology, label: 'Kỹ năng AI (Skill Registry)', index: 33),
      ],
    ),
    _NavGroup(
      title: 'Tài chính & Tri thức', groupIcon: Icons.account_balance_outlined,
      items: [
        _NavItem(icon: Icons.account_balance_wallet_outlined, selectedIcon: Icons.account_balance_wallet, label: 'Kế toán & Tài chính', index: 21),
        _NavItem(icon: Icons.folder_open, selectedIcon: Icons.folder, label: 'Kho tri thức', index: 2),
      ],
    ),
    _NavGroup(title: 'Tổ chức & Cài đặt', groupIcon: Icons.settings_outlined, items: [
      _NavItem(icon: Icons.corporate_fare_outlined, selectedIcon: Icons.corporate_fare, label: 'Sơ đồ tổ chức', index: 19, flagKey: 'advanced_org_chart_v13'),
      _NavItem(icon: Icons.account_tree_outlined, selectedIcon: Icons.account_tree, label: 'Quy trình', index: 5),
      _NavItem(icon: Icons.tune_rounded, selectedIcon: Icons.tune, label: 'Quản trị Template', index: 30),
      _NavItem(icon: Icons.settings_outlined, selectedIcon: Icons.settings, label: 'Cài đặt', index: 13),
    ]),
  ];

  static const _experimentalGroup = _NavGroup(title: 'Tính năng thử nghiệm', groupIcon: Icons.science_outlined, items: [
    _NavItem(icon: Icons.account_tree_outlined, selectedIcon: Icons.account_tree, label: 'Quy trình nâng cao', index: 5),
    _NavItem(icon: Icons.corporate_fare_outlined, selectedIcon: Icons.corporate_fare, label: 'Sơ đồ tổ chức chi tiết', index: 19, flagKey: 'advanced_org_chart_v13'),
  ]);

  static final List<_NavItem> _allNavItems = [..._coreNavGroups, _experimentalGroup].expand((g) => g.items).toList();

  List<_NavGroup> get _visibleNavGroups {
    final featureFlags = Get.find<FeatureFlagsController>();
    final groups = [..._coreNavGroups, if (controller.developerMode.value) _experimentalGroup];
    return groups
        .map((g) => _NavGroup(
              title: g.title,
              groupIcon: g.groupIcon,
              items: g.items.where((i) {
                final flagVisible = i.flagKey == null || featureFlags.isEnabled(i.flagKey!);
                return flagVisible;
              }).toList(),
            ))
        .where((g) => g.items.isNotEmpty)
        .toList();
  }

  String _getPageTitle(int index) {
    for (final item in _allNavItems) {
      if (item.index == index) return item.label;
    }
    return 'COSA OS';
  }

  @override
  Widget build(BuildContext context) {
    final bool isDesktop = MediaQuery.of(context).size.width >= 800;

    if (isDesktop) {
      return Scaffold(
        body: Container(
          decoration: const BoxDecoration(
            gradient: AppTheme.backgroundLinearGradient,
          ),
          child: Stack(
            children: [
              Padding(
                padding: const EdgeInsets.all(12.0),
                child: Row(
                  children: [
                    _buildDesktopSidebar(context),
                    const SizedBox(width: 12),
                    Expanded(child: _buildBodyContent()),
                  ],
                ),
              ),
              const FloatingVoiceHologram(),
            ],
          ),
        ),
      );
    }

    // Mobile layout
    final GlobalKey<ScaffoldState> scaffoldKey = GlobalKey<ScaffoldState>();

    return Scaffold(
      key: scaffoldKey,
      drawer: _buildDrawer(context),
      appBar: _buildMobileAppBar(scaffoldKey),
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: AppTheme.backgroundLinearGradient,
            ),
            child: _buildBodyContent(),
          ),
          const FloatingVoiceHologram(),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildMobileAppBar(GlobalKey<ScaffoldState> scaffoldKey) {
    return AppBar(
      backgroundColor: AppTheme.surfaceDarkHeader,
      elevation: 0,
      leading: IconButton(
        icon: const Icon(Icons.menu_rounded, color: Colors.white),
        onPressed: () => scaffoldKey.currentState?.openDrawer(),
      ),
      title: Obx(() {
        final idx = controller.currentIndex.value;
        return Text(
          _getPageTitle(idx),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
        );
      }),
      actions: [
        TextButton.icon(
          onPressed: () => Get.offNamed(AppRoutes.hub),
          icon: const Icon(Icons.psychology, size: 20, color: Color(0xFF14B8A6)),
          label: const Text(
            'Hologram',
            style: TextStyle(
              color: Color(0xFF14B8A6),
              fontSize: 13,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(width: 6),
      ],
      bottom: const PreferredSize(
        preferredSize: Size.fromHeight(1),
        child: Divider(height: 1, thickness: 1, color: AppTheme.borderDark),
      ),
    );
  }

  bool _isItemRecommendedForStage(int index, ProjectStage stage) {
    switch (stage) {
      case ProjectStage.p0Discovery:
      case ProjectStage.p1ProblemValidation:
        // P0/P1: Chat(0), Chiến lược - Evidence/Problem(3), Dự án(29), Kho tri thức(2), Nhiệm vụ(1), Phê duyệt(6)
        return [0, 3, 29, 2, 1, 6].contains(index);
      case ProjectStage.p2SolutionValidation:
        // P2: Chat(0), Chiến lược - MVP/Pricing(3), Dự án(29), Vận hành AI(31), Kho tri thức(2), Nhiệm vụ(1), Phê duyệt(6)
        return [0, 3, 29, 31, 2, 1, 6].contains(index);
      case ProjectStage.p3BuildValidate:
        // P3: Chat(0), Chiến lược - Unit Econ(3), Dự án(29), Kế toán(21), Bán hàng(23), Nhiệm vụ(1), Phê duyệt(6), Kho tri thức(2)
        return [0, 3, 29, 21, 23, 1, 6, 2].contains(index);
      case ProjectStage.p4GoToMarket:
        // P4: Marketing(17), Bán hàng/CRM(23), Đội ngũ AI(20), Kế hoạch(28), Chiến lược(3), Dự án(29), Tasks(1), Approvals(6)
        return [0, 17, 23, 20, 28, 3, 29, 1, 6, 2].contains(index);
      case ProjectStage.p5OperateGrowth:
      case ProjectStage.p6ScaleGovern:
        // P5/P6: Tất cả đều ưu tiên
        return true;
    }
  }

  Widget _buildStageDemoBar(BuildContext context) {
    return Obx(() {
      final stage = controller.selectedStage.value;
      final isFiltered = controller.isStageFilteringEnabled.value;
      return Container(
        margin: const EdgeInsets.fromLTRB(14, 2, 14, 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: stage.primaryColor.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: stage.primaryColor.withValues(alpha: 0.35),
            width: 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Row 1: Stage Badge + Demo Switcher Dropdown
            Row(
              children: [
                Icon(stage.icon, size: 14, color: stage.primaryColor),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Demo Stage: ${stage.code}',
                    style: TextStyle(
                      color: stage.primaryColor,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                PopupMenuButton<ProjectStage>(
                  tooltip: 'Chuyển đổi Stage để Test',
                  padding: EdgeInsets.zero,
                  color: const Color(0xFF0F172A),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: const BorderSide(color: Color(0xFF1E293B)),
                  ),
                  onSelected: controller.setDemoStage,
                  itemBuilder: (ctx) => ProjectStage.values.map((s) {
                    final isCurrent = s == stage;
                    return PopupMenuItem<ProjectStage>(
                      value: s,
                      child: Row(
                        children: [
                          StageBadge(stage: s, isCompact: true),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              s.displayNameVi,
                              style: TextStyle(
                                color: isCurrent ? s.primaryColor : Colors.white,
                                fontSize: 12,
                                fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                              ),
                            ),
                          ),
                          if (isCurrent) ...[
                            const SizedBox(width: 4),
                            Icon(Icons.check, size: 14, color: s.primaryColor),
                          ],
                        ],
                      ),
                    );
                  }).toList(),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                    decoration: BoxDecoration(
                      color: stage.primaryColor.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: stage.primaryColor.withValues(alpha: 0.4), width: 0.8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Đổi Stage',
                          style: TextStyle(color: stage.primaryColor, fontSize: 10.5, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(width: 2),
                        Icon(Icons.keyboard_arrow_down_rounded, size: 14, color: stage.primaryColor),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 5),

            // Row 2: Filter Toggle Switch
            InkWell(
              onTap: controller.toggleStageFiltering,
              borderRadius: BorderRadius.circular(6),
              child: Row(
                children: [
                  Icon(
                    isFiltered ? Icons.filter_alt_outlined : Icons.filter_alt_off_outlined,
                    size: 13,
                    color: isFiltered ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      isFiltered ? 'Lọc ưu tiên Stage ${stage.code}' : 'Hiện tất cả (Không lọc)',
                      style: TextStyle(
                        color: isFiltered ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                        fontSize: 10.5,
                        fontWeight: isFiltered ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                  ),
                  SizedBox(
                    height: 18,
                    width: 30,
                    child: Transform.scale(
                      scale: 0.65,
                      child: Switch(
                        value: isFiltered,
                        onChanged: (_) => controller.toggleStageFiltering(),
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        activeThumbColor: const Color(0xFF10B981),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildDesktopSidebar(BuildContext context) {
    return Container(
      width: 300,
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderDark, width: 1.0),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 20,
            spreadRadius: 2,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            // Logo Header
            Padding(
              padding: const EdgeInsets.only(bottom: 12, top: 20, left: 16, right: 16),
              child: InkWell(
                onTap: () => Get.offNamed(AppRoutes.hub),
                borderRadius: BorderRadius.circular(10),
                child: Padding(
                  padding: const EdgeInsets.all(4.0),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
                        ),
                        child: const Icon(Icons.psychology, size: 26, color: AppTheme.primary),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'COSA OS',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                                letterSpacing: 1.2,
                              ),
                            ),
                            Text(
                              'AI Business Suite',
                              style: TextStyle(
                                fontSize: 11.5,
                                color: AppTheme.textMutedDark,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            // Return to Hub Action Tile
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => Get.offNamed(AppRoutes.hub),
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
                    ),
                    child: Row(
                      children: const [
                        Icon(Icons.arrow_back, size: 16, color: AppTheme.primary),
                        SizedBox(width: 8),
                        Text(
                          'COSA Hologram Hub',
                          style: TextStyle(
                            color: AppTheme.primary,
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 6),

            // Phase 6: Stage Context Demo & Policy Bar
            _buildStageDemoBar(context),

            const SizedBox(height: 4),
            const Divider(height: 1, color: AppTheme.borderDark),

            // Grouped Accordion Submenu List (Text menu tiêu đề nhóm bằng 15.5pt đậm hơn submenu 15pt)
            Expanded(
              child: Obx(() {
                final activeIndex = controller.currentIndex.value;
                final expandedGroup = controller.expandedGroupIndex.value;
                final navGroups = _visibleNavGroups;

                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  itemCount: navGroups.length,
                  itemBuilder: (context, gIndex) {
                    final group = navGroups[gIndex];
                    final hasSubItems = group.items.length > 1;

                    if (!hasSubItems) {
                      final item = group.items.first;
                      final isSelected = activeIndex == item.index;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () => controller.changePage(item.index, gIndex),
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(8),
                                color: isSelected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
                                border: isSelected
                                    ? Border.all(color: AppTheme.primary.withValues(alpha: 0.35))
                                    : Border.all(color: Colors.transparent),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    group.groupIcon,
                                    size: 22,
                                    color: isSelected ? AppTheme.primary : AppTheme.textDark,
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Text(
                                      group.title,
                                      maxLines: 1,
                                      softWrap: false,
                                      overflow: TextOverflow.fade,
                                      style: TextStyle(
                                        fontSize: 15.5,
                                        fontWeight: FontWeight.bold,
                                        color: isSelected ? AppTheme.primary : AppTheme.textDark,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    }

                    final isExpanded = expandedGroup == gIndex;
                    final hasActiveChild = group.items.any((item) => item.index == activeIndex);

                    return Theme(
                      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                      child: ExpansionTile(
                        key: Key('desktop_group_${gIndex}_$isExpanded'),
                        initiallyExpanded: isExpanded,
                        onExpansionChanged: (expanding) {
                          if (expanding) {
                            controller.expandedGroupIndex.value = gIndex;
                          } else {
                            if (controller.expandedGroupIndex.value == gIndex) {
                              controller.expandedGroupIndex.value = -1;
                            }
                          }
                        },
                        tilePadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        childrenPadding: const EdgeInsets.only(left: 12, bottom: 6),
                        leading: Icon(
                          group.groupIcon,
                          size: 22,
                          color: (isExpanded || hasActiveChild) ? AppTheme.primary : AppTheme.textDark,
                        ),
                        title: Text(
                          group.title,
                          maxLines: 1,
                          softWrap: false,
                          style: TextStyle(
                            fontSize: 15.5,
                            fontWeight: FontWeight.bold,
                            color: (isExpanded || hasActiveChild) ? AppTheme.primary : AppTheme.textDark,
                          ),
                        ),
                        trailing: Icon(
                          Icons.keyboard_arrow_down_rounded,
                          size: 20,
                          color: (isExpanded || hasActiveChild) ? AppTheme.primary : AppTheme.textMutedDark,
                        ),
                        children: group.items.map((item) {
                          final isSelected = activeIndex == item.index;
                          final stage = controller.selectedStage.value;
                          final isFiltered = controller.isStageFilteringEnabled.value;
                          final isRec = _isItemRecommendedForStage(item.index, stage);
                          final isDimmed = isFiltered && !isRec;

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: _buildSidebarSubItem(
                              icon: isSelected ? item.selectedIcon : item.icon,
                              label: item.label,
                              isSelected: isSelected,
                              isRecommended: isRec,
                              isDimmed: isDimmed,
                              onTap: () => controller.changePage(item.index, gIndex),
                            ),
                          );
                        }).toList(),
                      ),
                    );
                  },
                );
              }),
            ),

            // Footer Logout Button
            const Divider(height: 1, color: AppTheme.borderDark),
            Obx(() => SwitchListTile(
              dense: true,
              title: const Text('Chế độ nhà phát triển', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
              value: controller.developerMode.value,
              onChanged: controller.setDeveloperMode,
            )),
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: controller.logout,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: Row(
                    children: const [
                      Icon(Icons.logout_rounded, color: AppTheme.error, size: 20),
                      SizedBox(width: 12),
                      Text(
                        'Đăng xuất',
                        style: TextStyle(color: AppTheme.error, fontSize: 15, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSidebarSubItem({
    required IconData icon,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    bool isRecommended = true,
    bool isDimmed = false,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            color: isSelected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
            border: isSelected
                ? Border.all(color: AppTheme.primary.withValues(alpha: 0.35))
                : Border.all(color: Colors.transparent),
          ),
          child: Opacity(
            opacity: isDimmed ? 0.55 : 1.0,
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 19,
                  color: isSelected
                      ? AppTheme.primary
                      : (isRecommended ? const Color(0xFF38BDF8) : AppTheme.textMutedDark),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    label,
                    maxLines: 1,
                    softWrap: false,
                    overflow: TextOverflow.fade,
                    style: TextStyle(
                      fontSize: 14.5,
                      fontWeight: isSelected
                          ? FontWeight.bold
                          : (isRecommended ? FontWeight.w600 : FontWeight.normal),
                      color: isSelected
                          ? Colors.white
                          : (isRecommended
                              ? Colors.white.withValues(alpha: 0.95)
                              : AppTheme.textDark.withValues(alpha: 0.7)),
                    ),
                  ),
                ),
                if (isRecommended && !isDimmed) ...[
                  const SizedBox(width: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: const Color(0xFF10B981).withValues(alpha: 0.3),
                        width: 0.6,
                      ),
                    ),
                    child: const Text(
                      'Ưu tiên',
                      style: TextStyle(
                        color: Color(0xFF10B981),
                        fontSize: 9.5,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ] else if (isDimmed) ...[
                  const SizedBox(width: 4),
                  Text(
                    'Sau',
                    style: TextStyle(
                      color: AppTheme.textMutedDark.withValues(alpha: 0.7),
                      fontSize: 9.5,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context) {
    return Drawer(
      backgroundColor: AppTheme.surfaceDark,
      child: SafeArea(
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
                    ),
                    child: const Icon(Icons.psychology, size: 30, color: AppTheme.primary),
                  ),
                  const SizedBox(width: 14),
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'COSA OS',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                          letterSpacing: 1.2,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'AI Business Operations',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppTheme.textMutedDark,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Return to Hologram Hub Action Tile for Mobile Drawer
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () {
                    Get.back(); // close drawer
                    Get.offNamed(AppRoutes.hub);
                  },
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
                    ),
                    child: Row(
                      children: const [
                        Icon(Icons.arrow_back, size: 18, color: AppTheme.primary),
                        SizedBox(width: 10),
                        Text(
                          'Về COSA Hologram Hub',
                          style: TextStyle(
                            color: AppTheme.primary,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 6),
            _buildStageDemoBar(context),
            const SizedBox(height: 4),
            Expanded(
              child: Obx(() {
                final activeIndex = controller.currentIndex.value;
                final expandedGroup = controller.expandedGroupIndex.value;
                final navGroups = _visibleNavGroups;

                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  itemCount: navGroups.length,
                  itemBuilder: (context, gIndex) {
                    final group = navGroups[gIndex];
                    final hasSubItems = group.items.length > 1;

                    if (!hasSubItems) {
                      final item = group.items.first;
                      final isSelected = activeIndex == item.index;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () {
                              controller.changePage(item.index, gIndex);
                              Navigator.pop(context);
                            },
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(8),
                                color: isSelected ? AppTheme.primaryLight.withValues(alpha: 0.15) : Colors.transparent,
                                border: isSelected
                                    ? Border.all(color: AppTheme.primaryLight.withValues(alpha: 0.35))
                                    : Border.all(color: Colors.transparent),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    group.groupIcon,
                                    size: 22,
                                    color: isSelected ? AppTheme.primaryLight : AppTheme.textDark,
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Text(
                                      group.title,
                                      maxLines: 1,
                                      softWrap: false,
                                      overflow: TextOverflow.fade,
                                      style: TextStyle(
                                        fontSize: 15.5,
                                        fontWeight: FontWeight.bold,
                                        color: isSelected ? AppTheme.primaryLight : AppTheme.textDark,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    }

                    final isExpanded = expandedGroup == gIndex;
                    final hasActiveChild = group.items.any((item) => item.index == activeIndex);

                    return Theme(
                      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                      child: ExpansionTile(
                        key: Key('mobile_group_${gIndex}_$isExpanded'),
                        initiallyExpanded: isExpanded,
                        onExpansionChanged: (expanding) {
                          if (expanding) {
                            controller.expandedGroupIndex.value = gIndex;
                          } else {
                            if (controller.expandedGroupIndex.value == gIndex) {
                              controller.expandedGroupIndex.value = -1;
                            }
                          }
                        },
                        tilePadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        childrenPadding: const EdgeInsets.only(left: 12, bottom: 6),
                        leading: Icon(
                          group.groupIcon,
                          size: 22,
                          color: (isExpanded || hasActiveChild) ? AppTheme.primaryLight : AppTheme.textDark,
                        ),
                        title: Text(
                          group.title,
                          maxLines: 1,
                          softWrap: false,
                          style: TextStyle(
                            fontSize: 15.5,
                            fontWeight: FontWeight.bold,
                            color: (isExpanded || hasActiveChild) ? AppTheme.primaryLight : AppTheme.textDark,
                          ),
                        ),
                        trailing: Icon(
                          Icons.keyboard_arrow_down_rounded,
                          size: 20,
                          color: (isExpanded || hasActiveChild) ? AppTheme.primaryLight : AppTheme.textMutedDark,
                        ),
                        children: group.items.map((item) {
                          final isSelected = activeIndex == item.index;
                          final stage = controller.selectedStage.value;
                          final isFiltered = controller.isStageFilteringEnabled.value;
                          final isRec = _isItemRecommendedForStage(item.index, stage);
                          final isDimmed = isFiltered && !isRec;

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: _buildSidebarSubItem(
                              icon: isSelected ? item.selectedIcon : item.icon,
                              label: item.label,
                              isSelected: isSelected,
                              isRecommended: isRec,
                              isDimmed: isDimmed,
                              onTap: () {
                                controller.changePage(item.index, gIndex);
                                Navigator.pop(context); // Close drawer
                              },
                            ),
                          );
                        }).toList(),
                      ),
                    );
                  },
                );
              }),
            ),
            const Divider(height: 1, color: Color(0xFF1E293B)),
            ListTile(
              leading: const Icon(Icons.logout, color: AppTheme.error),
              title: const Text('Đăng xuất', style: TextStyle(color: AppTheme.error, fontWeight: FontWeight.bold, fontSize: 15)),
              onTap: () {
                Navigator.pop(context);
                controller.logout();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBodyContent() {
    return Obx(() {
      final index = controller.currentIndex.value;
      final item = _allNavItems.firstWhereOrNull((candidate) => candidate.index == index);
      if (item?.flagKey != null &&
          !Get.find<FeatureFlagsController>().isEnabled(item!.flagKey!)) {
        return FeatureNotEnabledView(featureName: item.label);
      }
      try {
        return _buildFeatureView(index);
      } catch (e) {
        return _errorView(e.toString());
      }
    });
  }

  Widget _buildFeatureView(int index) {
    switch (index) {
      case 0:
        return const HologramHubView();
      case 1:
        return const TasksView();
      case 2:
        return const VaultView();
      case 3:
        return StrategyView(
          key: ValueKey('strategy_view_${controller.strategyInitialTabIndex.value}'),
          initialTabIndex: controller.strategyInitialTabIndex.value,
        );
      case 5:
        return const WorkflowsView();
      case 6:
        return const ApprovalsView();
      case 7:
        return const AgentsView();
      case 13:
        return const SettingsView();
      case 17:
        return const MarketingCockpitView();
      case 19:
        return const OrganizationView();
      case 21:
        return const FinanceView();
      case 22:
        return const LegalView();
      case 23:
        return const SalesView();
      case 24:
        return const NeedsYouView();
      case 25:
        return const BlockedWorkView();
      case 26:
        return const WorkInspectorView();
      case 27:
        return const OkrsView();
      case 28:
        return const TwelveWeekYearView();
      case 29:
        return const ProjectRoadmapView();
      case 30:
        return const TemplateLibraryView();
      case 32:
        return const ProjectFundingView();
      case 33:
        return const SkillRegistryView();
      default:
        return const HologramHubView();
    }
  }

  Widget _errorView(String error) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.error, size: 48),
              const SizedBox(height: 16),
              Text(
                'Không thể tải tính năng:\n$error',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.error, fontSize: 14),
              ),
            ],
          ),
        ),
      );
}
