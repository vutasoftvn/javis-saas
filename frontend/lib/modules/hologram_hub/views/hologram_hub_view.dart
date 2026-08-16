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

class HologramHubView extends GetView<HologramHubController> {
  const HologramHubView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<HologramHubController>()) {
      Get.put(HologramHubController());
    }
    return Scaffold(
      backgroundColor: const Color(0xFF070C18),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0.0, -0.2),
            radius: 1.2,
            colors: [Color(0xFF0B1934), Color(0xFF070C18), Color(0xFF04070E)],
            stops: [0.0, 0.65, 1.0],
          ),
        ),
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
                  // 1. Top Header Bar (Desktop / Wide screens only)
                  _buildHeader(context),
                  const Divider(
                    height: 1,
                    thickness: 1,
                    color: Color(0xFF1E293B),
                  ),

                  // 2. Company Pulse Banner
                  Obx(() {
                    final ccData = controller.commandCenterData.value;
                    final pulse = ccData?['company_pulse'] as Map<String, dynamic>?;
                    return Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
                      child: CompanyPulseBar(pulseData: pulse),
                    );
                  }),

                  // 3. Main Content Area — fills remaining space
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Left Rail — 3.5/12 of the desktop grid: Priorities & Active Missions
                          Expanded(
                            flex: 3,
                            child: Obx(() {
                              final ccData = controller.commandCenterData.value;
                              final priorities = ccData?['today_priorities'] as List<dynamic>? ?? [];
                              final missions = ccData?['active_missions'] as List<dynamic>? ?? [];

                              return SingleChildScrollView(
                                child: Column(
                                  children: [
                                    TodayPriorityList(
                                      priorities: priorities,
                                      onToggleTask: (id) => controller.togglePriorityTask(id),
                                      onTapTask: (id) => controller.openDashboard(1, 0),
                                    ),
                                    const SizedBox(height: 16),
                                    ActiveMissionsTracker(
                                      missions: missions,
                                      onTapMission: (id) => controller.openDashboard(3, 0),
                                    ),
                                  ],
                                ),
                              );
                            }),
                          ),
                          const SizedBox(width: 16),

                          // Center Core — 5/12 of the desktop grid: Hologram Core Avatar
                          Expanded(
                            flex: 5,
                            child: Obx(() {
                              final activePage = controller.activeContextualPage.value;
                              if (activePage != 'none') {
                                return _buildContextualWorkspace(context);
                              }
                              return Center(
                                child: SizedBox(
                                  width: double.infinity,
                                  child: MivaHologramCore(
                                    runtimeState: controller.runtimeState.value,
                                    onTalkPressed: controller.onTalkPressed,
                                    onDashboardPressed: () => controller.openDashboard(0, 0),
                                    onConversationModePressed: controller.onConversationModePressed,
                                    isConversationModeActive: controller.isConversationModeActive.value,
                                  ),
                                ),
                              );
                            }),
                          ),
                          const SizedBox(width: 16),

                          // Right Rail — 4/12 of the desktop grid: Waiting For You Approvals & Chat
                          Expanded(
                            flex: 4,
                            child: Obx(() {
                              final ccData = controller.commandCenterData.value;
                              final approvals = ccData?['waiting_for_you'] as List<dynamic>? ?? [];

                              return Column(
                                children: [
                                  if (approvals.isNotEmpty) ...[
                                    QuickApprovalQueue(
                                      approvals: approvals,
                                      onApprove: (id, decision, reason) =>
                                          controller.handleQuickApprove(id, decision, reason),
                                      onAskAI: (id) =>
                                          controller.executePrompt('Phân tích chi tiết về yêu cầu phê duyệt #$id'),
                                      onViewAll: () => controller.openProposalDetail(),
                                    ),
                                    const SizedBox(height: 12),
                                  ],
                                  Expanded(
                                    child: HubChatPanel(controller: controller),
                                  ),
                                ],
                              );
                            }),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // 4. KPI Strip — fixed at bottom, never scrolls
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                    child: Obx(() {
                      final kpiData =
                          controller.hubSummary.value?['kpi_strip']
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
        // 1. Chat History Messages (appears between top scaled orb and bottom command bar)
        Obx(() {
          final isChatActive = controller.isChatInputActive.value;
          return AnimatedPositioned(
            duration: const Duration(milliseconds: 400),
            curve: Curves.easeInOutCubic,
            top: isChatActive ? 212 : MediaQuery.of(context).size.height,
            bottom: 76,
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

        // 3. Central Hologram Orb with Smooth Scaling (1.0 -> 0.5) and Translation (Center -> Top 32px)
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

        // 4. Active Listening Feedback Overlay (shown when listening)
        Obx(() {
          final isListening =
              controller.isVoiceListening.value ||
              controller.runtimeState.value == HologramRuntimeState.listening;
          final isChatActive = controller.isChatInputActive.value;
          if (!isListening) return const SizedBox.shrink();

          return Positioned(
            top: isChatActive
                ? 148
                : (MediaQuery.of(context).size.height / 2 + 130),
            left: 20,
            right: 20,
            child: _buildActiveListeningIndicator(),
          );
        }),

        // 5. Bottom Controls (2 Standard Icons <-> Chat Input Bar)
        Positioned(
          left: 0,
          right: 0,
          bottom: 8,
          child: Obx(
            () => MobileCommandBar(
              runtimeState: controller.runtimeState.value,
              isChatInputActive: controller.isChatInputActive.value,
              isVoiceListening:
                  controller.isVoiceListening.value ||
                  controller.runtimeState.value ==
                      HologramRuntimeState.listening,
              onOpenChat: controller.openChatInput,
              onCloseChat: controller.closeChatInput,
              onVoiceTap: controller.onTalkPressed,
              onVoiceLongPress: controller.onConversationModePressed,
              onSubmit: controller.executePrompt,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMobileChatHistory() {
    return Obx(() {
      final msgs = controller.mobileMessages;
      if (msgs.isEmpty) {
        return const SizedBox.shrink();
      }

      return Container(
        decoration: BoxDecoration(
          color: const Color(0xFF070C18).withValues(alpha: 0.88),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: const Color(0xFF1E293B).withValues(alpha: 0.8),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF00F0FF).withValues(alpha: 0.06),
              blurRadius: 18,
              spreadRadius: 1,
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Column(
            children: [
              // Chat Header with Clear Button
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                color: const Color(0xFF0D172A).withValues(alpha: 0.9),
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
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            Container(
              width: 24,
              height: 24,
              margin: const EdgeInsets.only(right: 6, bottom: 2),
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [Color(0xFF00D2FF), Color(0xFF0072FF)],
                ),
              ),
              child: const Icon(
                Icons.psychology,
                size: 14,
                color: Colors.white,
              ),
            ),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              decoration: BoxDecoration(
                gradient: isUser
                    ? const LinearGradient(
                        colors: [Color(0xFF0072FF), Color(0xFF00D2FF)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isUser
                    ? null
                    : const Color(0xFF0D172A).withValues(alpha: 0.95),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(14),
                  topRight: const Radius.circular(14),
                  bottomLeft: Radius.circular(isUser ? 14 : 3),
                  bottomRight: Radius.circular(isUser ? 3 : 14),
                ),
                border: isUser
                    ? null
                    : Border.all(color: const Color(0xFF1E293B), width: 1),
                boxShadow: [
                  BoxShadow(
                    color: isUser
                        ? const Color(0xFF00D2FF).withValues(alpha: 0.2)
                        : Colors.black.withValues(alpha: 0.3),
                    blurRadius: 8,
                  ),
                ],
              ),
              child: Text(
                text,
                style: TextStyle(
                  color: isUser ? const Color(0xFF04070E) : Colors.white,
                  fontSize: 14,
                  height: 1.45,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 6),
            Container(
              width: 24,
              height: 24,
              margin: const EdgeInsets.only(left: 0, bottom: 2),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF1E293B),
                border: Border.all(color: const Color(0xFF334155), width: 1),
              ),
              child: const Icon(
                Icons.person,
                size: 14,
                color: Color(0xFF38BDF8),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildActiveListeningIndicator() {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF0B1934).withValues(alpha: 0.92),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.6),
            width: 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF00F0FF).withValues(alpha: 0.25),
              blurRadius: 16,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: const Color(0xFF00F0FF),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF00F0FF).withValues(alpha: 0.8),
                    blurRadius: 8,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            const Text(
              'Đang lắng nghe chủ động...',
              style: TextStyle(
                color: Color(0xFF00F0FF),
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
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

        // Wide Header (Desktop / Tablet)
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          color: const Color(0xFF080F1E),
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
                        'HỆ THỐNG AI DOANH NGHIỆP',
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

              // Right: Notifications, Waveform, Connectivity, Profile
              Row(
                children: [
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
        color: const Color(0xFF0B132B).withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1E293B)),
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
}

