import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/hologram_hub_controller.dart';
import '../presentation/widgets/miva_hologram_core.dart';
import '../presentation/widgets/kpi_strip.dart';
import '../presentation/widgets/mobile_command_bar.dart';
import '../presentation/widgets/hub_chat_panel.dart';
import '../presentation/widgets/agent_card.dart';
import '../presentation/widgets/task_card.dart';
import 'widgets/company_pulse_bar.dart';
import 'widgets/today_priority_list.dart';
import 'widgets/quick_approval_queue.dart';
import 'widgets/active_missions_tracker.dart';
import 'widgets/funding_readiness_card.dart';

import '../presentation/widgets/cyber_circuit_background.dart';
import '../presentation/widgets/glass_card.dart';

class HologramHubView extends GetView<HologramHubController> {
  const HologramHubView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<HologramHubController>()) {
      Get.put(HologramHubController());
    }
    return Scaffold(
      backgroundColor: const Color(0xFF040712),
      body: CyberCircuitBackground(
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 1100;

              // ── MOBILE layout: centered/top animated orb + chat history + 2 icons/command bar ──
              if (!isWide) {
                return _buildMobileLayout(context);
              }

              // ── DESKTOP / WIDE layout ────────────────────────────────────
              return Column(
                children: [
                  // 1. Top Header Bar (Fixed Top with 24px padding & rounded corners)
                  _buildHeader(context),

                  // 2. Middle Area (Stack fills space between AppBar and Bottom KPI Strip)
                  Expanded(
                    child: Obx(() {
                      final ccData = controller.commandCenterData.value;
                      final pulse = ccData?['company_pulse'] as Map<String, dynamic>?;
                      final priorities = ccData?['today_priorities'] as List<dynamic>? ?? [];
                      final missions = ccData?['active_missions'] as List<dynamic>? ?? [];
                      final funding = ccData?['funding_readiness'] as Map<String, dynamic>?;
                      final hasFunding = funding != null &&
                          funding['readiness_score_avg'] != null &&
                          (funding['readiness_score_avg'] as num) > 0;

                      final approvals = ccData?['waiting_for_you'] as List<dynamic>? ?? [];
                      final hasMessages = controller.mobileMessages.isNotEmpty;
                      final isListening = controller.isVoiceListening.value ||
                          controller.runtimeState.value == HologramRuntimeState.listening;
                      final isSpeaking = controller.runtimeState.value == HologramRuntimeState.speaking;
                      final isThinking = controller.runtimeState.value == HologramRuntimeState.thinking;
                      final isChatActive = controller.isChatInputActive.value ||
                          hasMessages ||
                          isListening ||
                          isSpeaking ||
                          isThinking;
                      final hasRightContent = isChatActive;
                      final activePage = controller.activeContextualPage.value;

                      return Stack(
                        clipBehavior: Clip.none,
                        children: [
                          // A. Central 3D Hologram Brain (Centered in MiddleArea, never covered by AppBar)
                          if (activePage == 'none')
                            Positioned.fill(
                              child: Center(
                                child: MivaHologramCore(
                                  runtimeState: controller.runtimeState.value,
                                  onTalkPressed: controller.onTalkPressed,
                                  onDashboardPressed: () => controller.openDashboard(0, 0),
                                  onConversationModePressed: controller.onConversationModePressed,
                                  isConversationModeActive: controller.isConversationModeActive.value,
                                  showActionButtons: false,
                                ),
                              ),
                            ),

                          // B. Left Rail (Approvals Queue + Company Pulse + Action Cards — padding top: 24px below AppBar)
                          Positioned(
                            left: 24,
                            top: 24,
                            bottom: 24,
                            width: 320,
                            child: SingleChildScrollView(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  if (approvals.isNotEmpty) ...[
                                    QuickApprovalQueue(
                                      approvals: approvals,
                                      onApprove: (id, decision, reason) =>
                                          controller.handleQuickApprove(id, decision, reason),
                                      onViewAll: () => controller.openProposalDetail(),
                                    ),
                                    const SizedBox(height: 14),
                                  ],
                                  CompanyPulseBar(pulseData: pulse),
                                  if (priorities.isNotEmpty) ...[
                                    const SizedBox(height: 14),
                                    TodayPriorityList(
                                      priorities: priorities,
                                      onToggleTask: (id) => controller.togglePriorityTask(id),
                                      onTapTask: (id) => controller.openDashboard(1, 0),
                                    ),
                                  ],
                                  if (missions.isNotEmpty) ...[
                                    const SizedBox(height: 14),
                                    ActiveMissionsTracker(
                                      missions: missions,
                                      onTapMission: (id) => controller.openMissionInspector(id),
                                    ),
                                  ],
                                  if (hasFunding) ...[
                                    const SizedBox(height: 14),
                                    FundingReadinessCard(fundingData: funding),
                                  ],
                                ],
                              ),
                            ),
                          ),

                          // C. Contextual Workspace (when active)
                          if (activePage != 'none')
                            Positioned.fill(
                              top: 24,
                              bottom: 24,
                              left: 24,
                              right: 24,
                              child: _buildContextualWorkspace(context),
                            ),

                          // D. Central Controls:
                          // 2 icon buttons -> padding 32px -> 4 command buttons -> padding 24px -> khung chat (bottom: 24px)
                          if (activePage == 'none' && !isChatActive)
                            Positioned(
                              left: 0,
                              right: 0,
                              bottom: 24,
                              child: Center(
                                child: _buildCentralControlStack(context),
                              ),
                            ),

                          // E. Right Rail (Chat Panel Floating — Topmost layer, padding top: 24px below AppBar)
                          if (hasRightContent)
                            Positioned(
                              right: 24,
                              top: 24,
                              bottom: 24,
                              width: 390,
                              child: HubChatPanel(controller: controller),
                            ),
                        ],
                      );
                    }),
                  ),

                  // 3. Bottom Row Card (KPI Strip — Fixed Bottom with 24px padding)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                    child: Obx(() {
                      final kpiData = controller.hubSummary.value?['kpi_strip']
                          as Map<String, dynamic>?;
                      return KpiStrip(
                        kpiData: kpiData,
                        onCardTap: (tabIdx) =>
                            controller.openDashboard(tabIdx, 0),
                      );
                    }),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildMobileLayout(BuildContext context) {
    return Stack(
      children: [
        // 1. Central Hologram Orb with Smooth Scaling (1.0 -> 0.5) and Translation (Center -> Top 32px)
        Obx(() {
          final isChatActive = controller.isChatInputActive.value;
          return AnimatedAlign(
            duration: const Duration(milliseconds: 400),
            curve: Curves.easeInOutCubic,
            alignment: isChatActive ? Alignment.topCenter : Alignment.center,
            child: Padding(
              padding: EdgeInsets.only(top: isChatActive ? 32.0 : 0.0),
              child: AnimatedScale(
                duration: const Duration(milliseconds: 400),
                curve: Curves.easeInOutCubic,
                scale: isChatActive ? 0.5 : 1.0,
                alignment: Alignment.topCenter,
                child: MivaHologramCore(
                  runtimeState: controller.runtimeState.value,
                  onTalkPressed: controller.onTalkPressed,
                  onDashboardPressed: () => controller.openDashboard(0, 0),
                  onConversationModePressed:
                      controller.onConversationModePressed,
                  isConversationModeActive:
                      controller.isConversationModeActive.value,
                ),
              ),
            ),
          );
        }),

        // 2. Chat History Messages (Top layer between top scaled orb and bottom command bar)
        Obx(() {
          final isChatActive = controller.isChatInputActive.value;
          return AnimatedPositioned(
            duration: const Duration(milliseconds: 400),
            curve: Curves.easeInOutCubic,
            top: isChatActive ? 212 : MediaQuery.of(context).size.height,
            bottom: 100,
            left: 16,
            right: 16,
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 350),
              curve: Curves.easeInOutCubic,
              opacity: isChatActive ? 1.0 : 0.0,
              child: isChatActive
                  ? _buildMobileChatHistory()
                  : const SizedBox.shrink(),
            ),
          );
        }),

        // 3. Bottom Controls (2 Standard Icons <-> Chat Input Bar)
        Positioned(
          left: 0,
          right: 0,
          bottom: 32,
          child: Obx(
            () => MobileCommandBar(
              runtimeState: controller.runtimeState.value,
              isChatInputActive: controller.isChatInputActive.value,
              isConversationModeActive:
                  controller.isConversationModeActive.value,
              isVoiceListening:
                  controller.isVoiceListening.value ||
                  controller.runtimeState.value ==
                      HologramRuntimeState.listening,
              onOpenChat: controller.openChatInput,
              onCloseChat: controller.closeChatInput,
              onVoiceTap: () {
                if (controller.isConversationModeActive.value) {
                  controller.onConversationModePressed();
                } else {
                  controller.onTalkPressed();
                }
              },
              onVoiceLongPress: controller.onConversationModePressed,
              onSubmit: controller.executePrompt,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCentralControlStack(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // 1. 2 Icon Buttons (Conversation Mode & Dashboard)
        _buildCentralTwoIconButtons(context),

        const SizedBox(height: 32), // Padding 32px to 4 command buttons

        // 2. 4 Command Buttons (Quick Chips)
        _buildQuickCommandChips(context),

        const SizedBox(height: 24), // Padding 24px to khung chat

        // 3. Khung Chat (Floating Command Bar)
        _buildFloatingCommandBar(context),
      ],
    );
  }

  Widget _buildCentralTwoIconButtons(BuildContext context) {
    return Obx(() {
      final isConvActive = controller.isConversationModeActive.value;
      return Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Tooltip(
            message: isConvActive ? 'Dừng hội thoại' : 'Chế độ Hội thoại',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: controller.onConversationModePressed,
                borderRadius: BorderRadius.circular(100),
                child: Container(
                  width: 48,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: isConvActive
                        ? const LinearGradient(
                            colors: [Color(0xFF00F0FF), Color(0xFF0072FF)],
                          )
                        : LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Colors.white.withValues(alpha: 0.08),
                              Colors.white.withValues(alpha: 0.02),
                            ],
                          ),
                    borderRadius: BorderRadius.circular(100),
                    boxShadow: [
                      BoxShadow(
                        color: isConvActive
                            ? const Color(0xFF00F0FF).withValues(alpha: 0.45)
                            : Colors.black.withValues(alpha: 0.35),
                        blurRadius: 16,
                        spreadRadius: 0.5,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Icon(
                    isConvActive
                        ? Icons.graphic_eq
                        : Icons.record_voice_over,
                    color: isConvActive
                        ? const Color(0xFF04070E)
                        : const Color(0xFF00F0FF),
                    size: 22,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Tooltip(
            message: 'Bảng Điều khiển',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => controller.openDashboard(0, 0),
                borderRadius: BorderRadius.circular(100),
                child: Container(
                  width: 48,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Colors.white.withValues(alpha: 0.08),
                        Colors.white.withValues(alpha: 0.02),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(100),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.35),
                        blurRadius: 14,
                        offset: const Offset(0, 2),
                      ),
                      BoxShadow(
                        color: const Color(0xFF38BDF8).withValues(alpha: 0.05),
                        blurRadius: 12,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.dashboard_customize_outlined,
                    color: Color(0xFF38BDF8),
                    size: 22,
                  ),
                ),
              ),
            ),
          ),
        ],
      );
    });
  }

  Widget _buildQuickCommandChips(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildCustomActionChip(
            icon: Icons.account_tree_outlined,
            label: 'Đội ngũ 12 Agents',
            color: const Color(0xFF00F0FF),
            onTap: () => controller.openWorkforceModal(context),
          ),
          const SizedBox(width: 8),
          _buildCustomActionChip(
            icon: Icons.gavel_outlined,
            label: 'Duyệt lệnh rủi ro',
            color: const Color(0xFFEF4444),
            onTap: () => controller.openApprovalInboxDrawer(context),
          ),
          const SizedBox(width: 8),
          _buildCustomActionChip(
            icon: Icons.assignment_turned_in_outlined,
            label: 'Thành phẩm AI',
            color: const Color(0xFF10B981),
            onTap: () => controller.openWorkProductModal(context),
          ),
          const SizedBox(width: 8),
          _buildQuickChip(
            icon: Icons.dashboard_outlined,
            label: 'Tổng quan vận hành',
            prompt: 'Tóm tắt tổng quan công việc, OKRs và tình hình vận hành hôm nay.',
          ),
          const SizedBox(width: 8),
          _buildQuickChip(
            icon: Icons.track_changes_outlined,
            label: 'Tiến độ OKRs',
            prompt: 'Báo cáo tình hình thực thi các mục tiêu OKRs quan trọng quý này.',
          ),
          const SizedBox(width: 8),
          _buildQuickChip(
            icon: Icons.analytics_outlined,
            label: 'Báo cáo tài chính',
            prompt: 'Tạo báo cáo tóm tắt tài chính và các chỉ số vận hành gần nhất.',
          ),
        ],
      ),
    );
  }

  Widget _buildCustomActionChip({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    Color color = const Color(0xFF38BDF8),
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(100),
        onTap: onTap,
        child: GlassCard(
          borderRadius: 100,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: color,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFloatingCommandBar(BuildContext context) {
    final textController = TextEditingController();
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 680),
      child: GlassCard(
        borderRadius: 100,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.40),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
          BoxShadow(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
            blurRadius: 20,
            spreadRadius: 1,
          ),
        ],
        child: Row(
          children: [
            // Voice Mic button
            Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(100),
                onTap: controller.onTalkPressed,
                child: Container(
                  width: 44,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: const Color(0xFF00F0FF).withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Icon(
                    Icons.mic_rounded,
                    color: Color(0xFF00F0FF),
                    size: 20,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),

            // Seamless Full-Width Text Field directly inside the outer glass dock
            Expanded(
              child: TextField(
                controller: textController,
                textAlignVertical: TextAlignVertical.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                ),
                decoration: const InputDecoration(
                  filled: false,
                  fillColor: Colors.transparent,
                  hintText: 'Hỏi COSA AI hoặc gõ lệnh...',
                  hintStyle: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 14,
                  ),
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  disabledBorder: InputBorder.none,
                  errorBorder: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(vertical: 12),
                ),
                onSubmitted: (val) {
                  final trimmed = val.trim();
                  if (trimmed.isNotEmpty) {
                    textController.clear();
                    controller.executePrompt(trimmed);
                    controller.openChatInput();
                  }
                },
              ),
            ),

            const SizedBox(width: 12),

            // Send Button with borderRadius 100
            Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(100),
                onTap: () {
                  final trimmed = textController.text.trim();
                  if (trimmed.isNotEmpty) {
                    textController.clear();
                    controller.executePrompt(trimmed);
                    controller.openChatInput();
                  }
                },
                child: Container(
                  width: 44,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF00F0FF), Color(0xFF0072FF)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(100),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF00F0FF).withValues(alpha: 0.35),
                        blurRadius: 10,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.send_rounded,
                    color: Color(0xFF04070E),
                    size: 18,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickChip({
    required IconData icon,
    required String label,
    required String prompt,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(100),
        onTap: () {
          controller.executePrompt(prompt);
          controller.openChatInput();
        },
        child: GlassCard(
          borderRadius: 100,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: const Color(0xFF38BDF8)),
              const SizedBox(width: 6),
              Text(
                label,
                style: const TextStyle(
                  color: Color(0xFFE2E8F0),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMobileChatHistory() {
    return Obx(() {
      final msgs = controller.mobileMessages;
      if (msgs.isEmpty) {
        return const SizedBox.shrink();
      }

      return GlassCard(
        padding: EdgeInsets.zero,
        borderRadius: 16,
        child: Column(
          children: [
            // Chat Header with Clear Button
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 8,
              ),
              decoration: BoxDecoration(
                color: const Color(0xFF0D172A).withValues(alpha: 0.8),
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(15)),
              ),
              child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(
                          Icons.psychology,
                          size: 16,
                          color: Color(0xFF00F0FF),
                        ),
                        SizedBox(width: 6),
                        Text(
                          'HỘI THOẠI',
                          style: TextStyle(
                            color: Color(0xFF38BDF8),
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                          ),
                        ),
                      ],
                    ),
                    GestureDetector(
                      onTap: controller.clearMobileHistory,
                      child: Tooltip(
                        message: 'Xoá lịch sử chat',
                        child: Container(
                          padding: const EdgeInsets.all(5),
                          decoration: BoxDecoration(
                            color: const Color(
                              0xFFEF4444,
                            ).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(
                            Icons.delete_outline_rounded,
                            size: 18,
                            color: Color(0xFFEF4444),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Chat Messages List (rendered from bottom up)
              Expanded(
                child: ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  itemCount: msgs.length,
                  itemBuilder: (context, index) {
                    final msg = msgs[msgs.length - 1 - index];
                    final isUser = msg['role'] == 'user';
                    final text = msg['text'] ?? '';
                    return _buildChatMessageBubble(text: text, isUser: isUser);
                  },
                ),
              ),
            ],
          ),
        );
      });
    }

  Widget _buildChatMessageBubble({required String text, required bool isUser}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              width: 26,
              height: 26,
              margin: const EdgeInsets.only(right: 8, top: 2),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF38BDF8).withValues(alpha: 0.16),
              ),
              child: const Icon(
                Icons.psychology,
                size: 15,
                color: Color(0xFF7DD3FC),
              ),
            ),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                gradient: isUser
                    ? LinearGradient(
                        colors: [
                          const Color(0xFF0369A1).withValues(alpha: 0.80),
                          const Color(0xFF0EA5E9).withValues(alpha: 0.80),
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isUser
                    ? null
                    : const Color(0xFF0D172A).withValues(alpha: 0.92),
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(isUser ? 14 : 3),
                  topRight: Radius.circular(isUser ? 3 : 14),
                  bottomLeft: const Radius.circular(14),
                  bottomRight: const Radius.circular(14),
                ),
                boxShadow: [
                  BoxShadow(
                    color: isUser
                        ? const Color(0xFF0EA5E9).withValues(alpha: 0.18)
                        : Colors.black.withValues(alpha: 0.25),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: text.isEmpty && !isUser
                  ? Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF38BDF8)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'COSA đang suy nghĩ...',
                          style: TextStyle(
                            color: const Color(0xFF94A3B8),
                            fontSize: 13,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    )
                  : Text(
                      text,
                      style: TextStyle(
                        color: isUser ? Colors.white : const Color(0xFFCBD5E1),
                        fontSize: 14,
                        height: 1.5,
                        fontWeight: isUser ? FontWeight.w600 : FontWeight.w400,
                      ),
                    ),
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            Container(
              width: 26,
              height: 26,
              margin: const EdgeInsets.only(left: 0, top: 2),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.08),
              ),
              child: const Icon(
                Icons.person,
                size: 15,
                color: Color(0xFF94A3B8),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 768;

        if (isMobile) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            color: Colors.transparent,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Left: Logo + COSA Title
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(
                            0xFF00F0FF,
                          ).withValues(alpha: 0.35),
                        ),
                      ),
                      child: const Icon(
                        Icons.psychology,
                        size: 20,
                        color: Color(0xFF00F0FF),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ShaderMask(
                      shaderCallback: (bounds) => const LinearGradient(
                        colors: [Color(0xFF00F0FF), Color(0xFF38BDF8)],
                      ).createShader(bounds),
                      child: const Text(
                        'COSA',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.5,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),

                // Right: Notifications + Profile Menu
                Row(
                  children: [
                    _buildSystemStatus(),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(
                        Icons.notifications_none_outlined,
                        color: Color(0xFF94A3B8),
                        size: 18,
                      ),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(
                        minWidth: 32,
                        minHeight: 32,
                      ),
                      tooltip: 'Thông báo',
                      onPressed: () {},
                    ),
                    const SizedBox(width: 4),
                    PopupMenuButton<String>(
                      color: const Color(0xFF0D172A),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: const BorderSide(color: Color(0xFF1E293B)),
                      ),
                      offset: const Offset(0, 40),
                      onSelected: (value) {
                        if (value == 'logout') {
                          controller.logout();
                        } else if (value == 'settings') {
                          controller.onSettingsPressed();
                        }
                      },
                      itemBuilder: (context) => [
                        PopupMenuItem(
                          value: 'info',
                          enabled: false,
                          child: Obx(
                            () => Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  controller.userName.value,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 15,
                                  ),
                                ),
                                Text(
                                  controller.userRole.value,
                                  style: const TextStyle(
                                    color: Color(0xFF00F0FF),
                                    fontSize: 14,
                                  ),
                                ),
                                const Divider(
                                  color: Color(0xFF1E293B),
                                  height: 16,
                                ),
                              ],
                            ),
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'settings',
                          child: Row(
                            children: [
                              Icon(
                                Icons.settings_outlined,
                                color: Color(0xFF94A3B8),
                                size: 18,
                              ),
                              SizedBox(width: 10),
                              Text(
                                'Cài đặt hệ thống',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'logout',
                          child: Row(
                            children: [
                              Icon(
                                Icons.logout,
                                color: Color(0xFFEF4444),
                                size: 18,
                              ),
                              SizedBox(width: 10),
                              Text(
                                'Đăng xuất',
                                style: TextStyle(
                                  color: Color(0xFFEF4444),
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                      child: Container(
                        padding: const EdgeInsets.all(5),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0D172A),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFF1E293B)),
                        ),
                        child: const Icon(
                          Icons.person,
                          size: 16,
                          color: Color(0xFF38BDF8),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        }

        // Wide Header (Desktop / Tablet) — Floating Glass with 24px padding, smooth shadow, no border
        return Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.45),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.20),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
                BoxShadow(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.05),
                  blurRadius: 20,
                  spreadRadius: 0.5,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.white.withValues(alpha: 0.08),
                      Colors.white.withValues(alpha: 0.02),
                    ],
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    // Left: MIVA Logo + Live Time & Date
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: const Color(0xFF00F0FF).withValues(alpha: 0.35),
                      ),
                    ),
                    child: const Icon(
                      Icons.psychology,
                      size: 26,
                      color: Color(0xFF00F0FF),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ShaderMask(
                        shaderCallback: (bounds) => const LinearGradient(
                          colors: [Color(0xFF00F0FF), Color(0xFF38BDF8)],
                        ).createShader(bounds),
                        child: const Text(
                          'COSA',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 2.0,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      const Text(
                        'COMPANY ONE SYSTEM AI',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.2,
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(width: 24),
                  Container(
                    height: 32,
                    width: 1,
                    color: const Color(0xFF1E293B),
                  ),
                  const SizedBox(width: 24),
                  // Clock readout
                  Obx(() {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          controller.currentTime.value,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                            letterSpacing: 0.5,
                          ),
                        ),
                        Text(
                          controller.currentDate.value,
                          style: const TextStyle(
                            fontSize: 14,
                            color: Color(0xFF94A3B8),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    );
                  }),
                ],
              ),

              // Right: Workforce Pill, Approvals, System Status, Profile
              Row(
                children: [
                  _buildWorkforceHeaderBadge(context),
                  const SizedBox(width: 8),
                  _buildApprovalHeaderButton(context),
                  const SizedBox(width: 8),
                  _buildSystemStatus(),
                  const SizedBox(width: 12),
                  IconButton(
                    icon: const Icon(
                      Icons.notifications_none_outlined,
                      color: Color(0xFF94A3B8),
                      size: 20,
                    ),
                    tooltip: 'Thông báo',
                    onPressed: () {},
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.graphic_eq,
                      color: Color(0xFF00F0FF),
                      size: 20,
                    ),
                    tooltip: 'Neural Stream',
                    onPressed: () {},
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.wifi,
                      color: Color(0xFF10B981),
                      size: 20,
                    ),
                    tooltip: 'Trạng thái kết nối',
                    onPressed: () {},
                  ),
                  const SizedBox(width: 12),

                  // Operating Mode Switcher (Founder, Operator, Developer)
                  Obx(() {
                    final mode = controller.operatingMode.value;
                    final modeColor = mode == 'developer'
                        ? const Color(0xFF818CF8)
                        : (mode == 'operator' ? const Color(0xFFF59E0B) : const Color(0xFF00F0FF));

                    return PopupMenuButton<String>(
                      color: const Color(0xFF0D172A),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: const BorderSide(color: Color(0xFF1E293B)),
                      ),
                      offset: const Offset(0, 40),
                      onSelected: (val) => controller.setOperatingMode(val),
                      itemBuilder: (ctx) => [
                        const PopupMenuItem(
                          value: 'founder',
                          child: Row(
                            children: [
                              Icon(Icons.verified_user_outlined, color: Color(0xFF00F0FF), size: 16),
                              SizedBox(width: 8),
                              Text('👑 Founder Mode', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'operator',
                          child: Row(
                            children: [
                              Icon(Icons.settings_suggest_outlined, color: Color(0xFFF59E0B), size: 16),
                              SizedBox(width: 8),
                              Text('⚙️ Operator Mode', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'developer',
                          child: Row(
                            children: [
                              Icon(Icons.science_outlined, color: Color(0xFF818CF8), size: 16),
                              SizedBox(width: 8),
                              Text('🔬 Developer Mode', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                            ],
                          ),
                        ),
                      ],
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF131D38),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: modeColor.withValues(alpha: 0.6)),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              mode == 'developer'
                                  ? Icons.science_outlined
                                  : (mode == 'operator' ? Icons.settings_suggest_outlined : Icons.verified_user_outlined),
                              size: 14,
                              color: modeColor,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              controller.userRole.value,
                              style: TextStyle(
                                color: modeColor,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Icon(Icons.arrow_drop_down, size: 16, color: Color(0xFF94A3B8)),
                          ],
                        ),
                      ),
                    );
                  }),
                  const SizedBox(width: 12),

                  // User Profile Pill with Menu & Logout
                  PopupMenuButton<String>(
                    color: const Color(0xFF0D172A),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(color: Color(0xFF1E293B)),
                    ),
                    offset: const Offset(0, 45),

                    onSelected: (value) {
                      if (value == 'logout') {
                        controller.logout();
                      } else if (value == 'settings') {
                        controller.onSettingsPressed();
                      }
                    },
                    itemBuilder: (context) => [
                      PopupMenuItem(
                        value: 'info',
                        enabled: false,
                        child: Obx(
                          () => Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                controller.userName.value,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 15,
                                ),
                              ),
                              Text(
                                controller.userRole.value,
                                style: const TextStyle(
                                  color: Color(0xFF00F0FF),
                                  fontSize: 14,
                                ),
                              ),
                              const Divider(
                                color: Color(0xFF1E293B),
                                height: 16,
                              ),
                            ],
                          ),
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'settings',
                        child: Row(
                          children: [
                            Icon(
                              Icons.settings_outlined,
                              color: Color(0xFF94A3B8),
                              size: 18,
                            ),
                            SizedBox(width: 10),
                            Text(
                              'Cài đặt hệ thống',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'logout',
                        child: Row(
                          children: [
                            Icon(
                              Icons.logout,
                              color: Color(0xFFEF4444),
                              size: 18,
                            ),
                            SizedBox(width: 10),
                            Text(
                              'Đăng xuất',
                              style: TextStyle(
                                color: Color(0xFFEF4444),
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0D172A),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFF1E293B)),
                      ),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: const Color(
                              0xFF38BDF8,
                            ).withValues(alpha: 0.2),
                            child: const Icon(
                              Icons.person,
                              size: 16,
                              color: Color(0xFF38BDF8),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Obx(() {
                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  controller.userName.value,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                Text(
                                  controller.userRole.value,
                                  style: const TextStyle(
                                    color: Color(0xFF64748B),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            );
                          }),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_drop_down,
                            color: Color(0xFF64748B),
                            size: 18,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ),
  );
      },
    );
  }

  Widget _buildContextualWorkspace(BuildContext context) {
    final pageType = controller.activeContextualPage.value;
    String title = 'KHÔNG GIAN VẬN HÀNH';
    IconData icon = Icons.dashboard_outlined;

    if (pageType == 'timeline_detail') {
      title = 'LỘ TRÌNH CHU KỲ N-TUẦN (12WY)';
      icon = Icons.timeline;
    } else if (pageType == 'report_detail') {
      title = 'BÁO CÁO ĐIỀU HÀNH TỔNG HỢP';
      icon = Icons.assessment_outlined;
    } else if (pageType == 'proposal_detail') {
      title = 'DANH SÁCH ĐỀ XUẤT CHỜ PHÊ DUYỆT';
      icon = Icons.gavel_outlined;
    } else if (pageType == 'agent_activity') {
      title = 'HOẠT ĐỘNG AGENT';
      icon = Icons.smart_toy_outlined;
    }

    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.45),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
          BoxShadow(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.05),
            blurRadius: 20,
            spreadRadius: 0.5,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Contextual Workspace Top Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
            ),
            child: Row(
              children: [
                Icon(icon, color: const Color(0xFF00F0FF), size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.1,
                    ),
                  ),
                ),
                Obx(() {
                  final isPinned = controller.isContextPinned.value;
                  return IconButton(
                    icon: Icon(
                      isPinned ? Icons.push_pin : Icons.push_pin_outlined,
                      color: isPinned ? const Color(0xFF00F0FF) : const Color(0xFF64748B),
                      size: 18,
                    ),
                    tooltip: isPinned ? 'Bỏ ghim' : 'Ghim trang này',
                    onPressed: controller.togglePinContext,
                  );
                }),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF94A3B8), size: 18),
                  tooltip: 'Đóng về Hologram',
                  onPressed: controller.forceCloseContextualPage,
                ),
              ],
            ),
          ),

          // Mini Voice Indicator when live voice is active
          Obx(() {
            if (!controller.isConversationModeActive.value) {
              return const SizedBox.shrink();
            }
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: const Color(0xFF00F0FF).withValues(alpha: 0.1),
              child: Row(
                children: [
                  const Icon(Icons.graphic_eq, color: Color(0xFF00F0FF), size: 16),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Live Voice đang kết nối — Hologram đang lắng nghe yêu cầu thoại...',
                      style: TextStyle(color: Color(0xFF00F0FF), fontSize: 12, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            );
          }),

          // Body Content based on pageType
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _buildContextualBody(pageType),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContextualBody(String pageType) {
    if (pageType == 'timeline_detail') {
      final cycle = controller.activeCycleTimeline.value?['cycle'] as Map<String, dynamic>? ?? {};
      final duration = cycle['duration_weeks'] as int? ?? 13;
      final currentWeek = cycle['current_week'] as int? ?? 1;

      return ListView(
        children: [
          Text(
            cycle['title'] as String? ?? 'Chu kỳ Chiến lược N-Tuần',
            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'Tuần hiện tại: $currentWeek / $duration tuần. Tất cả mục tiêu chiến lược và kết quả then chốt được theo dõi thời gian thực.',
            style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: controller.openTwelveWeekYear,
            icon: const Icon(Icons.open_in_new, size: 16),
            label: const Text('Mở toàn màn hình Module 12WY'),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B)),
          ),
        ],
      );
    } else if (pageType == 'proposal_detail') {
      return Obx(() {
        final approvals = controller.pendingApprovals;
        if (approvals.isEmpty) {
          return const Center(
            child: Text(
              'Không có đề xuất nào đang chờ phê duyệt.',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
            ),
          );
        }
        return ListView.separated(
          itemCount: approvals.length,
          separatorBuilder: (context, index) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final approval = approvals[index];
            final id = (approval['id'] ?? '').toString();
            return TaskCard(
              title: (approval['tool_name'] ?? '').toString(),
              status: 'waiting_approval',
              assignedAgent: approval['requested_by_agent']?.toString(),
              projectName: approval['capability']?.toString(),
              riskLevel: _mapApprovalRiskLevel(approval['risk_level']?.toString()),
              currentStepText: approval['action_type']?.toString(),
              onApprove: () => controller.approveTaskCard(id),
              onReject: () => controller.rejectTaskCard(id),
            );
          },
        );
      });
    } else if (pageType == 'agent_activity') {
      return Obx(() {
        final runs = controller.agentRuns;
        if (runs.isEmpty) {
          return const Center(
            child: Text(
              'Chưa có hoạt động agent gần đây.',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
            ),
          );
        }
        return ListView.separated(
          itemCount: runs.length,
          separatorBuilder: (context, index) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final run = runs[index];
            return AgentCard(
              agentName: (run['agent_key'] ?? '').toString(),
              domain: (run['provider'] ?? run['runtime'] ?? '').toString(),
              status: _mapRunStatus(run['status']?.toString()),
              currentActionDescription: (run['error_message'] ?? run['job_type'] ?? '').toString(),
            );
          },
        );
      });
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.analytics_outlined, color: Color(0xFF00F0FF), size: 40),
          const SizedBox(height: 12),
          const Text(
            'Báo cáo Tiến độ Điều hành Đã Sẵn sàng',
            style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Bạn có thể yêu cầu tạo báo cáo theo chu kỳ hoặc đọc tóm tắt qua Voice bất kỳ lúc nào.',
            style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  String _mapApprovalRiskLevel(String? riskLevel) {
    switch (riskLevel) {
      case 'critical':
        return 'L3A';
      case 'high':
        return 'L2';
      case 'medium':
        return 'L1';
      case 'low':
      default:
        return 'L0';
    }
  }

  String _mapRunStatus(String? status) {
    switch (status) {
      case 'running':
      case 'retrying':
      case 'fallback':
        return 'executing';
      case 'awaiting_approval':
        return 'waiting_approval';
      case 'completed':
        return 'completed';
      case 'failed':
      case 'cancelled':
        return 'paused';
      case 'created':
      default:
        return 'idle';
    }
  }

  Widget _buildSystemStatus() {
    return IconButton(
      icon: const Icon(
        Icons.check_circle_rounded,
        color: Color(0xFF10B981),
        size: 20,
      ),
      tooltip: 'Hệ thống đang hoạt động',
      onPressed: () {},
    );
  }

  Widget _buildWorkforceHeaderBadge(BuildContext context) {
    return Obx(() {
      final cpSummary = controller.controlPlaneSummary.value;
      final wf = cpSummary?['workforce_status'] as Map<String, dynamic>?;
      final fin = cpSummary?['financials'] as Map<String, dynamic>?;
      final totalAgents = wf?['total_agents'] ?? (controller.workforceAgents.isNotEmpty ? controller.workforceAgents.length : 12);
      final costUsd = (fin?['total_cost_usd'] as num?)?.toDouble() ?? 0.0;
      final costVnd = (fin?['total_cost_vnd'] as num?)?.toInt() ?? 0;

      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => controller.openWorkforceModal(context),
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xFF00F0FF).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF00F0FF).withValues(alpha: 0.35)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.hub_outlined, size: 15, color: Color(0xFF00F0FF)),
                const SizedBox(width: 6),
                Text(
                  '$totalAgents Agents',
                  style: const TextStyle(
                    color: Color(0xFF00F0FF),
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  '• \$$costUsd ($costVnd đ)',
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    });
  }

  Widget _buildApprovalHeaderButton(BuildContext context) {
    return Obx(() {
      final cpSummary = controller.controlPlaneSummary.value;
      final gov = cpSummary?['governance'] as Map<String, dynamic>?;
      final pendingCount = (gov?['pending_approvals_count'] as num?)?.toInt() ?? controller.activeApprovals.length;

      return Stack(
        clipBehavior: Clip.none,
        children: [
          IconButton(
            icon: Icon(
              pendingCount > 0 ? Icons.gavel : Icons.security_outlined,
              color: pendingCount > 0 ? const Color(0xFFEF4444) : const Color(0xFF94A3B8),
              size: 20,
            ),
            tooltip: pendingCount > 0 ? '$pendingCount yêu cầu rủi ro cần duyệt' : 'Phê duyệt rủi ro',
            onPressed: () => controller.openApprovalInboxDrawer(context),
          ),
          if (pendingCount > 0)
            Positioned(
              right: 6,
              top: 6,
              child: Container(
                padding: const EdgeInsets.all(3),
                decoration: const BoxDecoration(
                  color: Color(0xFFEF4444),
                  shape: BoxShape.circle,
                ),
                constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                child: Text(
                  '$pendingCount',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
        ],
      );
    });
  }
}


