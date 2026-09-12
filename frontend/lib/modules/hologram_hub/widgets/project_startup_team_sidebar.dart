import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/theme/app_theme.dart';
import '../controllers/founder_command_center_controller.dart';
import '../models/project_startup_team.dart';

class ProjectStartupTeamSidebar extends StatefulWidget {
  final FounderCommandCenterController controller;
  final VoidCallback onOpenCofounderChat;
  final bool shrinkWrap;
  final bool isCollapsed;
  final VoidCallback? onToggleCollapse;
  final String? initialExpandedProfileKey;

  const ProjectStartupTeamSidebar({
    super.key,
    required this.controller,
    required this.onOpenCofounderChat,
    this.shrinkWrap = false,
    this.isCollapsed = false,
    this.onToggleCollapse,
    this.initialExpandedProfileKey,
  });

  @override
  State<ProjectStartupTeamSidebar> createState() =>
      _ProjectStartupTeamSidebarState();
}

class _ProjectStartupTeamSidebarState extends State<ProjectStartupTeamSidebar> {
  final Set<String> _actionInProgressKeys = <String>{};
  String? _expandedProfileKey;

  bool _isEnglish() {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  @override
  void initState() {
    super.initState();
    _expandedProfileKey = widget.initialExpandedProfileKey ?? 'founder_assistant';
  }

  void _toggleExpand(String profileKey) {
    setState(() {
      if (_expandedProfileKey == profileKey) {
        _expandedProfileKey = null;
      } else {
        _expandedProfileKey = profileKey;
      }
    });
  }

  static const Map<String, IconData> _profileIcons = {
    'founder_assistant': Icons.psychology_outlined,
    'research_intelligence': Icons.travel_explore_outlined,
    'strategy': Icons.explore_outlined,
    'marketing': Icons.campaign_outlined,
    'finance': Icons.account_balance_wallet_outlined,
    'operations': Icons.settings_suggest_outlined,
    'crm': Icons.people_outline,
    'sales': Icons.trending_up,
    'coding': Icons.code_outlined,
    'customer_support': Icons.support_agent_outlined,
  };

  static const Map<String, String> _profileDescriptionsVi = {
    'founder_assistant': 'Trợ lý Co-Founder AI đồng hành chiến lược và điều phối',
    'research_intelligence': 'Nghiên cứu thị trường, phân tích đối thủ và tổng hợp thông tin',
    'strategy': 'Hoạch định chiến lược tăng trưởng, OKR và mục tiêu 12 tuần',
    'marketing': 'Sáng tạo nội dung, chiến dịch tiếp thị và xây dựng thương hiệu',
    'finance': 'Phân tích tài chính, dự báo dòng tiền và quản lý ngân sách',
    'operations': 'Chuẩn hóa quy trình, tối ưu vận hành và điều phối nguồn lực',
    'crm': 'Quản lý quan hệ khách hàng và quy trình tương tác',
    'sales': 'Tối ưu phễu bán hàng, kịch bản tư vấn và chuyển đổi',
    'coding': 'Lập trình, hiện thực hóa tính năng kỹ thuật và phát triển sản phẩm',
    'customer_support': 'Hỗ trợ khách hàng, giải đáp thắc mắc và chăm sóc sau bán',
  };

  static const Map<String, String> _profileDescriptionsEn = {
    'founder_assistant': 'AI Co-Founder assistant for strategic alignment and coordination',
    'research_intelligence': 'Market research, competitor analysis, and intelligence synthesis',
    'strategy': 'Growth strategy, OKRs planning, and 12-week execution goals',
    'marketing': 'Content creation, marketing campaigns, and brand building',
    'finance': 'Financial analysis, cash flow forecasting, and budget management',
    'operations': 'Standardize processes, optimize operations, and orchestrate resources',
    'crm': 'Customer relationship management and interaction workflows',
    'sales': 'Sales funnel optimization, consultative scripts, and conversion',
    'coding': 'Software engineering, technical implementation, and product development',
    'customer_support': 'Customer support, inquiry resolution, and post-sales care',
  };

  IconData _getIcon(String key) =>
      _profileIcons[key] ?? Icons.smart_toy_outlined;

  String _getDescription(String key) {
    final isEn = _isEnglish();
    final map = isEn ? _profileDescriptionsEn : _profileDescriptionsVi;
    return map[key] ?? (isEn ? 'AI Startup Team Member' : 'Thành viên đội ngũ khởi nghiệp AI');
  }

  Future<void> _handleActivate(ProjectStartupTeamMember member) async {
    if (_actionInProgressKeys.contains(member.profileKey)) return;
    setState(() => _actionInProgressKeys.add(member.profileKey));
    try {
      await widget.controller.activateTeamMember(
        member.profileKey,
        member.assignmentVersion ?? 1,
      );
    } finally {
      if (mounted) {
        setState(() => _actionInProgressKeys.remove(member.profileKey));
      }
    }
  }

  Future<void> _handlePause(ProjectStartupTeamMember member) async {
    if (_actionInProgressKeys.contains(member.profileKey)) return;
    setState(() => _actionInProgressKeys.add(member.profileKey));
    try {
      await widget.controller.pauseTeamMember(
        member.profileKey,
        member.assignmentVersion ?? 1,
      );
    } finally {
      if (mounted) {
        setState(() => _actionInProgressKeys.remove(member.profileKey));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.isCollapsed) {
      return _buildCollapsedRail();
    }
    return _buildExpandedSidebar();
  }

  Widget _buildCollapsedRail() {
    final isEn = _isEnglish();
    return Container(
      key: const Key('startup_team_collapsed_rail'),
      width: 68,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primary.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          const SizedBox(height: 12),
          if (widget.onToggleCollapse != null)
            IconButton(
              onPressed: widget.onToggleCollapse,
              icon: const Icon(Icons.chevron_right, color: AppTheme.primaryLight),
              tooltip: isEn ? 'Expand Startup Team' : 'Mở rộng Đội ngũ Khởi nghiệp',
            ),
          Divider(color: AppTheme.primary.withValues(alpha: 0.13)),
          const SizedBox(height: 6),
          Expanded(
            child: Obx(() {
              final team = widget.controller.startupTeam;
              return ListView.builder(
                shrinkWrap: widget.shrinkWrap,
                itemCount: team.length,
                itemBuilder: (context, index) {
                  final member = team[index];
                  final isActive = member.displayState == TeamDisplayState.active ||
                      member.displayState == TeamDisplayState.chatReady;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
                    child: Tooltip(
                      message: '${member.label} (${_badgeText(member)})',
                      child: Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: isActive
                              ? AppTheme.primary.withValues(alpha: 0.2)
                              : const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: isActive
                                ? AppTheme.primaryLight
                                : const Color(0xFF334155),
                          ),
                        ),
                        child: Icon(
                          _getIcon(member.profileKey),
                          color: isActive ? Colors.white : const Color(0xFF94A3B8),
                          size: 20,
                        ),
                      ),
                    ),
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildExpandedSidebar() {
    return Container(
      key: const Key('startup_team_sidebar'),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primary.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: Column(
        mainAxisSize: widget.shrinkWrap ? MainAxisSize.min : MainAxisSize.max,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: _buildHeader(),
          ),
          Divider(color: AppTheme.primary.withValues(alpha: 0.13), height: 1),
          if (widget.shrinkWrap)
            Padding(
              padding: const EdgeInsets.all(16),
              child: _buildBody(),
            )
          else
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: _buildBody(),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Obx(() {
      final isEn = _isEnglish();
      final team = widget.controller.startupTeam;
      final activeCount = team.where((m) =>
          m.displayState == TeamDisplayState.active ||
          m.displayState == TeamDisplayState.chatReady).length;
      final totalCount = team.length;
      final projectTitle = widget.controller.activeProjectTitle.value;

      return Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.primary, AppTheme.primaryDark],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.groups_outlined, color: Colors.white, size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isEn ? 'STARTUP TEAM' : 'ĐỘI NGŨ KHỞI NGHIỆP',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  projectTitle.isNotEmpty
                      ? (isEn
                          ? '$projectTitle ($activeCount/$totalCount running)'
                          : '$projectTitle ($activeCount/$totalCount đang chạy)')
                      : (isEn ? 'Selecting project...' : 'Đang chọn dự án...'),
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 11,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          if (widget.onToggleCollapse != null)
            IconButton(
              onPressed: widget.onToggleCollapse,
              icon: const Icon(Icons.chevron_left, color: Color(0xFF94A3B8), size: 20),
              tooltip: isEn ? 'Collapse sidebar' : 'Thu gọn cột',
            ),
        ],
      );
    });
  }

  Widget _buildBody() {
    return Obx(() {
      final isEn = _isEnglish();
      final pid = widget.controller.activeProjectId.value;
      if (pid == null || pid.isEmpty) {
        return _buildNoProjectState();
      }

      if (widget.controller.isTeamLoading.value &&
          widget.controller.startupTeam.isEmpty) {
        return const Center(
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 32),
            child: CircularProgressIndicator(),
          ),
        );
      }

      final error = widget.controller.teamError.value;
      if (error != null && widget.controller.startupTeam.isEmpty) {
        return _buildErrorState(error, pid);
      }

      final team = widget.controller.startupTeam;
      if (team.isEmpty) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 32),
            child: Text(
              isEn ? 'No startup team data' : 'Không có dữ liệu đội ngũ khởi nghiệp',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
            ),
          ),
        );
      }

      final listWidget = ListView.separated(
        shrinkWrap: widget.shrinkWrap,
        physics: widget.shrinkWrap
            ? const NeverScrollableScrollPhysics()
            : const BouncingScrollPhysics(),
        itemCount: team.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final member = team[index];
          return _buildMemberCard(member);
        },
      );

      return widget.shrinkWrap ? listWidget : Expanded(child: listWidget);
    });
  }

  Widget _buildNoProjectState() {
    final isEn = _isEnglish();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Center(
        child: Column(
          children: [
            const Icon(Icons.folder_open_outlined, color: Color(0xFF64748B), size: 36),
            const SizedBox(height: 8),
            Text(
              isEn ? 'No project selected' : 'Chưa chọn dự án',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              isEn
                  ? 'Select a project to view and manage its startup team.'
                  : 'Chọn một dự án để xem và quản lý đội ngũ khởi nghiệp.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(String error, String projectId) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF7F1D1D).withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.4)),
      ),
      child: Column(
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 28),
          const SizedBox(height: 8),
          Text(
            error,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 12),
          ),
          const SizedBox(height: 12),
          ElevatedButton.icon(
            key: const Key('team_error_retry_button'),
            onPressed: () => widget.controller.loadStartupTeam(projectId),
            icon: const Icon(Icons.refresh, size: 14),
            label: const Text('Thử lại', style: TextStyle(fontSize: 12)),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF334155),
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMemberCard(ProjectStartupTeamMember member) {
    final isEn = _isEnglish();
    final isExpanded = _expandedProfileKey == member.profileKey;
    final isActionInProgress = _actionInProgressKeys.contains(member.profileKey);
    final badge = _badgeText(member);
    final badgeColor = _badgeColor(member);
    final isChatReady = member.displayState == TeamDisplayState.chatReady;
    final isActive = member.displayState == TeamDisplayState.active;
    final isPaused = member.displayState == TeamDisplayState.paused;

    final canActivate = member.displayState == TeamDisplayState.template &&
        member.runtimeReadiness == RuntimeReadiness.ready;
    final canResume = isPaused &&
        member.runtimeReadiness == RuntimeReadiness.ready;

    return Container(
      key: Key('startup_team_card_${member.profileKey}'),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isActive || isChatReady
              ? AppTheme.primary.withValues(alpha: 0.4)
              : const Color(0xFF334155),
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: Key('startup_team_card_inkwell_${member.profileKey}'),
          onTap: () => _toggleExpand(member.profileKey),
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: isActive || isChatReady
                            ? AppTheme.primary.withValues(alpha: 0.2)
                            : const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isActive || isChatReady
                              ? AppTheme.primaryLight.withValues(alpha: 0.5)
                              : const Color(0xFF475569),
                        ),
                      ),
                      child: Icon(
                        _getIcon(member.profileKey),
                        color: isActive || isChatReady ? Colors.white : const Color(0xFF94A3B8),
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              member.label,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: badgeColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: badgeColor.withValues(alpha: 0.4)),
                            ),
                            child: Text(
                              badge,
                              style: TextStyle(
                                color: badgeColor,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    Icon(
                      isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                      color: const Color(0xFF94A3B8),
                      size: 18,
                    ),
                  ],
                ),

                if (isExpanded) ...[
                  const SizedBox(height: 8),
                  Text(
                    _getDescription(member.profileKey),
                    style: const TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 11,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),

                  // Activation metadata
                  if (isActive && member.activatedAt != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A).withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.verified_outlined, color: Color(0xFF10B981), size: 12),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              isEn
                                  ? 'Activated: ${_formatDate(member.activatedAt!)}${member.activatedBy != null ? ' by ${member.activatedBy}' : ''}'
                                  : 'Kích hoạt: ${_formatDate(member.activatedAt!)}${member.activatedBy != null ? ' bởi ${member.activatedBy}' : ''}',
                              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 10),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  // Action buttons
                  const SizedBox(height: 10),
                  if (isChatReady) ...[
                    SizedBox(
                      width: double.infinity,
                      height: 32,
                      child: ElevatedButton.icon(
                        key: const Key('btn_chat_cofounder'),
                        onPressed: widget.onOpenCofounderChat,
                        icon: const Icon(Icons.chat_bubble_outline, size: 14),
                        label: Text(
                          isEn ? 'Open Co-Founder Chat' : 'Mở Chat Co-Founder',
                          style: const TextStyle(fontSize: 11),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primary,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                          ),
                          padding: EdgeInsets.zero,
                        ),
                      ),
                    ),
                  ] else if (isActive) ...[
                    SizedBox(
                      width: double.infinity,
                      height: 32,
                      child: OutlinedButton.icon(
                        key: Key('btn_pause_${member.profileKey}'),
                        onPressed: isActionInProgress ? null : () => _handlePause(member),
                        icon: isActionInProgress
                            ? const SizedBox(
                                width: 12,
                                height: 12,
                                child: CircularProgressIndicator(strokeWidth: 1.5),
                              )
                            : const Icon(Icons.pause_circle_outline, size: 14),
                        label: Text(
                          isEn ? 'Pause' : 'Tạm dừng',
                          style: const TextStyle(fontSize: 11),
                        ),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFFF59E0B),
                          side: const BorderSide(color: Color(0xFFF59E0B)),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                          ),
                          padding: EdgeInsets.zero,
                        ),
                      ),
                    ),
                  ] else if (canActivate || canResume) ...[
                    SizedBox(
                      width: double.infinity,
                      height: 32,
                      child: ElevatedButton.icon(
                        key: Key('btn_activate_${member.profileKey}'),
                        onPressed: isActionInProgress ? null : () => _handleActivate(member),
                        icon: isActionInProgress
                            ? const SizedBox(
                                width: 12,
                                height: 12,
                                child: CircularProgressIndicator(strokeWidth: 1.5, color: Colors.white),
                              )
                            : const Icon(Icons.play_circle_outline, size: 14),
                        label: Text(
                          canResume
                              ? (isEn ? 'Reactivate' : 'Kích hoạt lại')
                              : (isEn ? 'Activate' : 'Kích hoạt'),
                          style: const TextStyle(fontSize: 11),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                          ),
                          padding: EdgeInsets.zero,
                        ),
                      ),
                    ),
                  ] else ...[
                    // Disabled action button for deferred or pending dependencies
                    SizedBox(
                      width: double.infinity,
                      height: 32,
                      child: Tooltip(
                        message: _disabledExplanation(member),
                        child: OutlinedButton.icon(
                          key: Key('btn_disabled_${member.profileKey}'),
                          onPressed: null,
                          icon: const Icon(Icons.lock_outline, size: 14),
                          label: Text(
                            _disabledButtonLabel(member),
                            style: const TextStyle(fontSize: 11),
                          ),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF64748B),
                            disabledForegroundColor: const Color(0xFF64748B),
                            side: const BorderSide(color: Color(0xFF334155)),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(6),
                            ),
                            padding: EdgeInsets.zero,
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _badgeText(ProjectStartupTeamMember member) {
    final isEn = _isEnglish();
    switch (member.displayState) {
      case TeamDisplayState.chatReady:
        return 'Co-Founder chat ready';
      case TeamDisplayState.active:
        return 'Active';
      case TeamDisplayState.paused:
        return isEn ? 'Paused' : 'Tạm dừng';
      case TeamDisplayState.retired:
        return isEn ? 'Retired' : 'Đã giải thể';
      case TeamDisplayState.template:
        switch (member.runtimeReadiness) {
          case RuntimeReadiness.deferredCoding:
            return 'Coming later';
          case RuntimeReadiness.pendingCrmFoundation:
            return isEn ? 'Needs CRM Integration' : 'Cần tích hợp CRM';
          case RuntimeReadiness.pendingProjectKnowledge:
            return isEn ? 'Needs Project Knowledge' : 'Cần tri thức dự án';
          case RuntimeReadiness.ready:
            return isEn ? 'Ready' : 'Sẵn sàng';
        }
    }
  }

  Color _badgeColor(ProjectStartupTeamMember member) {
    switch (member.displayState) {
      case TeamDisplayState.chatReady:
        return const Color(0xFF3B82F6);
      case TeamDisplayState.active:
        return const Color(0xFF10B981);
      case TeamDisplayState.paused:
        return const Color(0xFFF59E0B);
      case TeamDisplayState.retired:
        return const Color(0xFF64748B);
      case TeamDisplayState.template:
        switch (member.runtimeReadiness) {
          case RuntimeReadiness.deferredCoding:
          case RuntimeReadiness.pendingCrmFoundation:
          case RuntimeReadiness.pendingProjectKnowledge:
            return const Color(0xFF94A3B8);
          case RuntimeReadiness.ready:
            return const Color(0xFF38BDF8);
        }
    }
  }

  String _disabledButtonLabel(ProjectStartupTeamMember member) {
    final isEn = _isEnglish();
    if (member.runtimeReadiness == RuntimeReadiness.deferredCoding) {
      return 'Coming later';
    }
    if (member.runtimeReadiness == RuntimeReadiness.pendingCrmFoundation) {
      return isEn ? 'Needs CRM Integration' : 'Cần tích hợp CRM';
    }
    if (member.runtimeReadiness == RuntimeReadiness.pendingProjectKnowledge) {
      return isEn ? 'Needs Project Knowledge' : 'Cần tri thức dự án';
    }
    return isEn ? 'Not Ready' : 'Chưa sẵn sàng';
  }

  String _disabledExplanation(ProjectStartupTeamMember member) {
    final isEn = _isEnglish();
    if (member.disabledReason != null && member.disabledReason!.isNotEmpty) {
      return member.disabledReason!;
    }
    if (member.runtimeReadiness == RuntimeReadiness.deferredCoding) {
      return isEn
          ? 'Coding capability is not available in the current stage'
          : 'Tính năng lập trình chưa mở trong giai đoạn hiện tại';
    }
    if (member.runtimeReadiness == RuntimeReadiness.pendingCrmFoundation) {
      return isEn
          ? 'CRM platform integration required before activating agent'
          : 'Cần tích hợp nền tảng CRM trước khi kích hoạt agent';
    }
    if (member.runtimeReadiness == RuntimeReadiness.pendingProjectKnowledge) {
      return isEn
          ? 'Project documentation and knowledge setup required before activation'
          : 'Cần cấu hình tài liệu và tri thức dự án trước khi kích hoạt';
    }
    return isEn ? 'Agent is not ready to activate' : 'Agent chưa sẵn sàng để kích hoạt';
  }

  String _formatDate(DateTime dt) {
    final d = dt.toLocal();
    final day = d.day.toString().padLeft(2, '0');
    final month = d.month.toString().padLeft(2, '0');
    final year = d.year.toString();
    final hour = d.hour.toString().padLeft(2, '0');
    final min = d.minute.toString().padLeft(2, '0');
    return '$day/$month/$year $hour:$min';
  }
}
