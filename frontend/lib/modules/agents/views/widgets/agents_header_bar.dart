import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/agents_controller.dart';
import 'work_product_viewer_dialog.dart';
import 'decision_records_dialog.dart';
import 'agent_routines_dialog.dart';

class AgentsHeaderBar extends StatelessWidget {
  final AgentsController controller;

  const AgentsHeaderBar({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
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
}
