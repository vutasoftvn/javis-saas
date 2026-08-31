import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/services/feature_flags_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/dashboard_controller.dart';
import '../../models/dashboard_nav_config.dart';
import 'dashboard_stage_demo_bar.dart';

class DashboardDesktopSidebar extends StatelessWidget {
  final DashboardController controller;

  const DashboardDesktopSidebar({super.key, required this.controller});

  List<DashboardNavGroup> _getVisibleNavGroups() {
    final featureFlags = Get.find<FeatureFlagsController>();
    final groups = [
      ...DashboardNavConfig.coreNavGroups,
      if (controller.developerMode.value) DashboardNavConfig.experimentalGroup,
    ];
    return groups
        .map((g) => DashboardNavGroup(
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

  @override
  Widget build(BuildContext context) {
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

            // Stage Context Demo & Policy Bar
            DashboardStageDemoBar(controller: controller),

            const SizedBox(height: 4),
            const Divider(height: 1, color: AppTheme.borderDark),

            // Grouped Accordion Submenu List
            Expanded(
              child: Obx(() {
                final activeIndex = controller.currentIndex.value;
                final expandedGroup = controller.expandedGroupIndex.value;
                final navGroups = _getVisibleNavGroups();

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
                          final isRec = DashboardNavConfig.isItemRecommendedForStage(item.index, stage);
                          final isDimmed = isFiltered && !isRec;

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: DashboardSidebarSubItem(
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
}

class DashboardMobileDrawer extends StatelessWidget {
  final DashboardController controller;

  const DashboardMobileDrawer({super.key, required this.controller});

  List<DashboardNavGroup> _getVisibleNavGroups() {
    final featureFlags = Get.find<FeatureFlagsController>();
    final groups = [
      ...DashboardNavConfig.coreNavGroups,
      if (controller.developerMode.value) DashboardNavConfig.experimentalGroup,
    ];
    return groups
        .map((g) => DashboardNavGroup(
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

  @override
  Widget build(BuildContext context) {
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

            // Return to Hologram Hub Action Tile
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () {
                    Get.back();
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
            DashboardStageDemoBar(controller: controller),
            const SizedBox(height: 4),
            Expanded(
              child: Obx(() {
                final activeIndex = controller.currentIndex.value;
                final expandedGroup = controller.expandedGroupIndex.value;
                final navGroups = _getVisibleNavGroups();

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
                          final isRec = DashboardNavConfig.isItemRecommendedForStage(item.index, stage);
                          final isDimmed = isFiltered && !isRec;

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: DashboardSidebarSubItem(
                              icon: isSelected ? item.selectedIcon : item.icon,
                              label: item.label,
                              isSelected: isSelected,
                              isRecommended: isRec,
                              isDimmed: isDimmed,
                              onTap: () {
                                controller.changePage(item.index, gIndex);
                                Navigator.pop(context);
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
}

class DashboardSidebarSubItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final bool isRecommended;
  final bool isDimmed;

  const DashboardSidebarSubItem({
    super.key,
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.isRecommended = true,
    this.isDimmed = false,
  });

  @override
  Widget build(BuildContext context) {
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
}
