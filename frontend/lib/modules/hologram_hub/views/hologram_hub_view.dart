import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/widgets/runtime_app_chrome.dart';
import '../../../core/services/secure_storage_service.dart';
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
import 'executive_advisory_board_view.dart';

class HologramHubView extends StatefulWidget {
  const HologramHubView({super.key});

  @override
  State<HologramHubView> createState() => _HologramHubViewState();
}

class _HologramHubViewState extends State<HologramHubView> {
  Map<String, dynamic>? _selectedAgentForChat;

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
                  // Chat luôn thuộc Project đang hoạt động; thiếu Project thì sheet báo lỗi.
                  projectId: controller.activeProjectId.value,
                  profileKey: (_selectedAgentForChat!['profile_key'] ??
                          _selectedAgentForChat!['key'] ??
                          '')
                      .toString(),
                  onClose: () => setState(() => _selectedAgentForChat = null),
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
        color: const Color(0xFF0F172A).withValues(alpha: 0.45),
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
                          // Obx: `projectsList` tải bất đồng bộ sau khi hub dựng (nhất là khi
                          // khởi động lại app); đọc `.toList()` ngoài Obx sẽ giữ danh sách rỗng
                          // và thanh mãi hiện "Select Project" dù project đã được chọn.
                          child: Obx(
                            () => ProjectContextBar(
                              projects: controller.projectsList.toList(),
                              selectedProjectId: controller.activeProjectId,
                              onSelected: (projectId) =>
                                  controller.selectProject(projectId),
                            ),
                          ),
                        ),

                      // 16 AI Agents Button (Mở Modal Biệt đội chuyên viên)
                      Container(
                        margin: const EdgeInsets.only(right: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: const Color(0xFF6366F1).withValues(alpha: 0.45),
                          ),
                        ),
                        child: IconButton(
                          key: const Key('appbar_ai_workforce_button'),
                          onPressed: () => _showAiWorkforceModal(context, controller),
                          icon: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: const [
                              Icon(
                                Icons.smart_toy_outlined,
                                color: Color(0xFF818CF8),
                                size: 18,
                              ),
                              SizedBox(width: 4),
                              Text(
                                '16',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFFC7D2FE),
                                ),
                              ),
                            ],
                          ),
                          tooltip: Get.locale?.languageCode == 'vi'
                              ? '16 AI Agents (Biệt đội chuyên viên)'
                              : '16 AI Agents Workforce',
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          constraints: const BoxConstraints(minHeight: 36),
                        ),
                      ),

                      // Hội đồng Cố vấn (Executive Advisory Board Button)
                      Container(
                        margin: const EdgeInsets.only(right: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF8B5CF6).withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: const Color(0xFF8B5CF6).withValues(alpha: 0.45),
                          ),
                        ),
                        child: IconButton(
                          key: const ValueKey('open_executive_board_button'),
                          onPressed: () {
                            final pid = controller.activeProjectId.value;
                            if (pid != null) {
                              _showExecutiveAdvisoryBoardModal(context, pid);
                            } else {
                              AppToast.warning(
                                Get.locale?.languageCode == 'vi'
                                    ? 'Vui lòng chọn dự án trước'
                                    : 'Please select a project first',
                              );
                            }
                          },
                          icon: const Icon(
                            Icons.shield_outlined,
                            color: Color(0xFFA78BFA),
                            size: 18,
                          ),
                          tooltip: Get.locale?.languageCode == 'vi'
                              ? 'Hội đồng Cố vấn (Executive Advisory Board)'
                              : 'Executive Advisory Board',
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
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
  // Hub Main Content: 2 cột responsive (Kính mờ siêu trong suốt)
  // Cột trái: Khung Chat Co-Founder + Card Chu kỳ hoạt động (Operating Week) + WGA
  // Cột phải: Thống kê Pulse + Top 3 Focus + Cần bạn duyệt + Hoạt động dự án
  // 16 AI Agents & Hội đồng Cố vấn: Nằm trên AppBar dưới dạng Icon Button mở Modal
  // ────────────────────────────────────────────────────────────────────────────
  Widget _buildHubMainContent(
    BuildContext context,
    FounderCommandCenterController controller,
    BoxConstraints constraints,
  ) {
    final width = constraints.maxWidth;
    final isDesktop = width >= 1100;

    if (Get.isRegistered<LocaleController>()) {
      Get.find<LocaleController>().current.value;
    }

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
                      '${AppRoutes.projectAnalysisFor(controller.activeProjectId.value!)}?title=${Uri.encodeComponent(controller.activeProjectTitle.value)}&stage=${controller.pulse.value?.companyStage ?? "P0_DISCOVERY"}',
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
                approvals: const [],
                onResolveDecision: (decId, optKey, notes) =>
                    controller.resolveDecision(
                  decisionId: decId,
                  optionKey: optKey,
                  founderNotes: notes,
                ),
              ),
              const SizedBox(height: 16),
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

    Widget leftColumn() {
      final projectSelected = controller.activeProjectId.value != null;

      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Khung chat với Co-Founder (Cột bên trái) - hiệu ứng kính mờ trong suốt
          Container(
            height: 480,
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withValues(alpha: 0.38),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0x336366F1)),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF6366F1).withValues(alpha: 0.05),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: ChatPanelContent(
                controller: controller,
                enabled: projectSelected,
                showCloseButton: false,
              ),
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

    // ── DESKTOP (≥1100): 3 Cột (3/12 - 6/12 - 3/12)
    // Cột bên trái (3/12): Khung chat Co-Founder + Card Chu kỳ hoạt động
    // Ở giữa (6/12): Để trống (tập trung tôn vinh toàn bộ Trống Đồng trung tâm)
    // Cột bên phải (3/12): Thống kê Pulse + Top 3 Focus + Cần bạn duyệt + Hoạt động
    if (isDesktop) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: leftColumn()),
            const SizedBox(width: 24),
            const Expanded(
              flex: 6,
              child: SizedBox.shrink(),
            ),
            const SizedBox(width: 24),
            Expanded(flex: 3, child: statsColumn()),
          ],
        ),
      );
    }

    // ── TABLET (800 - 1099): 2 Cột — Trái 6/12 | Phải 6/12 ──
    if (width >= 800) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 6, child: leftColumn()),
            const SizedBox(width: 20),
            Expanded(flex: 6, child: statsColumn()),
          ],
        ),
      );
    }

    // ── MOBILE (<800): Cuộn dọc — Khung Chat & Chu kỳ trước, Thống kê bên dưới ──
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          leftColumn(),
          const SizedBox(height: 20),
          statsColumn(),
        ],
      ),
    );
  }

  Future<void> _showAiWorkforceModal(
    BuildContext context,
    FounderCommandCenterController controller,
  ) async {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Container(
            width: 580,
            constraints: const BoxConstraints(maxHeight: 820),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withValues(alpha: 0.95),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0x556366F1)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.6),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  decoration: const BoxDecoration(
                    border: Border(bottom: BorderSide(color: Color(0x336366F1))),
                    color: Color(0xFF131D38),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                          ),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.groups_outlined, color: Colors.white, size: 18),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              Get.locale?.languageCode == 'vi'
                                  ? 'AI WORKFORCE (16 Chuyên viên)'
                                  : 'AI WORKFORCE (16 Specialist Agents)',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              Get.locale?.languageCode == 'vi'
                                  ? 'Kích hoạt, giao việc và chỉ đạo biệt đội AI'
                                  : 'Activate, assign tasks and instruct the AI workforce',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.6),
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.white70, size: 20),
                        onPressed: () => Navigator.of(ctx).pop(),
                      ),
                    ],
                  ),
                ),
                Flexible(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: ProjectStartupTeamSidebar(
                      controller: controller,
                      shrinkWrap: true,
                      onOpenCofounderChat: () {
                        Navigator.of(ctx).pop();
                        if (Get.isRegistered<ChatPanelController>()) {
                          Get.find<ChatPanelController>().open();
                        }
                      },
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

  Future<void> _showExecutiveAdvisoryBoardModal(
    BuildContext context,
    String projectId,
  ) async {
    // Executive Board activation từ Task 9 chuyển sang Workspace-scoped —
    // lấy workspace_id hiện tại giống pattern FounderCommandCenterController
    // (SecureStorageService), không suy diễn từ Project.
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId == null) {
      AppToast.error(L10nKey.commonError.tr);
      return;
    }
    if (!context.mounted) return;

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
            child: ExecutiveAdvisoryBoardView(
              projectId: projectId,
              workspaceId: workspaceId,
            ),
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
