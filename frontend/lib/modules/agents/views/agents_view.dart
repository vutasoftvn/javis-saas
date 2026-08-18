import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/agents_controller.dart';
import 'widgets/agent_card.dart';
import 'widgets/agent_org_chart_widget.dart';
import 'widgets/agent_test_run_drawer.dart';
import 'widgets/agent_run_detail_dialog.dart';
import 'widgets/agent_routines_dialog.dart';
import 'widgets/work_product_viewer_dialog.dart';
import 'widgets/decision_records_dialog.dart';

class AgentsView extends GetView<AgentsController> {
  const AgentsView({super.key});

  final List<String> _departments = const [
    'All',
    'Finance',
    'Marketing',
    'Sales',
    'Engineering',
    'Legal',
    'HR',
    'Product',
    'Operations',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      body: Stack(
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header Bar
                    _buildHeaderBar(context),

                    // Master Control Plane KPI Summary Bar
                    _buildMasterKpiBar(context),

                    // Tab Views Content
                    Expanded(
                      child: Obx(() {
                        switch (controller.selectedTab.value) {
                          case 0:
                            return _buildDirectoryTab(context);
                          case 1:
                            return _buildOrgChartTab(context);
                          case 2:
                            return _buildRunsHistoryTab(context);
                          default:
                            return _buildDirectoryTab(context);
                        }
                      }),
                    ),
                  ],
                ),
              ),
            ],
          ),

          // Slide-Over Test Run Drawer
          Obx(() {
            if (controller.selectedAgentForTest.value == null) {
              return const SizedBox.shrink();
            }
            return Positioned(
              top: 0,
              right: 0,
              bottom: 0,
              child: AgentTestRunDrawer(
                agent: controller.selectedAgentForTest.value!,
                isLoading: controller.isTestingRun.value,
                result: controller.testRunResult.value,
                onClose: controller.closeTestRunDrawer,
                onExecute: (prompt, model, temp) {
                  controller.executeTestRun(prompt, model, temp);
                },
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildHeaderBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.blueAccent.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.smart_toy_rounded, color: Colors.blueAccent, size: 24),
          ),
          const SizedBox(width: 14),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'AI Workforce Control Plane',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                'Quản lý danh bạ nhân sự số, sơ đồ tổ chức và phiên thực thi',
                style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
              ),
            ],
          ),
          const Spacer(),

          // Tab Navigation Bar
          Obx(() {
            return Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Row(
                children: [
                  _buildNavTab(index: 0, title: 'Danh bạ Agent', icon: Icons.grid_view_rounded),
                  _buildNavTab(index: 1, title: 'Sơ đồ Org Chart', icon: Icons.account_tree_outlined),
                  _buildNavTab(index: 2, title: 'Lịch sử Runs', icon: Icons.history_rounded),
                ],
              ),
            );
          }),

          const SizedBox(width: 16),

          // Work Products Vault Button
          IconButton(
            tooltip: 'Sản phẩm bàn giao (Work Products)',
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => const WorkProductViewerDialog(),
              );
            },
            icon: const Icon(Icons.inventory_2_outlined, color: Colors.purpleAccent),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            ),
          ),

          const SizedBox(width: 8),

          // Decision Records (ADR) Button
          IconButton(
            tooltip: 'Sổ quyết định kiến trúc (ADR)',
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => const DecisionRecordsDialog(),
              );
            },
            icon: const Icon(Icons.bookmark_border_rounded, color: Colors.cyanAccent),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            ),
          ),

          const SizedBox(width: 8),

          // Autonomous Routines & Heartbeats Button
          IconButton(
            tooltip: 'Quy trình tự động & Heartbeats',
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => const AgentRoutinesDialog(),
              );
            },
            icon: const Icon(Icons.alarm_on_rounded, color: Colors.tealAccent),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            ),
          ),

          const SizedBox(width: 8),

          // Refresh Button
          IconButton(
            tooltip: 'Làm mới dữ liệu',
            onPressed: () {
              controller.loadAgents();
              controller.loadOrgChart();
              controller.loadRuns();
            },
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: Color(0xFF334155)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNavTab({required int index, required String title, required IconData icon}) {
    final isSelected = controller.selectedTab.value == index;
    return InkWell(
      onTap: () => controller.selectedTab.value = index,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? Colors.blueAccent : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(icon, size: 16, color: isSelected ? Colors.white : Colors.grey),
            const SizedBox(width: 8),
            Text(
              title,
              style: TextStyle(
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected ? Colors.white : Colors.grey,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // --- TAB 1: DIRECTORY ---
  Widget _buildDirectoryTab(BuildContext context) {
    return Column(
      children: [
        // Filter Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
          ),
          child: Row(
            children: [
              const Text('Phòng ban:', style: TextStyle(color: Colors.grey, fontSize: 13, fontWeight: FontWeight.w600)),
              const SizedBox(width: 12),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: _departments.map((dept) {
                      return Obx(() {
                        final isSelected = controller.selectedDepartment.value == dept;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: FilterChip(
                            label: Text(dept),
                            selected: isSelected,
                            onSelected: (_) => controller.filterByDepartment(dept),
                            selectedColor: Colors.blueAccent,
                            backgroundColor: const Color(0xFF1E293B),
                            labelStyle: TextStyle(
                              fontSize: 12.5,
                              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                              color: isSelected ? Colors.white : Colors.grey.shade400,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(20),
                              side: BorderSide(
                                color: isSelected ? Colors.blueAccent : const Color(0xFF334155),
                              ),
                            ),
                          ),
                        );
                      });
                    }).toList(),
                  ),
                ),
              ),
            ],
          ),
        ),

        // Grid View
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator(color: Colors.blueAccent));
            }
            if (controller.filteredAgents.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.person_search_outlined, size: 48, color: Colors.grey.shade600),
                    const SizedBox(height: 12),
                    Text('Không tìm thấy Agent nào trong phòng ban này.', style: TextStyle(color: Colors.grey.shade400)),
                  ],
                ),
              );
            }

            return LayoutBuilder(
              builder: (ctx, constraints) {
                int crossAxisCount = 3;
                if (constraints.maxWidth > 1400) {
                  crossAxisCount = 4;
                } else if (constraints.maxWidth < 900) {
                  crossAxisCount = 2;
                } else if (constraints.maxWidth < 600) {
                  crossAxisCount = 1;
                }

                return GridView.builder(
                  padding: const EdgeInsets.all(24),
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: crossAxisCount,
                    crossAxisSpacing: 18,
                    mainAxisSpacing: 18,
                    mainAxisExtent: 220,
                  ),
                  itemCount: controller.filteredAgents.length,
                  itemBuilder: (ctx, index) {
                    final agent = controller.filteredAgents[index];
                    return AgentCard(
                      agent: agent,
                      onTestRun: () => controller.openTestRunDrawer(agent),
                    );
                  },
                );
              },
            );
          }),
        ),
      ],
    );
  }

  // --- TAB 2: ORG CHART ---
  Widget _buildOrgChartTab(BuildContext context) {
    return Obx(() {
      if (controller.isLoadingOrgChart.value) {
        return const Center(child: CircularProgressIndicator(color: Colors.blueAccent));
      }
      return AgentOrgChartWidget(
        orgChartData: controller.orgChartData,
        onSelectAgent: (agentKey) {
          final match = controller.agents.firstWhereOrNull((a) => a['key'] == agentKey);
          if (match != null) {
            controller.openTestRunDrawer(match);
          }
        },
      );
    });
  }

  // --- TAB 3: RUNS HISTORY ---
  Widget _buildRunsHistoryTab(BuildContext context) {
    return Obx(() {
      if (controller.isLoadingRuns.value) {
        return const Center(child: CircularProgressIndicator(color: Colors.blueAccent));
      }
      if (controller.runs.isEmpty) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.history_toggle_off_rounded, size: 48, color: Colors.grey.shade600),
              const SizedBox(height: 12),
              Text('Chưa có lịch sử phiên chạy nào.', style: TextStyle(color: Colors.grey.shade400)),
            ],
          ),
        );
      }

      return ListView.separated(
        padding: const EdgeInsets.all(24),
        itemCount: controller.runs.length,
        separatorBuilder: (context, index) => const SizedBox(height: 10),
        itemBuilder: (ctx, index) {
          final run = controller.runs[index];
          final traceId = run['trace_id'] ?? 'N/A';
          final agentKey = run['agent_key'] ?? 'Unknown';
          final runtime = run['runtime_provider'] ?? 'Claude';
          final status = (run['status'] ?? 'completed').toString().toUpperCase();
          final duration = run['duration_ms'] ?? 0;
          final cost = (run['estimated_cost'] ?? 0.0).toStringAsFixed(4);
          final tokens = (run['input_tokens'] ?? 0) + (run['output_tokens'] ?? 0);

          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.blueAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.flash_on_rounded, color: Colors.blueAccent, size: 20),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Trace: $traceId',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                      Text(
                        'Agent: $agentKey | Runtime: $runtime | $tokens tokens',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade400),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      status,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF10B981)),
                    ),
                    Text(
                      '$duration ms | \$$cost',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade400),
                    ),
                  ],
                ),
                const SizedBox(width: 14),
                IconButton(
                  tooltip: 'Xem chi tiết Trace & Steps',
                  icon: const Icon(Icons.chevron_right_rounded, color: Colors.grey),
                  onPressed: () async {
                    final detail = await controller.getRunDetail(run['id']);
                    if (detail != null && context.mounted) {
                      showDialog(
                        context: context,
                        builder: (_) => AgentRunDetailDialog(runDetail: detail),
                      );
                    }
                  },
                ),
              ],
            ),
          );
        },
      );
    });
  }

  Widget _buildMasterKpiBar(BuildContext context) {
    return Obx(() {
      final totalAgents = controller.agents.length;
      final activeAgents = controller.agents.where((a) => a['status'] == 'busy').length;
      final runsCount = controller.runs.length;
      final runtimesCount = controller.runtimes.length;

      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        decoration: const BoxDecoration(
          color: Color(0xFF0F172A),
          border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
        ),
        child: Row(
          children: [
            _buildKpiBadge(
              icon: Icons.people_outline_rounded,
              color: Colors.blueAccent,
              label: 'Tổng Agent',
              value: '$totalAgents Agents ($activeAgents Active)',
            ),
            const SizedBox(width: 16),
            _buildKpiBadge(
              icon: Icons.bolt_rounded,
              color: const Color(0xFF10B981),
              label: 'Phiên Thực Thi',
              value: '$runsCount Runs',
            ),
            const SizedBox(width: 16),
            _buildKpiBadge(
              icon: Icons.hub_outlined,
              color: Colors.purpleAccent,
              label: 'Runtime Providers',
              value: '$runtimesCount Adapters (Multi-fallback)',
            ),
            const Spacer(),
            // Resilience status
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 14),
                  SizedBox(width: 6),
                  Text(
                    'Multi-Provider Fallback Active',
                    style: TextStyle(color: Color(0xFF10B981), fontSize: 11.5, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildKpiBadge({required IconData icon, required Color color, required String label, required String value}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Text('$label: ', style: TextStyle(color: Colors.grey.shade400, fontSize: 12)),
          Text(value, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

