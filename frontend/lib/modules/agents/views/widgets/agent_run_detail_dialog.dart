import 'package:flutter/material.dart';

class AgentRunDetailDialog extends StatelessWidget {
  final Map<String, dynamic> runDetail;

  const AgentRunDetailDialog({super.key, required this.runDetail});

  @override
  Widget build(BuildContext context) {
    final run = runDetail['run'] ?? runDetail;
    final List<dynamic> steps = runDetail['steps'] ?? [];

    final traceId = run['trace_id'] ?? 'N/A';
    final agentKey = run['agent_key'] ?? 'Unknown';
    final runtime = run['runtime_provider'] ?? 'Claude';
    final modelName = run['model_name'] ?? 'claude-3-5-sonnet';
    final status = run['status'] ?? 'completed';
    final durationMs = run['duration_ms'] ?? 0;
    final inputTokens = run['input_tokens'] ?? 0;
    final outputTokens = run['output_tokens'] ?? 0;
    final cost = run['estimated_cost'] ?? 0.0;
    final promptSnapshot = run['prompt_snapshot'] ?? '';
    final outputPayload = run['output_payload'] ?? '';

    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 780,
        height: 640,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.blueAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.analytics_outlined, color: Colors.blueAccent, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Chi tiết phiên chạy: $traceId',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                      Text(
                        'Agent: $agentKey | Runtime: $runtime ($modelName)',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade400),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close_rounded, color: Colors.grey),
                ),
              ],
            ),

            const SizedBox(height: 18),

            // Summary Metrics Bar
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildMetric('Trạng thái', status.toUpperCase(), valueColor: status == 'completed' ? const Color(0xFF10B981) : Colors.amber),
                  _buildMetric('Thời lượng', '$durationMs ms'),
                  _buildMetric('Input Tokens', '$inputTokens'),
                  _buildMetric('Output Tokens', '$outputTokens'),
                  _buildMetric('Chi phí (\$)', '\$${cost.toStringAsFixed(4)}', valueColor: const Color(0xFF10B981)),
                ],
              ),
            ),

            const SizedBox(height: 18),

            // Tabs / Content
            Expanded(
              child: DefaultTabController(
                length: 3,
                child: Column(
                  children: [
                    const TabBar(
                      tabs: [
                        Tab(text: 'Output Payload'),
                        Tab(text: 'Prompt Snapshot'),
                        Tab(text: 'Step Timeline'),
                      ],
                      labelColor: Colors.blueAccent,
                      unselectedLabelColor: Colors.grey,
                      indicatorColor: Colors.blueAccent,
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: TabBarView(
                        children: [
                          // Tab 1: Output
                          _buildCodeViewer(outputPayload.isNotEmpty ? outputPayload : 'No output payload recorded.'),
                          // Tab 2: Prompt
                          _buildCodeViewer(promptSnapshot.isNotEmpty ? promptSnapshot : 'No prompt snapshot recorded.'),
                          // Tab 3: Steps Timeline
                          steps.isEmpty
                              ? Center(
                                  child: Text('Không có bước con (step span) nào.', style: TextStyle(color: Colors.grey.shade500)),
                                )
                              : ListView.builder(
                                  itemCount: steps.length,
                                  itemBuilder: (ctx, i) {
                                    final step = steps[i];
                                    return Container(
                                      margin: const EdgeInsets.only(bottom: 8),
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF1E293B),
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: const Color(0xFF334155)),
                                      ),
                                      child: Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.all(6),
                                            decoration: BoxDecoration(
                                              color: Colors.blueAccent.withValues(alpha: 0.15),
                                              shape: BoxShape.circle,
                                            ),
                                            child: Text('${i + 1}', style: const TextStyle(color: Colors.blueAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                                          ),
                                          const SizedBox(width: 12),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  step['name'] ?? 'Step Span',
                                                  style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                                                ),
                                                Text(
                                                  'Type: ${step['step_type'] ?? 'unknown'} | Duration: ${step['duration_ms'] ?? 0} ms',
                                                  style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
                                                ),
                                              ],
                                            ),
                                          ),
                                          Text(
                                            (step['status'] ?? 'SUCCESS').toUpperCase(),
                                            style: const TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.w700),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
                                ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCodeViewer(String content) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF020617),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: SingleChildScrollView(
        child: SelectableText(
          content,
          style: const TextStyle(
            color: Color(0xFFE2E8F0),
            fontSize: 12.5,
            height: 1.5,
            fontFamily: 'monospace',
          ),
        ),
      ),
    );
  }

  Widget _buildMetric(String label, String value, {Color? valueColor}) {
    return Column(
      children: [
        Text(label, style: TextStyle(color: Colors.grey.shade400, fontSize: 11)),
        const SizedBox(height: 3),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
