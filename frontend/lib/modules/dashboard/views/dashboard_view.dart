import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/dashboard_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/routing/app_routes.dart';
import '../../chat/views/chat_view.dart';
import '../../chat/controllers/chat_controller.dart';
import '../../tasks/views/tasks_view.dart';
import '../../vault/views/vault_view.dart';
import '../../strategy/views/strategy_view.dart';
import '../../usage/views/usage_view.dart';
import '../../workflows/views/workflows_view.dart';
import '../../approvals/views/approvals_view.dart';
import '../../agents/views/agents_view.dart';
import '../../connections/views/connections_view.dart';
import '../../plugins/views/plugins_view.dart';
import '../../audit/views/audit_view.dart';
import '../../channels/views/channels_view.dart';
import '../../chatbots/views/chatbots_view.dart';
import '../../settings/views/settings_view.dart';
import '../../branding/views/branding_view.dart';
import '../../backup/views/backup_view.dart';
import '../../diagnostics/views/diagnostics_view.dart';
import '../../marketing/views/marketing_cockpit_view.dart';
import '../../developer/views/developer_view.dart';
import '../../organization/views/organization_view.dart';

class _NavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final int index;
  final bool desktopOnly;

  const _NavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.index,
    this.desktopOnly = false,
  });
}

// The Local Worker Plane (Claude Code CLI + git worktree, blueprint Phase 5)
// is a native desktop concept - a web/mobile session has no filesystem/CLI
// to run it against, so the Developer nav item must not appear there
// (roadmap Phase 5: "mobile build only ever shows job status/approval...
// never talks to the Local Worker Plane directly").
bool get _isNativeDesktopPlatform =>
    !kIsWeb && (Platform.isMacOS || Platform.isWindows || Platform.isLinux);

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

  static const List<_NavGroup> _navGroups = [
    _NavGroup(
      title: 'Tương tác & AI',
      groupIcon: Icons.forum_outlined,
      items: [
        _NavItem(icon: Icons.chat_bubble_outline, selectedIcon: Icons.chat_bubble, label: 'Nhắn tin', index: 0),
        _NavItem(icon: Icons.smart_toy_outlined, selectedIcon: Icons.smart_toy, label: 'Agents AI', index: 7),
        _NavItem(icon: Icons.support_agent_outlined, selectedIcon: Icons.support_agent, label: 'Chatbots (Zalo/TG)', index: 12),
      ],
    ),
    _NavGroup(
      title: 'Vận hành & công việc',
      groupIcon: Icons.work_outline,
      items: [
        _NavItem(icon: Icons.check_box_outline_blank, selectedIcon: Icons.check_box, label: 'Công việc', index: 1),
        _NavItem(icon: Icons.account_tree_outlined, selectedIcon: Icons.account_tree, label: 'Workflows', index: 5),
        _NavItem(icon: Icons.fact_check_outlined, selectedIcon: Icons.fact_check, label: 'Duyệt', index: 6),
        _NavItem(icon: Icons.developer_mode_outlined, selectedIcon: Icons.developer_mode, label: 'Lập trình (Dev)', index: 18, desktopOnly: true),
        _NavItem(icon: Icons.corporate_fare_outlined, selectedIcon: Icons.corporate_fare, label: 'Tổ chức & Nhân sự', index: 19),
      ],
    ),
    _NavGroup(
      title: 'Tri thức & chiến lược',
      groupIcon: Icons.auto_stories_outlined,
      items: [
        _NavItem(icon: Icons.folder_open, selectedIcon: Icons.folder, label: 'Lưu trữ (Vault)', index: 2),
        _NavItem(icon: Icons.flag_outlined, selectedIcon: Icons.flag, label: 'Chiến lược & OKRs', index: 3),
        _NavItem(icon: Icons.campaign_outlined, selectedIcon: Icons.campaign, label: 'Marketing OS', index: 17),
      ],
    ),
    _NavGroup(
      title: 'Tích hợp & mở rộng',
      groupIcon: Icons.hub_outlined,
      items: [
        _NavItem(icon: Icons.power_outlined, selectedIcon: Icons.power, label: 'Kết nối (MCP)', index: 8),
        _NavItem(icon: Icons.extension_outlined, selectedIcon: Icons.extension, label: 'Plugins', index: 9),
        _NavItem(icon: Icons.chat_outlined, selectedIcon: Icons.chat, label: 'Kênh kết nối', index: 11),
      ],
    ),
    _NavGroup(
      title: 'Hệ thống & cài đặt',
      groupIcon: Icons.settings_applications_outlined,
      items: [
        _NavItem(icon: Icons.bar_chart_outlined, selectedIcon: Icons.bar_chart, label: 'Sử dụng AI', index: 4),
        _NavItem(icon: Icons.history_outlined, selectedIcon: Icons.history, label: 'Nhật ký audit', index: 10),
        _NavItem(icon: Icons.palette_outlined, selectedIcon: Icons.palette, label: 'Thương hiệu', index: 14),
        _NavItem(icon: Icons.backup_outlined, selectedIcon: Icons.backup, label: 'Sao lưu', index: 15),
        _NavItem(icon: Icons.monitor_heart_outlined, selectedIcon: Icons.monitor_heart, label: 'Chẩn đoán', index: 16),
        _NavItem(icon: Icons.settings_outlined, selectedIcon: Icons.settings, label: 'Cài đặt chung', index: 13),
      ],
    ),
  ];

  static final List<_NavItem> _allNavItems = _navGroups.expand((g) => g.items).toList();

  static List<_NavGroup> get _visibleNavGroups {
    final isDesktop = _isNativeDesktopPlatform;
    return _navGroups
        .map((g) => _NavGroup(
              title: g.title,
              groupIcon: g.groupIcon,
              items: g.items.where((i) => !i.desktopOnly || isDesktop).toList(),
            ))
        .where((g) => g.items.isNotEmpty)
        .toList();
  }

  String _getPageTitle(int index) {
    for (final item in _allNavItems) {
      if (item.index == index) return item.label;
    }
    return 'Javis OS';
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
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              children: [
                _buildDesktopSidebar(context),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildBodyContent(),
                ),
              ],
            ),
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
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppTheme.backgroundLinearGradient,
        ),
        child: _buildBodyContent(),
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
        if (idx == 0 && Get.isRegistered<ChatController>()) {
          final chatCtrl = Get.find<ChatController>();
          return Obx(() {
            final selected = chatCtrl.selectedModel.value;
            final options = chatCtrl.models;
            final label = selected != null
                ? (selected['label'] as String? ?? '${selected['provider']} · ${selected['model']}')
                : 'Chọn model...';
            if (options.isEmpty) {
              return Text(label, style: const TextStyle(fontSize: 14, color: AppTheme.textMutedDark));
            }
            return PopupMenuButton<Map<String, dynamic>>(
              tooltip: 'Đổi model',
              padding: EdgeInsets.zero,
              color: AppTheme.surfaceDark,
              onSelected: chatCtrl.selectModel,
              itemBuilder: (context) => options.cast<Map<String, dynamic>>().map((m) {
                final configured = m['configured'] == true;
                return PopupMenuItem<Map<String, dynamic>>(
                  value: m,
                  child: Row(
                    children: [
                      Icon(
                        configured ? Icons.check_circle : Icons.remove_circle_outline,
                        size: 15,
                        color: configured ? AppTheme.success : AppTheme.textMutedDark,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          m['label'] as String? ?? '${m['provider']} · ${m['model']}',
                          style: TextStyle(
                            color: configured ? AppTheme.textDark : AppTheme.textMutedDark,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(label, style: const TextStyle(fontSize: 15, color: Colors.white)),
                  const SizedBox(width: 4),
                  const Icon(Icons.expand_more, size: 18, color: AppTheme.textMutedDark),
                ],
              ),
            );
          });
        }
        return Text(
          _getPageTitle(idx),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
        );
      }),
      bottom: const PreferredSize(
        preferredSize: Size.fromHeight(1),
        child: Divider(height: 1, thickness: 1, color: AppTheme.borderDark),
      ),
    );
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
                              'JAVIS OS',
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
            const SizedBox(height: 8),
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
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: _buildSidebarSubItem(
                              icon: isSelected ? item.selectedIcon : item.icon,
                              label: item.label,
                              isSelected: isSelected,
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
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
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
                icon,
                size: 20,
                color: isSelected ? AppTheme.primary : AppTheme.textMutedDark,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  softWrap: false,
                  overflow: TextOverflow.fade,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? Colors.white : AppTheme.textDark.withValues(alpha: 0.9),
                  ),
                ),
              ),
            ],
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
                        'JAVIS OS',
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
                        children: group.items.map((item) {
                          final isSelected = activeIndex == item.index;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: _buildSidebarSubItem(
                              icon: isSelected ? item.selectedIcon : item.icon,
                              label: item.label,
                              isSelected: isSelected,
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
      switch (controller.currentIndex.value) {
        case 0:
          return const ChatView();
        case 1:
          return const TasksView();
        case 2:
          return const VaultView();
        case 3:
          return const StrategyView();
        case 4:
          return const UsageView();
        case 5:
          return const WorkflowsView();
        case 6:
          return const ApprovalsView();
        case 7:
          return const AgentsView();
        case 8:
          return const ConnectionsView();
        case 9:
          return const PluginsView();
        case 10:
          return const AuditView();
        case 11:
          return const ChannelsView();
        case 12:
          return const ChatbotsView();
        case 13:
          return const SettingsView();
        case 14:
          return const BrandingView();
        case 15:
          return const BackupView();
        case 16:
          return const DiagnosticsView();
        case 17:
          return const MarketingCockpitView();
        case 18:
          return const DeveloperView();
        case 19:
          return const OrganizationView();
        default:
          return const ChatView();
      }
    });
  }
}
