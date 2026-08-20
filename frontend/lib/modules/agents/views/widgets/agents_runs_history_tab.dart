import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/agents_controller.dart';
import 'agent_run_detail_dialog.dart';

class AgentsRunsHistoryTab extends StatelessWidget {
  final AgentsController controller;

  const AgentsRunsHistoryTab({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
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
}
