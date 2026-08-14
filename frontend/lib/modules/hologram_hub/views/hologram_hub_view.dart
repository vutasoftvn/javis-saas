import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/hologram_hub_controller.dart';
import '../presentation/widgets/miva_hologram_core.dart';
import '../presentation/widgets/system_health_panel.dart';
import '../presentation/widgets/kpi_strip.dart';
import '../presentation/widgets/mobile_command_bar.dart';
import '../presentation/widgets/hub_chat_panel.dart';

class HologramHubView extends GetView<HologramHubController> {
  const HologramHubView({super.key});

  @override
  Widget build(BuildContext context) {
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

                  // 2. Main Content Area — fills remaining space, no scroll
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Left Rail — 3/12 of the desktop grid.
                          Expanded(
                            flex: 3,
                            child: LayoutBuilder(
                              builder: (context, constraints) {
                                const gap = 16.0;
                                return Obx(
                                  () => SystemHealthPanel(
                                    data: controller.hubSummary.value,
                                    gap: gap,
                                    onViewSubsystems: () =>
                                        controller.openDashboard(16, 4),
                                    onViewActivity: () =>
                                        controller.openDashboard(10, 4),
                                  ),
                                );
                              },
                            ),
                          ),
                          const SizedBox(width: 20),

                          // Center Core — 6/12 of the desktop grid.
                          Expanded(
                            flex: 6,
                            child: Center(
                              child: SizedBox(
                                width: double.infinity,
                                child: Obx(
                                  () => MivaHologramCore(
                                    runtimeState:
                                        controller.runtimeState.value,
                                    onTalkPressed: controller.onTalkPressed,
                                    onDashboardPressed: () =>
                                        controller.openDashboard(0, 0),
                                    onConversationModePressed:
                                        controller.onConversationModePressed,
                                    isConversationModeActive: controller
                                        .isConversationModeActive
                                        .value,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 20),

                          // Right Rail — 3/12 of the desktop grid (Hub Chat Card)
                          Expanded(
                            flex: 3,
                            child: HubChatPanel(controller: controller),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // 3. KPI Strip — fixed at bottom, never scrolls
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
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
                  const SizedBox(width: 10),

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
