import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/agents_controller.dart';

class AgentsKpiSummaryBar extends StatelessWidget {
  final AgentsController controller;

  const AgentsKpiSummaryBar({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
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
