import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/hologram_hub_controller.dart';
import '../presentation/widgets/miva_hologram_core.dart';
import '../presentation/widgets/system_health_panel.dart';
import '../presentation/widgets/memory_core_panel.dart';
import '../presentation/widgets/kpi_strip.dart';
import '../presentation/widgets/next_actions_panel.dart';
import '../presentation/widgets/quick_commands_bar.dart';
import '../presentation/widgets/global_command_bar.dart';

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
            colors: [
              Color(0xFF0B1934),
              Color(0xFF070C18),
              Color(0xFF04070E),
            ],
            stops: [0.0, 0.65, 1.0],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 1100;

              return Column(
                children: [
                  // 1. Top Header Bar
                  _buildHeader(context),
                  const Divider(height: 1, thickness: 1, color: Color(0xFF1E293B)),

                  // 2. Main Content Area
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (isWide)
                            // Desktop / Wide 3-column Layout
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Left Rail (System Health, Voice, Subsystems, Activity)
                                SizedBox(
                                  width: 270,
                                  child: Obx(() {
                                    return SystemHealthPanel(
                                      data: controller.hubSummary.value,
                                      onViewSubsystems: () => controller.openDashboard(16, 4), // Diagnostics
                                      onViewActivity: () => controller.openDashboard(10, 4),   // Audit log
                                    );
                                  }),
                                ),
                                const SizedBox(width: 24),

                                // Center Core (Hologram Orb, AI OS tagline, Actions, Quick Commands)
                                Expanded(
                                  child: Column(
                                    children: [
                                      const SizedBox(height: 10),
                                      Obx(() {
                                        return MivaHologramCore(
                                          runtimeState: controller.runtimeState.value,
                                          onTalkPressed: controller.onTalkPressed,
                                          onDashboardPressed: () => controller.openDashboard(0, 0),
                                        );
                                      }),
                                      const SizedBox(height: 32),
                                      QuickCommandsBar(
                                        onCommandTap: controller.handleQuickCommand,
                                      ),
                                      const SizedBox(height: 20),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 24),

                                // Right Rail (Memory Core, Active Agents, Build Mode)
                                SizedBox(
                                  width: 270,
                                  child: Column(
                                    children: [
                                      Obx(() {
                                        return MemoryCorePanel(
                                          data: controller.hubSummary.value,
                                          onViewAgents: () => controller.openDashboard(7, 0), // Agents
                                        );
                                      }),
                                      Obx(() {
                                        return NextActionsPanel(
                                          actions: controller.ceoNextActions.toList(),
                                          onViewAll: controller.openStrategyNextActions,
                                        );
                                      }),
                                    ],
                                  ),
                                ),
                              ],
                            )
                          else
                            // Tablet / Mobile Responsive Column Layout
                            Column(
                              children: [
                                Obx(() {
                                  return MivaHologramCore(
                                    runtimeState: controller.runtimeState.value,
                                    onTalkPressed: controller.onTalkPressed,
                                    onDashboardPressed: () => controller.openDashboard(0, 0),
                                  );
                                }),
                                const SizedBox(height: 20),
                                QuickCommandsBar(
                                  onCommandTap: controller.handleQuickCommand,
                                ),
                                const SizedBox(height: 24),
                                Obx(() {
                                  return SystemHealthPanel(
                                    data: controller.hubSummary.value,
                                    onViewSubsystems: () => controller.openDashboard(16, 4),
                                    onViewActivity: () => controller.openDashboard(10, 4),
                                  );
                                }),
                                const SizedBox(height: 16),
                                Obx(() {
                                  return MemoryCorePanel(
                                    data: controller.hubSummary.value,
                                    onViewAgents: () => controller.openDashboard(7, 0),
                                  );
                                }),
                                const SizedBox(height: 16),
                                Obx(() {
                                  return NextActionsPanel(
                                    actions: controller.ceoNextActions.toList(),
                                    onViewAll: controller.openStrategyNextActions,
                                  );
                                }),
                              ],
                            ),

                          const SizedBox(height: 20),

                          // 3. Bottom KPI Strip (7 cards)
                          Obx(() {
                            final kpiData = controller.hubSummary.value?['kpi_strip'] as Map<String, dynamic>?;
                            return KpiStrip(
                              kpiData: kpiData,
                              onCardTap: (tabIdx) => controller.openDashboard(tabIdx, 0),
                            );
                          }),
                          const SizedBox(height: 16),
                        ],
                      ),
                    ),
                  ),

                  // 4. Bottom Global Command Bar
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    decoration: const BoxDecoration(
                      color: Color(0xFF080F1E),
                      border: Border(top: BorderSide(color: Color(0xFF1E293B))),
                    ),
                    child: GlobalCommandBar(
                      onSubmit: controller.executePrompt,
                      onSettingsTap: controller.onSettingsPressed,
                      onThemeTap: controller.onThemeToggle,
                      onVoiceTap: controller.onTalkPressed,
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
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
                child: const Icon(Icons.psychology, size: 26, color: Color(0xFF00F0FF)),
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
                      fontSize: 9.5,
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
                        fontSize: 11,
                        color: Color(0xFF94A3B8),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                );
              }),
            ],
          ),

          // Center: cosa.os Pill Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF0D172A).withValues(alpha: 0.8),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: const Color(0xFF00F0FF).withValues(alpha: 0.3),
                width: 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.1),
                  blurRadius: 10,
                ),
              ],
            ),
            child: const Text(
              'cosa.os',
              style: TextStyle(
                color: Color(0xFF38BDF8),
                fontSize: 13,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.2,
              ),
            ),
          ),

          // Right: Notifications, Waveform, Connectivity, Profile
          Row(
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_none_outlined, color: Color(0xFF94A3B8), size: 20),
                tooltip: 'Thông báo',
                onPressed: () {},
              ),
              IconButton(
                icon: const Icon(Icons.graphic_eq, color: Color(0xFF00F0FF), size: 20),
                tooltip: 'Neural Stream',
                onPressed: () {},
              ),
              IconButton(
                icon: const Icon(Icons.wifi, color: Color(0xFF10B981), size: 20),
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
                    child: Obx(() => Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              controller.userName.value,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                              ),
                            ),
                            Text(
                              controller.userRole.value,
                              style: const TextStyle(
                                color: Color(0xFF00F0FF),
                                fontSize: 11,
                              ),
                            ),
                            const Divider(color: Color(0xFF1E293B), height: 16),
                          ],
                        )),
                  ),
                  const PopupMenuItem(
                    value: 'settings',
                    child: Row(
                      children: [
                        Icon(Icons.settings_outlined, color: Color(0xFF94A3B8), size: 18),
                        SizedBox(width: 10),
                        Text('Cài đặt hệ thống', style: TextStyle(color: Colors.white, fontSize: 13)),
                      ],
                    ),
                  ),
                  const PopupMenuItem(
                    value: 'logout',
                    child: Row(
                      children: [
                        Icon(Icons.logout, color: Color(0xFFEF4444), size: 18),
                        SizedBox(width: 10),
                        Text('Đăng xuất', style: TextStyle(color: Color(0xFFEF4444), fontSize: 13)),
                      ],
                    ),
                  ),
                ],
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0D172A),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 14,
                        backgroundColor: const Color(0xFF38BDF8).withValues(alpha: 0.2),
                        child: const Icon(Icons.person, size: 16, color: Color(0xFF38BDF8)),
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
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              controller.userRole.value,
                              style: const TextStyle(
                                color: Color(0xFF64748B),
                                fontSize: 10,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        );
                      }),
                      const SizedBox(width: 4),
                      const Icon(Icons.arrow_drop_down, color: Color(0xFF64748B), size: 18),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
