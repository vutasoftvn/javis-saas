import 'package:flutter/material.dart';

class AgentActivityTimelineWidget extends StatelessWidget {
  final List<Map<String, dynamic>> events;
  final VoidCallback? onRefresh;

  const AgentActivityTimelineWidget({
    super.key,
    required this.events,
    this.onRefresh,
  });

  Color _getStatusColor(String? status) {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'success':
        return Colors.greenAccent;
      case 'running':
      case 'in_progress':
        return Colors.cyanAccent;
      case 'waiting_approval':
      case 'pending':
        return Colors.amberAccent;
      case 'failed':
      case 'error':
        return Colors.redAccent;
      default:
        return Colors.white70;
    }
  }

  IconData _getDomainIcon(String? domain) {
    switch (domain?.toLowerCase()) {
      case 'sales':
        return Icons.trending_up;
      case 'finance':
        return Icons.account_balance;
      case 'founder':
      case 'chief_of_staff':
        return Icons.psychology;
      case 'marketing':
        return Icons.campaign;
      case 'legal':
        return Icons.gavel;
      default:
        return Icons.smart_toy_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E222D),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.timeline, color: Colors.cyanAccent, size: 22),
                  SizedBox(width: 10),
                  Text(
                    'Agent Activity Timeline',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              if (onRefresh != null)
                IconButton(
                  icon: const Icon(Icons.refresh, color: Colors.white70, size: 20),
                  onPressed: onRefresh,
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (events.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 32),
              alignment: Alignment.center,
              child: const Text(
                'No agent execution events recorded yet.',
                style: TextStyle(color: Colors.white54),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: events.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final ev = events[index];
                final domain = ev['domain'] ?? ev['payload']?['domain'] ?? 'agent';
                final capability = ev['capability'] ?? ev['payload']?['capability'] ?? '';
                final eventType = ev['event_type'] ?? 'step_event';
                final tool = ev['tool_id'] ?? ev['payload']?['tool_id'];
                final status = ev['status'] ?? ev['payload']?['status'] ?? 'completed';
                final timestamp = ev['timestamp'] ?? '';
                final statusColor = _getStatusColor(status);

                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: statusColor.withValues(alpha: 0.2)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.12),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(_getDomainIcon(domain), color: statusColor, size: 18),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  '$domain : $capability',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                    fontSize: 14,
                                    color: Colors.white,
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: statusColor.withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    status.toUpperCase(),
                                    style: TextStyle(
                                      color: statusColor,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Event: $eventType ${tool != null ? '• Tool: $tool' : ''}',
                              style: const TextStyle(color: Colors.white70, fontSize: 12),
                            ),
                            if (timestamp.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(top: 4),
                                child: Text(
                                  timestamp,
                                  style: const TextStyle(color: Colors.white38, fontSize: 10),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
