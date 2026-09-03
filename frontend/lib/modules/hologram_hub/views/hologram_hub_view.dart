import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/widgets/runtime_app_chrome.dart';
import '../controllers/founder_command_center_controller.dart';
import '../widgets/cofounder_card_widget.dart';
import '../widgets/top3_focus_widget.dart';
import '../widgets/waiting_for_you_widget.dart';
import '../widgets/decision_modal_sheet.dart';
import '../widgets/ai_workforce_tab.dart';
import '../../../core/contracts/enums.generated.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../../data/models/stage_model.dart';
import '../../../shared/widgets/company_scope_switcher.dart';
import '../../../shared/widgets/stage_badge.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../controllers/hologram_hub_controller.dart';
import '../presentation/widgets/cyber_circuit_background.dart';
import '../../dashboard/models/dashboard_nav_config.dart';
import '../../../core/routing/module_routes.dart';
import '../../dashboard/views/widgets/floating_voice_hologram.dart';
import '../widgets/draggable_chat_panel.dart';
import '../../../core/shell/chat_panel_controller.dart';

class HologramHubView extends StatelessWidget {
  const HologramHubView({super.key});

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
      if (!context.mounted) return;
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

                    // 2. Main Tab Content Area
                    Expanded(
                      child: Obx(() {
                        if (controller.isLoading.value) {
                          return const Center(
                            child: CircularProgressIndicator(
                              color: Color(0xFF6366F1),
                            ),
                          );
                        }

                        return LayoutBuilder(
                          builder: (context, constraints) {
                            final isWide = constraints.maxWidth >= 950;

                            return Center(
                              child: ConstrainedBox(
                                constraints: const BoxConstraints(maxWidth: 1360),
                                child: IndexedStack(
                                  index: controller.selectedTabIndex.value,
                                  children: [
                                    // Tab 0: Founder Command Center (Co-Founder, Pulse, Top 3, Waiting for You)
                                    _buildCommandCenterTab(
                                      context,
                                      controller,
                                      isWide,
                                    ),

                                    // Tab 1: AI Workforce & Optional Packs Store
                                    _buildWorkforceTab(context, controller, isWide),
                                  ],
                                ),
                              ),
                            );
                          },
                        );
                      }),
                    ),
                  ],
                ),
              ),
            ),
            const FloatingVoiceHologram(),
            const DraggableChatPanel(),
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
              Expanded(
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Row(
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
                      Flexible(
                        child: Column(
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
                                'Hệ điều hành doanh nghiệp AI',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.white.withValues(alpha: 0.5),
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                          ],
                        ),
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
                ),
              ),

              // --- CENTER: 2 Navigation Tabs (Command Center & AI Workforce) ---
              Obx(() {
                final activeTab = controller.selectedTabIndex.value;
                return Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B).withValues(alpha: 0.8),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF334155)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.25),
                        blurRadius: 10,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  padding: const EdgeInsets.all(4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildTabButton(
                        label: isCompact ? 'Command' : 'Command Center',
                        icon: Icons.dashboard_outlined,
                        isSelected: activeTab == 0,
                        onTap: () => controller.selectedTabIndex.value = 0,
                      ),
                      const SizedBox(width: 4),
                      _buildTabButton(
                        label: isCompact ? 'Workforce' : 'AI Workforce',
                        icon: Icons.groups_outlined,
                        isSelected: activeTab == 1,
                        onTap: () => controller.selectedTabIndex.value = 1,
                      ),
                    ],
                  ),
                );
              }),

              // --- RIGHT: CompanyScopeSwitcher & Actions ---
              Expanded(
                child: Align(
                  alignment: Alignment.centerRight,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Company Scope Switcher (Bên phải)
                      if (!isCompact) ...[
                        const CompanyScopeSwitcher(),
                        const SizedBox(width: 8),
                      ],

                      // Module Switcher — thay cho sidebar không còn ở Hub
                      IconButton(
                        onPressed: () => _openModuleSwitcher(context),
                        icon: const Icon(
                          Icons.apps_rounded,
                          color: Colors.white70,
                          size: 20,
                        ),
                        tooltip: 'Chuyển module',
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
                        tooltip: 'Quản trị Dashboard',
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
                        tooltip: 'Làm mới dữ liệu',
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
                        tooltip: 'Hồ sơ của tôi',
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

  Widget _buildTabButton({
    required String label,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeInOut,
      decoration: BoxDecoration(
        gradient: isSelected
            ? const LinearGradient(
                colors: [Color(0xFF6366F1), Color(0xFF4F46E5)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
        color: isSelected ? null : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        boxShadow: isSelected
            ? [
                BoxShadow(
                  color: const Color(0xFF6366F1).withValues(alpha: 0.35),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  icon,
                  size: 16,
                  color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                ),
                const SizedBox(width: 8),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                    color: isSelected ? Colors.white : const Color(0xFF94A3B8),
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCommandCenterTab(
    BuildContext context,
    FounderCommandCenterController controller,
    bool isWide,
  ) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Lưới an toàn: guard/backstop (Task 1-5) đảm bảo Hub không còn render
          // ở trạng thái 0 project; nhưng nếu có race khiến nó render tạm thời,
          // ẩn toàn bộ widget phụ thuộc project để không hiện số liệu giả.
          if (controller.hasProjects.value) ...[
            // A. Hero Co-Founder Card + Company Pulse
            CoFounderCardWidget(
              pulse: controller.pulse.value,
              onAskCosa: () => Get.find<ChatPanelController>().open(),
            ),
            const SizedBox(height: 24),

            Obx(() {
              final setup = controller.activeProjectSetup.value;
              final activeProjectId = controller.projectsList.isNotEmpty
                  ? controller.projectsList.first['id']?.toString()
                  : null;
              if (activeProjectId != null &&
                  (setup == null ||
                      setup.status != OperatingSetupStatus.active)) {
                return _buildSetupIncompleteCard(context, activeProjectId);
              }
              if (setup != null && setup.status == OperatingSetupStatus.active) {
                return _buildActiveOperatingSetupCard(context, setup);
              }
              return const SizedBox.shrink();
            }),

            // B & C: Responsive Grid (Side-by-Side on Desktop, Stacked on Mobile)
            if (isWide)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // B. Top 3 Focus (12-Week Year) - Left Column
                  Expanded(
                    flex: 6,
                    child: Top3FocusWidget(
                      actions: controller.top3Actions.toList(),
                      onActionTap: (action) =>
                          _handleActionTap(context, controller, action),
                    ),
                  ),
                  const SizedBox(width: 24),

                  // C. Waiting for You (Decisions & Approvals) - Right Column
                  Expanded(
                    flex: 5,
                    child: WaitingForYouWidget(
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
                  ),
                ],
              )
            else ...[
              // Mobile Stacked layout
              Top3FocusWidget(
                actions: controller.top3Actions.toList(),
                onActionTap: (action) =>
                    _handleActionTap(context, controller, action),
              ),
              const SizedBox(height: 24),
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
            ],
            const SizedBox(height: 24),
          ],
        ],
      ),
    );
  }

  Widget _buildSetupIncompleteCard(BuildContext context, String projectId) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFF59E0B).withValues(alpha: 0.5),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 620;
          final action = ElevatedButton.icon(
            onPressed: () {
              if (Get.isRegistered<DashboardController>()) {
                Get.find<DashboardController>().openProjectKickoff(projectId);
              }
            },
            icon: const Icon(Icons.arrow_forward_rounded, size: 16),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFF59E0B),
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            label: const Text(
              'Tiếp tục thiết lập',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          );
          final message = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                'Hoàn tất thiết lập vòng khởi đầu',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Dự án của bạn chưa hoàn thành 3 bước thiết lập mục tiêu và hành động tuần đầu.',
                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
              ),
            ],
          );
          final icon = Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.flag_circle_outlined,
              color: Color(0xFFF59E0B),
              size: 28,
            ),
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    icon,
                    const SizedBox(width: 16),
                    Expanded(child: message),
                  ],
                ),
                const SizedBox(height: 16),
                Align(alignment: Alignment.centerRight, child: action),
              ],
            );
          }
          return Row(
            children: [
              icon,
              const SizedBox(width: 16),
              Expanded(child: message),
              const SizedBox(width: 16),
              action,
            ],
          );
        },
      ),
    );
  }

  Widget _buildActiveOperatingSetupCard(
    BuildContext context,
    ProjectOperatingSetup setup,
  ) {
    final stageLabel =
        setup.selectedStage == ProjectLifecycleStage.p1ProblemValidation
        ? 'Xác thực vấn đề (P1)'
        : 'Khám phá (P0)';
    final duration =
        setup.stageDurationWeeks ??
        (setup.selectedStage == ProjectLifecycleStage.p1ProblemValidation
            ? 4
            : 2);
    final reviewDay = setup.weeklyReviewWeekday == 5
        ? 'Thứ Sáu'
        : 'Thứ ${setup.weeklyReviewWeekday}';
    final reviewTime = setup.weeklyReviewTime ?? '16:00';

    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFF10B981).withValues(alpha: 0.4),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final stage = Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFF10B981).withValues(alpha: 0.4),
                  ),
                ),
                child: Text(
                  'Vòng hiện tại: $stageLabel · $duration tuần',
                  style: const TextStyle(
                    color: Color(0xFF10B981),
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              );
              final review = Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.schedule_rounded,
                    size: 15,
                    color: Color(0xFF94A3B8),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'Ngày review: $reviewDay · $reviewTime',
                    style: const TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 12.5,
                    ),
                  ),
                ],
              );
              if (constraints.maxWidth < 760) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [stage, const SizedBox(height: 10), review],
                );
              }
              return Row(children: [stage, const Spacer(), review]);
            },
          ),
          if (setup.firstWeekOutcome != null &&
              setup.firstWeekOutcome!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              'Kết quả tuần 1: ${setup.firstWeekOutcome}',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          if (setup.firstWeekActions.isNotEmpty) ...[
            const SizedBox(height: 10),
            const Text(
              'Hành động tuần đầu:',
              style: TextStyle(
                color: Color(0xFF94A3B8),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: setup.firstWeekActions.asMap().entries.map((entry) {
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: Text(
                    '${entry.key + 1}. ${entry.value.title}',
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }

  // Giữ lại cho spec follow-up (tạo dự án đầu tiên) — first-project banner đã
  // gỡ nên tạm thời không còn call-site trong file này.
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
              title: const Row(
                children: [
                  Icon(Icons.rocket_launch, color: Color(0xFF6366F1), size: 22),
                  SizedBox(width: 10),
                  Text(
                    'Khởi tạo dự án mới',
                    style: TextStyle(
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
                    const Text(
                      'Tên dự án *',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      controller: titleController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Ví dụ: Nền tảng B2B SaaS cho Doanh nghiệp',
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
                    const Text(
                      'Mô tả bài toán / JTBD',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    TextField(
                      controller: descriptionController,
                      maxLines: 3,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText:
                            'Mô tả ngắn gọn ý tưởng, vấn đề cần giải quyết...',
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
                  child: const Text(
                    'Hủy',
                    style: TextStyle(color: Colors.white60),
                  ),
                ),
                ElevatedButton(
                  onPressed: () async {
                    final title = titleController.text.trim();
                    final desc = descriptionController.text.trim();
                    if (title.isEmpty) {
                      AppToast.warning(
                        'Vui lòng nhập tên dự án',
                        title: 'Thiếu thông tin',
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
                  child: const Text(
                    'Khởi tạo dự án',
                    style: TextStyle(
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
      controller.chatInputController.text =
          'Tôi muốn thiết lập hồ sơ doanh nghiệp mới. Hãy hướng dẫn tôi định hình Vision, Problem và Target Market!';
      Get.find<ChatPanelController>().open();
      return;
    } else if (action.id == 'act_genesis_12wy') {
      controller.chatInputController.text =
          'Hãy hướng dẫn tôi thiết lập Mục tiêu 12-Week Year cho Quý đầu tiên.';
      Get.find<ChatPanelController>().open();
      return;
    }

    Get.find<ChatPanelController>().open();
  }

  Widget _buildWorkforceTab(
    BuildContext context,
    FounderCommandCenterController controller,
    bool isWide,
  ) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: AiWorkforceTab(
        packs: controller.workforcePacks.toList(),
        onTogglePack: (key, val) => controller.togglePack(key, val),
      ),
    );
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
                      group.title,
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
                        item.label,
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
