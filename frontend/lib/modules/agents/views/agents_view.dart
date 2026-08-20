import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/agents_controller.dart';
import 'widgets/agent_org_chart_widget.dart';
import 'widgets/agent_test_run_drawer.dart';
import 'widgets/agents_header_bar.dart';
import 'widgets/agents_kpi_summary_bar.dart';
import 'widgets/agents_directory_tab.dart';
import 'widgets/agents_runs_history_tab.dart';

class AgentsView extends GetView<AgentsController> {
  const AgentsView({super.key});

  static const List<String> departments = [
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
                    // 1. Header Bar
                    AgentsHeaderBar(controller: controller),

                    // 2. Master KPI Summary Bar
                    AgentsKpiSummaryBar(controller: controller),

                    // 3. Tab Views Content
                    Expanded(
                      child: Obx(() {
                        switch (controller.selectedTab.value) {
                          case 0:
                            return AgentsDirectoryTab(
                              controller: controller,
                              departments: departments,
                            );
                          case 1:
                            return _buildOrgChartTab();
                          case 2:
                            return AgentsRunsHistoryTab(controller: controller);
                          default:
                            return AgentsDirectoryTab(
                              controller: controller,
                              departments: departments,
                            );
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

  Widget _buildOrgChartTab() {
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
}
