import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../controllers/founder_command_center_controller.dart';
import '../widgets/cofounder_card_widget.dart';
import '../widgets/top3_focus_widget.dart';
import '../widgets/waiting_for_you_widget.dart';
import '../widgets/decision_modal_sheet.dart';
import '../widgets/ai_workforce_tab.dart';
import '../presentation/widgets/cyber_circuit_background.dart';
import '../../../data/models/stage_model.dart';
import '../../../shared/widgets/stage_badge.dart';
import '../../../shared/widgets/company_scope_switcher.dart';
import '../../../core/routing/app_routes.dart';
import '../controllers/hologram_hub_controller.dart';

class HologramHubView extends StatelessWidget {
  const HologramHubView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(FounderCommandCenterController());

    return Scaffold(
      backgroundColor: const Color(0xFF040712),
      body: CyberCircuitBackground(
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
                      child: CircularProgressIndicator(color: Color(0xFF6366F1)),
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
                              _buildCommandCenterTab(context, controller, isWide),

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
    );
  }

  Widget _buildHeader(BuildContext context, FounderCommandCenterController controller) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.9),
        border: const Border(bottom: BorderSide(color: Color(0x336366F1), width: 1)),
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
                          gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)]),
                          borderRadius: BorderRadius.circular(10),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF6366F1).withValues(alpha: 0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: const Icon(Icons.rocket_launch, color: Colors.white, size: 18),
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
                                style: TextStyle(fontSize: 11, color: Colors.white.withValues(alpha: 0.5)),
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
                          child: StageBadge(stage: ProjectStage.fromString(stage), isCompact: true),
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

                      // Dashboard Button — vào màn hình quản trị (Dashboard)
                      IconButton(
                        onPressed: () => Get.find<HologramHubController>().onSettingsPressed(),
                        icon: const Icon(Icons.space_dashboard_outlined, color: Colors.white70, size: 20),
                        tooltip: 'Quản trị Dashboard',
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                      ),
                      const SizedBox(width: 4),

                      // Refresh Button
                      IconButton(
                        onPressed: () => controller.loadDashboardData(),
                        icon: const Icon(Icons.refresh, color: Colors.white70, size: 20),
                        tooltip: 'Làm mới dữ liệu',
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                      ),
                      const SizedBox(width: 4),

                      // Profile Button
                      IconButton(
                        onPressed: () => Get.toNamed(AppRoutes.profile),
                        icon: const Icon(Icons.account_circle_outlined, color: Colors.white70, size: 20),
                        tooltip: 'Hồ sơ của tôi',
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
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
          // A. Hero Co-Founder Card + Company Pulse
          CoFounderCardWidget(
            pulse: controller.pulse.value,
            onAskCosa: () => _openChatBottomSheet(context, controller),
          ),
          const SizedBox(height: 24),

          // Hiển thị Banner gợi ý khởi tạo dự án đầu tiên khi chưa có Project nào
          Obx(() {
            if (!controller.hasProjects.value) {
              return _buildFirstProjectBanner(context, controller);
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
                    onActionTap: (action) => _handleActionTap(context, controller, action),
                  ),
                ),
                const SizedBox(width: 24),

                // C. Waiting for You (Decisions & Approvals) - Right Column
                Expanded(
                  flex: 5,
                  child: WaitingForYouWidget(
                    decisions: controller.pendingDecisions.toList(),
                    approvals: controller.pendingApprovals.toList(),
                    onResolveDecision: (decId, optKey, notes) => controller.resolveDecision(
                      decisionId: decId,
                      optionKey: optKey,
                      founderNotes: notes,
                    ),
                    onApproveTask: (appId) => controller.approveTask(appId),
                    onRejectTask: (appId, reason) => controller.rejectTask(appId, reason),
                  ),
                ),
              ],
            )
          else ...[
            // Mobile Stacked layout
            Top3FocusWidget(
              actions: controller.top3Actions.toList(),
              onActionTap: (action) => _handleActionTap(context, controller, action),
            ),
            const SizedBox(height: 24),
            WaitingForYouWidget(
              decisions: controller.pendingDecisions.toList(),
              approvals: controller.pendingApprovals.toList(),
              onResolveDecision: (decId, optKey, notes) => controller.resolveDecision(
                decisionId: decId,
                optionKey: optKey,
                founderNotes: notes,
              ),
              onApproveTask: (appId) => controller.approveTask(appId),
              onRejectTask: (appId, reason) => controller.rejectTask(appId, reason),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildFirstProjectBanner(
    BuildContext context,
    FounderCommandCenterController controller,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1E1B4B), Color(0xFF312E81)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF818CF8).withValues(alpha: 0.4), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6366F1).withValues(alpha: 0.12),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isNarrow = constraints.maxWidth < 650;
          if (isNarrow) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6366F1).withValues(alpha: 0.25),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.rocket_launch, color: Color(0xFF818CF8), size: 24),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Khởi tạo Dự án Đầu tiên',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Workspace hiện chưa có dự án nào. Hãy thiết lập dự án để AI Co-Founder đề xuất Top 3 trọng tâm và kích hoạt chu trình 12-Week Year!',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.white.withValues(alpha: 0.75),
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 14),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _showCreateProjectDialog(context, controller),
                    icon: const Icon(Icons.add, size: 18, color: Colors.white),
                    label: const Text('Khởi tạo dự án ngay', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                      elevation: 4,
                    ),
                  ),
                ),
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF6366F1).withValues(alpha: 0.25),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.rocket_launch, color: Color(0xFF818CF8), size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Khởi tạo Dự án & Lộ trình Đầu tiên',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Workspace hiện chưa có dự án nào. Hãy thiết lập dự án để AI Co-Founder đề xuất Top 3 trọng tâm và kích hoạt chu trình 12-Week Year!',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.white.withValues(alpha: 0.75),
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              ElevatedButton.icon(
                onPressed: () => _showCreateProjectDialog(context, controller),
                icon: const Icon(Icons.add, size: 18, color: Colors.white),
                label: const Text('Khởi tạo dự án', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  elevation: 4,
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showCreateProjectDialog(
    BuildContext context,
    FounderCommandCenterController controller,
  ) {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    String selectedStage = 'P1_PROBLEM_VALIDATION';

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
                    style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              content: SizedBox(
                width: 480,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Tên dự án *', style: TextStyle(color: Colors.white70, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: titleController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Ví dụ: Nền tảng B2B SaaS cho Doanh nghiệp',
                        hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.35), fontSize: 13),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      ),
                    ),
                    const SizedBox(height: 14),
                    const Text('Mô tả bài toán / JTBD *', style: TextStyle(color: Colors.white70, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: descriptionController,
                      maxLines: 3,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Mô tả vấn đề khách hàng đang gặp phải, giải pháp dự kiến...',
                        hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.35), fontSize: 13),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      ),
                    ),
                    const SizedBox(height: 14),
                    const Text('Giai đoạn dự án (Stage)', style: TextStyle(color: Colors.white70, fontSize: 13)),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: selectedStage,
                          dropdownColor: const Color(0xFF1E293B),
                          isExpanded: true,
                          style: const TextStyle(color: Colors.white, fontSize: 13),
                          items: const [
                            DropdownMenuItem(value: 'P1_PROBLEM_VALIDATION', child: Text('P1: Xác thực Vấn đề (Problem Validation)')),
                            DropdownMenuItem(value: 'P2_SOLUTION_FIT', child: Text('P2: Phù hợp Giải pháp (Solution Fit)')),
                            DropdownMenuItem(value: 'P3_MVP_BUILD', child: Text('P3: Xây dựng MVP (MVP Build)')),
                            DropdownMenuItem(value: 'P4_PMF_GROWTH', child: Text('P4: Tăng trưởng & PMF (PMF Growth)')),
                            DropdownMenuItem(value: 'P5_SCALE_OPERATE', child: Text('P5: Vận hành Quy mô lớn (Scale & Operate)')),
                          ],
                          onChanged: (val) {
                            if (val != null) setModalState(() => selectedStage = val);
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('Hủy', style: TextStyle(color: Colors.white60)),
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
                    await controller.createFirstProject(
                      title: title,
                      description: desc.isNotEmpty ? desc : 'Khởi tạo dự án đầu tiên cho doanh nghiệp.',
                      stage: selectedStage,
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6366F1),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  child: const Text('Khởi tạo dự án', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
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
        final found = controller.pendingDecisions.firstWhereOrNull((d) => d.id == decId);
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
      _openChatBottomSheet(
        context,
        controller,
        initialMessage: 'Tôi muốn thiết lập hồ sơ doanh nghiệp mới. Hãy hướng dẫn tôi định hình Vision, Problem và Target Market!',
      );
      return;
    } else if (action.id == 'act_genesis_12wy') {
      _openChatBottomSheet(
        context,
        controller,
        initialMessage: 'Hãy hướng dẫn tôi thiết lập Mục tiêu 12-Week Year cho Quý đầu tiên.',
      );
      return;
    }

    _openChatBottomSheet(context, controller);
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

  void _openChatBottomSheet(
    BuildContext context,
    FounderCommandCenterController controller, {
    String? initialMessage,
  }) {
    if (initialMessage != null && initialMessage.isNotEmpty) {
      controller.chatInputController.text = initialMessage;
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.75,
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          padding: EdgeInsets.only(
            top: 20,
            left: 20,
            right: 20,
            bottom: MediaQuery.of(context).viewInsets.bottom + 20,
          ),
          child: Column(
            children: [
              Row(
                children: [
                  const Icon(Icons.psychology, color: Color(0xFF8B5CF6), size: 24),
                  const SizedBox(width: 10),
                  const Text(
                    'Trao đổi cùng COSA Co-Founder',
                    style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.pop(ctx),
                    icon: const Icon(Icons.close, color: Colors.white70),
                  ),
                ],
              ),
              const Divider(color: Color(0x336366F1)),
              Expanded(
                child: Obx(() {
                  if (controller.chatMessages.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.chat_bubble_outline, size: 48, color: Colors.white.withValues(alpha: 0.2)),
                          const SizedBox(height: 12),
                          Text(
                            'Hãy hỏi COSA về tiến độ kinh doanh, phản biện giả định hoặc giao Mission!',
                            style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    );
                  }

                  return ListView.builder(
                    itemCount: controller.chatMessages.length,
                    itemBuilder: (c, idx) {
                      final msg = controller.chatMessages[idx];
                      final isUser = msg['role'] == 'user';
                      final isError = msg['role'] == 'error';
                      return Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 6),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isUser
                                ? const Color(0xFF6366F1)
                                : (isError ? const Color(0x33EF4444) : const Color(0xFF1E293B)),
                            borderRadius: BorderRadius.circular(12),
                            border: isError ? Border.all(color: const Color(0xFFEF4444), width: 1) : null,
                          ),
                          child: Text(
                            msg['content'] ?? '',
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                          ),
                        ),
                      );
                    },
                  );
                }),
              ),
              if (controller.isChatLoading.value)
                const Padding(
                  padding: EdgeInsets.all(8.0),
                  child: LinearProgressIndicator(color: Color(0xFF6366F1)),
                ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller.chatInputController,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Nhập tin nhắn trao đổi với Co-Founder...',
                        hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                      onSubmitted: (text) => controller.sendChatMessage(text),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () => controller.sendChatMessage(controller.chatInputController.text),
                    icon: const Icon(Icons.send, color: Color(0xFF6366F1)),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}
