import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/widgets/runtime_app_chrome.dart';
import '../controllers/founder_command_center_controller.dart';
import '../widgets/cofounder_card_widget.dart';
import '../widgets/execution_plan_card_widget.dart';
import '../widgets/your_tasks_widget.dart';
import '../widgets/pulse_stat_bar_widget.dart';
import '../widgets/top3_focus_widget.dart';
import '../widgets/waiting_for_you_widget.dart';
import '../widgets/decision_modal_sheet.dart';
import '../widgets/ai_workforce_tab.dart';
import '../../../core/routing/app_routes.dart';
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
import '../../../core/localization/app_translations.dart';
import '../../../core/localization/locale_controller.dart';
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
                                L10nKey.hubSubtitle.tr,
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
                if (Get.isRegistered<LocaleController>()) {
                  Get.find<LocaleController>().current.value;
                }
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
                        label: isCompact ? L10nKey.hubTabCommandCenterShort.tr : L10nKey.hubTabCommandCenter.tr,
                        icon: Icons.dashboard_outlined,
                        isSelected: activeTab == 0,
                        onTap: () => controller.selectedTabIndex.value = 0,
                      ),
                      const SizedBox(width: 4),
                      _buildTabButton(
                        label: isCompact ? L10nKey.hubTabWorkforceShort.tr : L10nKey.hubTabWorkforce.tr,
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
    return Obx(() {
      if (Get.isRegistered<LocaleController>()) {
        Get.find<LocaleController>().current.value;
      }
      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Lưới an toàn: guard/backstop (Task 1-5) đảm bảo Hub không còn render
            // ở trạng thái 0 project; nhưng nếu có race khiến nó render tạm thời,
            // ẩn toàn bộ widget phụ thuộc project để không hiện số liệu giả.
            if (controller.hasProjects.value) ...[
            // A0. Thống kê nhanh — đặt trên cùng theo feedback founder (2026-09-04)
            // xem docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md
            PulseStatBarWidget(pulse: controller.pulse.value),
            const SizedBox(height: 16),

            // A. Hero Co-Founder Card
            CoFounderCardWidget(
              pulse: controller.pulse.value,
              onAskCosa: () => Get.find<ChatPanelController>().open(),
            ),
            const SizedBox(height: 24),

            // A1/A2. WGA — "Kế hoạch đề xuất" + "Việc của bạn" (poll 20s qua wrapper)
            _WgaSurfaces(controller: controller),

            // B & C: Responsive Grid (Side-by-Side on Desktop, Stacked on Mobile)
            if (isWide)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // B. Top 3 Focus (12-Week Year) - Left Column
                  //
                  // Fix-review (2026-09-04, final review, Fix 1) — đọc
                  // `activeProjectSetup.value` ở đây trước đây KHÔNG được
                  // track bởi Obx nào: `Obx` bao ngoài ở dòng ~66 chỉ track
                  // các Rx read xảy ra ĐỒNG BỘ trong chính builder của nó,
                  // nhưng builder đó chỉ trả về `LayoutBuilder` — các đọc
                  // Rx thật sự (trong `_buildCommandCenterTab`) chạy ở pass
                  // build RIÊNG của `LayoutBuilder`, lúc đó GetX đã un-bind
                  // proxy tracking. `_refreshActiveProjectSetup()` gán giá
                  // trị mới nhưng không widget nào bị đánh dấu dirty ⇒
                  // checklist không rebuild. Bọc riêng `Obx` tại đúng
                  // call-site này (cùng pattern đã dùng cho banner ở dòng
                  // ~424) để đọc `activeProjectSetup.value` NGAY TRONG
                  // builder của chính `Obx` đó.
                  Expanded(
                    flex: 7,
                    child: Obx(
                      () => Top3FocusWidget(
                        actions: controller.top3Actions.toList(),
                        onActionTap: (action) =>
                            _handleActionTap(context, controller, action),
                      ),
                    ),
                  ),
                  const SizedBox(width: 24),

                  // C. Waiting for You (Decisions & Approvals) - Right Column
                  Expanded(
                    flex: 3,
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
              // Mobile Stacked layout — cùng lý do Obx-wrap như nhánh desktop
              // ở trên (Fix 1).
              Obx(
                () => Top3FocusWidget(
                  actions: controller.top3Actions.toList(),
                  onActionTap: (action) =>
                      _handleActionTap(context, controller, action),
                ),
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
    });
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
    return Obx(() {
      if (Get.isRegistered<LocaleController>()) {
        Get.find<LocaleController>().current.value;
      }
      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        child: AiWorkforceTab(
          packs: controller.workforcePacks.toList(),
          onTogglePack: (key, val) => controller.togglePack(key, val),
        ),
      );
    });
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
          () => (c.activeProjectId.value?.isEmpty ?? true)
              ? const SizedBox.shrink()
              : Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Icon(
                        c.sweepEnabled.value
                            ? Icons.smart_toy_outlined
                            : Icons.pause_circle_outline,
                        size: 16,
                        color: const Color(0xFF94A3B8),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          c.sweepEnabled.value
                              ? L10nKey.hubSweepEnabled.tr
                              : L10nKey.hubSweepDisabled.tr,
                          style: const TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 12,
                          ),
                        ),
                      ),
                      Switch(
                        value: c.sweepEnabled.value,
                        activeThumbColor: const Color(0xFF6366F1),
                        onChanged: c.setSweepEnabled,
                      ),
                    ],
                  ),
                ),
        ),
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
