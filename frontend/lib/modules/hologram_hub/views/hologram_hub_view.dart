import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/widgets/runtime_app_chrome.dart';
import '../controllers/founder_command_center_controller.dart';
import '../widgets/execution_plan_card_widget.dart';
import '../widgets/your_tasks_widget.dart';
import '../widgets/pulse_stat_bar_widget.dart';
import '../widgets/top3_focus_widget.dart';
import '../widgets/waiting_for_you_widget.dart';
import '../widgets/project_context_bar.dart';
import '../widgets/project_activity_timeline.dart';
import '../models/project_activity_models.dart';
import '../services/project_activity_service.dart';
import '../widgets/chat_panel_content.dart';
import '../widgets/decision_modal_sheet.dart';
import '../widgets/project_operating_week_card.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/models/stage_model.dart';
import '../../../shared/widgets/stage_badge.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../controllers/hologram_hub_controller.dart';
import '../presentation/widgets/cyber_circuit_background.dart';
import '../../dashboard/models/dashboard_nav_config.dart';
import '../../../core/routing/module_routes.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/shell/chat_panel_controller.dart';

import '../widgets/agent_direct_chat_sheet.dart';
import '../widgets/project_startup_team_sidebar.dart';
import '../../agents/views/widgets/agent_test_run_drawer.dart';
import 'executive_advisory_board_view.dart';

class HologramHubView extends StatefulWidget {
  const HologramHubView({super.key});

  @override
  State<HologramHubView> createState() => _HologramHubViewState();
}

class _HologramHubViewState extends State<HologramHubView> {
  bool _isMobileWorkforceExpanded = false;
  Map<String, dynamic>? _selectedAgentForChat;
  Map<String, dynamic>? _selectedAgentForTestRun;

  @override
  Widget build(BuildContext context) {
    // Task 10 — trước đây view này tự `Get.put` một instance MỚI của
    // `FounderCommandCenterController`, chồng lên instance đã được
    // `DashboardBinding` đăng ký qua `lazyPut` khi vào `/hub` — hai instance
    // cùng tồn tại là đúng "duplicate hub controller ownership" mà Task 10
    // phải dọn: `HologramHubView` không sở hữu binding riêng, chỉ được tìm
    // lại controller đã có, không tạo thêm bản sao.
    final controller = Get.find<FounderCommandCenterController>();

    // Task 10 — `/chat` (route cũ) giờ redirect vào đây kèm `?panel=chat`
    // (xem `app_pages.dart`); mở lại đúng chat sheet hiện có của Hub thay vì
    // dựng thêm một bề mặt chat song song. `addPostFrameCallback` vì mở
    // `showModalBottomSheet` cần build xong khung hình hiện tại trước.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      controller.maybeAutoOpenChatFromRoute(() => Get.find<ChatPanelController>().open());
    });

    // Task 5 — Hub đứng độc lập (standalone shell) cũng phải có
    // RuntimeAppChrome giống Dashboard: banner offline/degraded không được
    // chỉ xuất hiện ở một shell mà thiếu ở shell còn lại.
    return RuntimeAppChrome(
      child: Scaffold(
        backgroundColor: const Color(0xFF040712),
        body: Stack(
          children: [
            CyberCircuitBackground(
              child: SafeArea(
                child: Column(
                  children: [
                    // 1. Top Header & Navigation Bar
                    _buildHeader(context, controller),

                    // 2. Main Content Area (Full Width, không bọc ConstrainedBox)
                    Expanded(
                      child: LayoutBuilder(
                        builder: (context, constraints) {
                          return Obx(() {
                            if (controller.isLoading.value) {
                              return const Center(
                                child: CircularProgressIndicator(
                                  color: Color(0xFF6366F1),
                                ),
                              );
                            }

                            return _buildHubMainContent(
                              context,
                              controller,
                              constraints,
                            );
                          });
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Direct Agent Mission Chat Sheet (Slide Drawer từ bên phải)
            if (_selectedAgentForChat != null) ...[
              Positioned.fill(
                child: GestureDetector(
                  onTap: () => setState(() => _selectedAgentForChat = null),
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.5),
                  ),
                ),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: AgentDirectChatSheet(
                  agent: _selectedAgentForChat!,
                  onClose: () => setState(() => _selectedAgentForChat = null),
                  onTaskCreated: (title, desc) {
                    final isEn = (Get.isRegistered<LocaleController>() &&
                            Get.find<LocaleController>().current.value ==
                                SupportedLocale.enUS) ||
                        Get.locale?.languageCode == 'en';
                    AppToast.success(
                      isEn
                          ? 'Saved task to weekly plan!'
                          : 'Đã lưu nhiệm vụ vào kế hoạch tuần!',
                    );
                    setState(() => _selectedAgentForChat = null);
                  },
                ),
              ),
            ],

            // Test Run Drawer (nếu bấm Test)
            if (_selectedAgentForTestRun != null) ...[
              Positioned.fill(
                child: GestureDetector(
                  onTap: () => setState(() => _selectedAgentForTestRun = null),
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.5),
                  ),
                ),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: AgentTestRunDrawer(
                  agent: _selectedAgentForTestRun!,
                  isLoading: false,
                  onClose: () => setState(() => _selectedAgentForTestRun = null),
                  onExecute: (prompt, model, temp) {
                    final isEn = (Get.isRegistered<LocaleController>() &&
                            Get.find<LocaleController>().current.value ==
                                SupportedLocale.enUS) ||
                        Get.locale?.languageCode == 'en';
                    AppToast.success(
                      isEn
                          ? 'Executing test run with Agent...'
                          : 'Đang thực thi thử nghiệm với Agent...',
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    FounderCommandCenterController controller,
  ) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.9),
        border: const Border(
          bottom: BorderSide(color: Color(0x336366F1), width: 1),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 850;

          return Row(
            children: [
              // --- LEFT: Brand Logo & Subtitle & Stage ---
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                      ),
                      borderRadius: BorderRadius.circular(10),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(
                            0xFF6366F1,
                          ).withValues(alpha: 0.3),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.rocket_launch,
                      color: Colors.white,
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        'COSA',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                          letterSpacing: 0.5,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (!isCompact)
                        Text(
                          L10nKey.hubSubtitle.tr,
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.white.withValues(alpha: 0.5),
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                  // StageBadge
                  Obx(() {
                    final stage = controller.pulse.value?.companyStage;
                    if (stage == null) return const SizedBox.shrink();
                    return Padding(
                      padding: const EdgeInsets.only(left: 12),
                      child: StageBadge(
                        stage: ProjectStage.fromString(stage),
                        isCompact: true,
                      ),
                    );
                  }),
                ],
              ),

              const SizedBox(width: 16),

              // --- RIGHT: ProjectContextBar & Actions ---
              Expanded(
                child: Align(
                  alignment: Alignment.centerRight,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Project Context Bar (Bên phải)
                      if (!isCompact)
                        Expanded(
                          child: ProjectContextBar(
                            projects: controller.projectsList.toList(),
                            selectedProjectId: controller.activeProjectId,
                            onSelected: (projectId) =>
                                controller.selectProject(projectId),
                          ),
                        ),

                      // Project Operating Loop Icon Button (chuyển từ Top3 Focus lên AppBar)
                      Obx(() {
                        final pid = controller.activeProjectId.value;
                        return IconButton(
                          key: const Key('appbar_project_loop_button'),
                          onPressed: pid != null
                              ? () => Get.toNamed(AppRoutes.projectLoopFor(pid))
                              : null,
                          icon: const Icon(
                            Icons.all_inclusive_rounded,
                            color: Colors.white70,
                            size: 20,
                          ),
                          tooltip: Get.locale?.languageCode == 'vi'
                              ? 'Vòng lặp Vận hành (Project Loop)'
                              : 'Open Project Operating Loop',
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(
                            minWidth: 36,
                            minHeight: 36,
                          ),
                        );
                      }),
                      const SizedBox(width: 4),

                      // Module Switcher — thay cho sidebar không còn ở Hub
                      IconButton(
                        onPressed: () => _openModuleSwitcher(context),
                        icon: const Icon(
                          Icons.apps_rounded,
                          color: Colors.white70,
                          size: 20,
                        ),
                        tooltip: L10nKey.hubSwitchModule.tr,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 36,
                          minHeight: 36,
                        ),
                      ),
                      const SizedBox(width: 4),

                      // Dashboard Button — vào màn hình quản trị (Dashboard)
                      IconButton(
                        onPressed: () => Get.find<HologramHubController>()
                            .onSettingsPressed(),
                        icon: const Icon(
                          Icons.space_dashboard_outlined,
                          color: Colors.white70,
                          size: 20,
                        ),
                        tooltip: L10nKey.hubManageDashboard.tr,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 36,
                          minHeight: 36,
                        ),
                      ),
                      const SizedBox(width: 4),

                      // Refresh Button
                      IconButton(
                        onPressed: () => controller.loadDashboardData(),
                        icon: const Icon(
                          Icons.refresh,
                          color: Colors.white70,
                          size: 20,
                        ),
                        tooltip: L10nKey.hubRefreshData.tr,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 36,
                          minHeight: 36,
                        ),
                      ),
                      const SizedBox(width: 4),

                      // Profile Button
                      IconButton(
                        onPressed: () => Get.toNamed(AppRoutes.profile),
                        icon: const Icon(
                          Icons.account_circle_outlined,
                          color: Colors.white70,
                          size: 20,
                        ),
                        tooltip: L10nKey.hubMyProfile.tr,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 36,
                          minHeight: 36,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  // ────────────────────────────────────────────────────────────────────────────
  // Hub Main Content: Full width, không tab, 3 cột responsive, bỏ CoFounderCard
  // Desktop (≥1100): Left AI Workforce 4/12 | Center Top3+WGA 4/12 | Right Stats 4/12
  // Tablet (850-1099): Left+Center 6/12 | Right Stats 6/12
  // Mobile (<850): Stacked (Stats → Top3 → AI Workforce → WaitingForYou)
  // ────────────────────────────────────────────────────────────────────────────
  Widget _buildHubMainContent(
    BuildContext context,
    FounderCommandCenterController controller,
    BoxConstraints constraints,
  ) {
    final width = constraints.maxWidth;
    final isDesktop = width >= 1100;
    final isTablet = width >= 850 && width < 1100;

    if (Get.isRegistered<LocaleController>()) {
      Get.find<LocaleController>().current.value;
    }

    // ── Widget builders (shared across breakpoints) ──

    Widget workforceSidebar({bool shrinkWrap = false}) =>
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ProjectStartupTeamSidebar(
              controller: controller,
              shrinkWrap: shrinkWrap,
              onOpenCofounderChat: () {
                if (Get.isRegistered<ChatPanelController>()) {
                  Get.find<ChatPanelController>().open();
                }
              },
            ),
            const SizedBox(height: 12),
            if (controller.activeProjectId.value != null)
              OutlinedButton.icon(
                key: const ValueKey('open_executive_board_button'),
                onPressed: () {
                  _showExecutiveAdvisoryBoardModal(
                    context,
                    controller.activeProjectId.value!,
                  );
                },
                icon: const Icon(Icons.shield_outlined, size: 16, color: Color(0xFF818CF8)),
                label: const _LocalizedText(
                  en: 'Advisory Board',
                  vi: 'Hội đồng Cố vấn',
                  style: TextStyle(color: Color(0xFF818CF8), fontSize: 13),
                ),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFF3730A3)),
                  backgroundColor: const Color(0xFF1E1B4B).withValues(alpha: 0.5),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
          ],
        );

    Widget top3Widget() => Obx(
          () => Top3FocusWidget(
            showDescription: false,
            actions: controller.top3Actions.toList(),
            onActionTap: (action) =>
                _handleActionTap(context, controller, action),
            onDiscuss: () => Get.find<ChatPanelController>().open(),
            onOpenProjectLoop: controller.activeProjectId.value != null
                ? () => Get.toNamed(
                      AppRoutes.projectLoopFor(
                        controller.activeProjectId.value!,
                      ),
                    )
                : null,
            onOpenProjectAnalysis: controller.activeProjectId.value != null
                ? () => Get.toNamed(
                      '${AppRoutes.projectAnalysisFor(controller.activeProjectId.value!)}?title=${Uri.encodeComponent(controller.activeProjectTitle.value)}&stage=${controller.pulse.value?.companyStage ?? 'P0_DISCOVERY'}',
                    )
                : null,
          ),
        );

    Widget statsColumn() => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (controller.hasProjects.value && controller.activeProjectId.value != null) ...[
              PulseStatBarWidget(pulse: controller.pulse.value),
              const SizedBox(height: 16),
              top3Widget(),
              const SizedBox(height: 16),
              WaitingForYouWidget(
                decisions: controller.pendingDecisions.toList(),
                approvals: controller.pendingApprovals.toList(),
                onResolveDecision: (decId, optKey, notes) =>
                    controller.resolveDecision(
                  decisionId: decId,
                  optionKey: optKey,
                  founderNotes: notes,
                ),
                onApproveTask: (appId) => controller.approveTask(appId),
                onRejectTask: (appId, reason) =>
                    controller.rejectTask(appId, reason),
              ),
              const SizedBox(height: 16),
              // Project Activity Timeline (replaces HubActivityTimelineCard) —
              // durable, fetch thật qua ProjectActivityService, không còn
              // session-composed từ chatMessages/FounderInboxTask/ExecutionPlan.
              SizedBox(
                height: 420,
                child: _ProjectActivityFeed(
                  projectId: controller.activeProjectId.value!,
                ),
              ),
            ] else if (!controller.hasProjects.value) ...[
              Center(
                child: _LocalizedText(
                  en: 'No projects available',
                  vi: 'Chưa có dự án nào',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                  ),
                ),
              ),
            ] else ...[
              top3Widget(),
              const SizedBox(height: 16),
              Center(
                child: _LocalizedText(
                  en: 'Select a project to view activity',
                  vi: 'Chọn dự án để xem hoạt động',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                  ),
                ),
              ),
            ],
          ],
        );

    Widget centerColumn() {
      final projectSelected = controller.activeProjectId.value != null;

      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Chat panel - fixed and Project-bound, luôn mount, disable nội bộ
          // khi chưa chọn Project (xem ChatPanelContent.enabled).
          Container(
            height: 400,
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withValues(alpha: 0.95),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: ChatPanelContent(
              controller: controller,
              enabled: projectSelected,
              showCloseButton: false,
            ),
          ),
          if (controller.selectedProjectId != null) ...[
            const SizedBox(height: 16),
            Obx(() => ProjectOperatingWeekCard(
              operatingLoop: controller.currentOperatingLoop.value,
              isLoading: controller.isOperatingLoopLoading.value,
              errorMessage: controller.operatingLoopError.value,
              onRetry: () {
                final pid = controller.selectedProjectId;
                if (pid != null) {
                  controller.loadOperatingLoop(pid);
                }
              },
            )),
          ],
          if (controller.hasProjects.value && projectSelected) ...[
            const SizedBox(height: 16),
            _WgaSurfaces(controller: controller),
          ],
        ],
      );
    }

    // ── DESKTOP (≥1100): 1 hàng 3 cột — AI Workforce 3/12 | Top3 Focus + WGA
    // 6/12 | Thống kê 3/12 ──
    if (isDesktop) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: workforceSidebar(shrinkWrap: true)),
            const SizedBox(width: 24),
            Expanded(flex: 6, child: centerColumn()),
            const SizedBox(width: 24),
            Expanded(flex: 3, child: statsColumn()),
          ],
        ),
      );
    }

    // ── TABLET (850-1099): AI Workforce + Top3 gộp 6/12 (trái) | Thống kê
    // 6/12 (phải) ──
    if (isTablet) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  workforceSidebar(shrinkWrap: true),
                  const SizedBox(height: 16),
                  centerColumn(),
                ],
              ),
            ),
            const SizedBox(width: 24),
            Expanded(child: statsColumn()),
          ],
        ),
      );
    }

    // ── MOBILE (<850): cuộn dọc, full width ──
    final mobileProjectSelected = controller.activeProjectId.value != null;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Chat panel - fixed and Project-bound (xem centerColumn() ở
          // desktop/tablet — mobile cũng cần khung chat cố định, không còn
          // panel nổi kéo-thả).
          Container(
            height: 340,
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withValues(alpha: 0.95),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: ChatPanelContent(
              controller: controller,
              enabled: mobileProjectSelected,
              showCloseButton: false,
            ),
          ),
          const SizedBox(height: 20),
          statsColumn(),
          if (controller.selectedProjectId != null) ...[
            Obx(() => ProjectOperatingWeekCard(
              operatingLoop: controller.currentOperatingLoop.value,
              isLoading: controller.isOperatingLoopLoading.value,
              errorMessage: controller.operatingLoopError.value,
              onRetry: () {
                final pid = controller.selectedProjectId;
                if (pid != null) {
                  controller.loadOperatingLoop(pid);
                }
              },
            )),
            const SizedBox(height: 20),
          ],
          // AI Workforce accordion
          Material(
              color: const Color(0xFF0F172A).withValues(alpha: 0.95),
              borderRadius: BorderRadius.circular(16),
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0x336366F1)),
                ),
                child: Column(
                  children: [
                    InkWell(
                      onTap: () => setState(
                        () => _isMobileWorkforceExpanded =
                            !_isMobileWorkforceExpanded,
                      ),
                      borderRadius: BorderRadius.circular(16),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [
                                    Color(0xFF6366F1),
                                    Color(0xFF8B5CF6),
                                  ],
                                ),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(
                                Icons.groups_outlined,
                                color: Colors.white,
                                size: 18,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const _LocalizedText(
                                    en: 'AI WORKFORCE (Specialist Team)',
                                    vi: 'AI WORKFORCE (Biệt đội chuyên viên)',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  _LocalizedText(
                                    en: _isMobileWorkforceExpanded
                                        ? 'Tap to collapse'
                                        : 'Tap to open task assignments',
                                    vi: _isMobileWorkforceExpanded
                                        ? 'Bấm để thu gọn'
                                        : 'Bấm để mở danh sách giao việc',
                                    style: TextStyle(
                                      color: Colors.white.withValues(
                                        alpha: 0.5,
                                      ),
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Icon(
                              _isMobileWorkforceExpanded
                                  ? Icons.keyboard_arrow_up
                                  : Icons.keyboard_arrow_down,
                              color: const Color(0xFF818CF8),
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (_isMobileWorkforceExpanded) ...[
                      const Divider(color: Color(0x226366F1), height: 1),
                      workforceSidebar(shrinkWrap: true),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
          if (controller.hasProjects.value)
            _WgaSurfaces(controller: controller),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  void _showExecutiveAdvisoryBoardModal(BuildContext context, String projectId) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: SizedBox(
            width: 1000,
            height: 750,
            child: ExecutiveAdvisoryBoardView(projectId: projectId),
          ),
        ),
      ),
    );
  }

  // ignore: unused_element
  void _showCreateProjectDialog(
    BuildContext context,
    FounderCommandCenterController controller,
  ) {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();

    showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF0F172A),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
                side: const BorderSide(color: Color(0xFF334155), width: 1),
              ),
              title: Row(
                children: [
                  const Icon(Icons.rocket_launch, color: Color(0xFF6366F1), size: 22),
                  const SizedBox(width: 10),
                  Text(
                    L10nKey.hubCreateNewProject.tr,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              content: SizedBox(
                width: 480,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      L10nKey.hubProjectNameLabel.tr,
                      style: const TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      controller: titleController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: L10nKey.hubProjectNameHint.tr,
                        hintStyle: TextStyle(
                          color: Colors.white.withValues(alpha: 0.35),
                          fontSize: 13,
                        ),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      L10nKey.hubProjectDescLabel.tr,
                      style: const TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      controller: descriptionController,
                      maxLines: 3,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: L10nKey.hubProjectDescHint.tr,
                        hintStyle: TextStyle(
                          color: Colors.white.withValues(alpha: 0.35),
                          fontSize: 13,
                        ),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: Text(
                    L10nKey.commonCancel.tr,
                    style: const TextStyle(color: Colors.white60),
                  ),
                ),
                ElevatedButton(
                  onPressed: () async {
                    final title = titleController.text.trim();
                    final desc = descriptionController.text.trim();
                    if (title.isEmpty) {
                      AppToast.warning(
                        L10nKey.hubEnterProjectNameError.tr,
                        title: L10nKey.hubMissingInfoTitle.tr,
                      );
                      return;
                    }
                    Navigator.pop(dialogContext);
                    final createdId = await controller.createFirstProject(
                      title: title,
                      description: desc,
                    );
                    if (createdId != null) {
                      if (Get.isRegistered<DashboardController>()) {
                        Get.find<DashboardController>().openProjectKickoff(
                          createdId,
                        );
                      }
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6366F1),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  child: Text(
                    L10nKey.hubCreateProjectAction.tr,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _handleActionTap(
    BuildContext context,
    FounderCommandCenterController controller,
    dynamic action,
  ) {
    if (action.category == 'DECISION') {
      final decId = action.actionPayload?['decision_id'];
      if (decId != null) {
        final found = controller.pendingDecisions.firstWhereOrNull(
          (d) => d.id == decId,
        );
        if (found != null) {
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            backgroundColor: Colors.transparent,
            builder: (_) => DecisionModalSheet(
              decision: found,
              onResolve: (optKey, notes) => controller.resolveDecision(
                decisionId: found.id,
                optionKey: optKey,
                founderNotes: notes,
              ),
            ),
          );
          return;
        }
      }
    } else if (action.id == 'act_genesis_team') {
      controller.selectedTabIndex.value = 1;
      return;
    } else if (action.id == 'act_genesis_profile') {
      final isEn = (Get.isRegistered<LocaleController>() &&
              Get.find<LocaleController>().current.value ==
                  SupportedLocale.enUS) ||
          Get.locale?.languageCode == 'en';
      controller.chatInputController.text = isEn
          ? 'I want to set up a new company profile. Please guide me to define Vision, Problem, and Target Market!'
          : 'Tôi muốn thiết lập hồ sơ doanh nghiệp mới. Hãy hướng dẫn tôi định hình Vision, Problem và Target Market!';
      Get.find<ChatPanelController>().open();
      return;
    } else if (action.id == 'act_genesis_12wy') {
      final isEn = (Get.isRegistered<LocaleController>() &&
              Get.find<LocaleController>().current.value ==
                  SupportedLocale.enUS) ||
          Get.locale?.languageCode == 'en';
      controller.chatInputController.text = isEn
          ? 'Please guide me to set up 12-Week Year Goals for the first quarter.'
          : 'Hãy hướng dẫn tôi thiết lập Mục tiêu 12-Week Year cho Quý đầu tiên.';
      Get.find<ChatPanelController>().open();
      return;
    }

    Get.find<ChatPanelController>().open();
  }

  // Task 4 (hub-no-sidebar) — Hub không còn sidebar riêng, icon menu ở header
  // mở overlay này thay thế vai trò điều hướng module cũ. Tái dùng
  // `DashboardNavConfig.coreNavGroups` (nguồn sự thật danh sách module) và
  // `moduleForLegacyIndex` (Task 9) để lấy route canonical thật — không tự
  // định nghĩa lại danh sách module ở đây.
  void _openModuleSwitcher(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.7,
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          padding: const EdgeInsets.all(20),
          child: Material(
            color: Colors.transparent,
            child: ListView(
              children: DashboardNavConfig.coreNavGroups.expand((group) {
                // Bỏ mục "Hub" (index 0) khỏi danh sách switcher — đang
                // đứng ở Hub rồi thì hiện lại chính nó là dead-click vô
                // nghĩa (index 0 không map tới `WorkspaceModule` nào).
                final items = group.items
                    .where((item) => moduleForLegacyIndex(item.index) != null)
                    .toList();
                if (items.isEmpty) return const <Widget>[];
                return [
                  Padding(
                    padding: const EdgeInsets.only(top: 12, bottom: 6),
                    child: Text(
                      group.localizedTitle,
                      style: const TextStyle(
                        color: Colors.white54,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  ...items.map((item) {
                    final module = moduleForLegacyIndex(item.index)!;
                    return ListTile(
                      leading: Icon(item.icon, color: Colors.white70),
                      title: Text(
                        item.localizedLabel,
                        style: const TextStyle(color: Colors.white),
                      ),
                      onTap: () {
                        Navigator.pop(ctx);
                        Get.toNamed(module.path);
                      },
                    );
                  }),
                ];
              }).toList(),
            ),
          ),
        );
      },
    );
  }
}

/// WGA #6b — bọc 2 card WGA và poll `refreshWgaSurfaces()` mỗi 20s. Timer gắn
/// với vòng đời widget này (dispose đúng cách) thay vì controller onInit —
/// controller là `permanent: true` nên timer ở đó sẽ treo trong widget test.
class _WgaSurfaces extends StatefulWidget {
  final FounderCommandCenterController controller;

  const _WgaSurfaces({required this.controller});

  @override
  State<_WgaSurfaces> createState() => _WgaSurfacesState();
}

class _WgaSurfacesState extends State<_WgaSurfaces> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    widget.controller.loadExecutionSettings();
    _timer = Timer.periodic(
      const Duration(seconds: 20),
      (_) => widget.controller.refreshWgaSurfaces(),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    return Column(
      children: [
        Obx(
          () => Column(
            children: c.draftPlans
                .map(
                  (plan) => ExecutionPlanCardWidget(
                    plan: plan,
                    onAccept: c.acceptPlan,
                    onReject: c.rejectPlan,
                    onChangeItemClass: (itemId, klass) =>
                        c.updatePlanItem(plan.id, itemId, autonomyClass: klass),
                    onDropItem: (itemId) =>
                        c.updatePlanItem(plan.id, itemId, drop: true),
                  ),
                )
                .toList(),
          ),
        ),
        Obx(() => YourTasksWidget(tasks: c.founderInboxTasks.toList())),
      ],
    );
  }
}

/// Task 7 — bọc `ProjectActivityTimeline` với fetch thật qua
/// `ProjectActivityService`, thay `HubActivityTimelineCard` cũ (vốn tự dựng
/// dòng thời gian từ `chatMessages`/`FounderInboxTask`/`ExecutionPlan` — state
/// phiên làm việc, không bền vững). Fetch lại mỗi khi đổi Project.
class _ProjectActivityFeed extends StatefulWidget {
  final String projectId;

  const _ProjectActivityFeed({required this.projectId});

  @override
  State<_ProjectActivityFeed> createState() => _ProjectActivityFeedState();
}

class _ProjectActivityFeedState extends State<_ProjectActivityFeed> {
  final _service = ProjectActivityService();
  late Future<List<ProjectActivityEvent>> _future;

  @override
  void initState() {
    super.initState();
    _future = _service.fetch(widget.projectId);
  }

  @override
  void didUpdateWidget(covariant _ProjectActivityFeed oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.projectId != widget.projectId) {
      setState(() {
        _future = _service.fetch(widget.projectId);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ProjectActivityEvent>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return ProjectActivityTimeline(
            events: const [],
            onSelectEvent: (_) {},
            loading: true,
            unavailable: false,
          );
        }
        if (snapshot.hasError) {
          return ProjectActivityTimeline(
            events: const [],
            onSelectEvent: (_) {},
            loading: false,
            unavailable: true,
          );
        }
        return ProjectActivityTimeline(
          events: snapshot.data ?? const [],
          loading: false,
          unavailable: false,
          // ProjectActivityTimeline tự hiển thị ProjectActivityInspector
          // inline khi tap 1 event (xem widget) — không cần mở thêm dialog
          // ở đây, tránh double inspector.
          onSelectEvent: (_) {},
        );
      },
    );
  }
}

class _LocalizedText extends StatelessWidget {
  const _LocalizedText({
    required this.en,
    required this.vi,
    this.style,
  });

  final String en;
  final String vi;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    if (Get.isRegistered<LocaleController>()) {
      return Obx(() {
        final isEn =
            Get.find<LocaleController>().current.value == SupportedLocale.enUS;
        return Text(isEn ? en : vi, style: style);
      });
    }
    final isEn = Get.locale?.languageCode == 'en';
    return Text(isEn ? en : vi, style: style);
  }
}
