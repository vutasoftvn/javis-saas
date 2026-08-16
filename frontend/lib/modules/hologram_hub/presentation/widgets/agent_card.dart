import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'hud_card.dart';

/// Agent Card Component for Hologram Hub (Harness Spec §22.1).
///
/// Displays canonical agent metrics:
/// - Agent Status & Domain
/// - Plan Step progress (x/y)
/// - Tool invocation count
/// - Verification checks passed (x/y)
/// - Interactive control actions [Open], [Pause/Resume]
class AgentCard extends StatelessWidget {
  final String agentName;
  final String domain;
  final String status; // 'idle', 'planning', 'executing', 'waiting_approval', 'paused', 'completed'
  final int planCurrentStep;
  final int planTotalSteps;
  final int toolsCount;
  final int verificationPassed;
  final int verificationTotal;
  final String currentActionDescription;
  final VoidCallback? onOpen;
  final VoidCallback? onTogglePause;

  const AgentCard({
    super.key,
    required this.agentName,
    required this.domain,
    this.status = 'idle',
    this.planCurrentStep = 0,
    this.planTotalSteps = 0,
    this.toolsCount = 0,
    this.verificationPassed = 0,
    this.verificationTotal = 0,
    this.currentActionDescription = '',
    this.onOpen,
    this.onTogglePause,
  });

  Color _getStatusColor() {
    switch (status.toLowerCase()) {
      case 'executing':
      case 'in_progress':
        return const Color(0xFF00F0FF);
      case 'planning':
      case 'thinking':
        return const Color(0xFF818CF8);
      case 'waiting_approval':
        return const Color(0xFFF59E0B);
      case 'paused':
      case 'blocked':
        return const Color(0xFFEF4444);
      case 'completed':
      case 'done':
        return const Color(0xFF10B981);
      case 'idle':
      default:
        return const Color(0xFF64748B);
    }
  }

  String _getStatusLabel() {
    switch (status.toLowerCase()) {
      case 'executing':
      case 'in_progress':
        return 'Đang thực thi';
      case 'planning':
      case 'thinking':
        return 'Lập kế hoạch';
      case 'waiting_approval':
        return 'Chờ phê duyệt';
      case 'paused':
      case 'blocked':
        return 'Tạm dừng';
      case 'completed':
      case 'done':
        return 'Hoàn thành';
      case 'idle':
      default:
        return 'Chờ lệnh (Idle)';
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _getStatusColor();
    final isPaused = status.toLowerCase() == 'paused' || status.toLowerCase() == 'blocked';

    return hudCard(
      onTap: onOpen,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Header: Agent Name + Domain & Status Badge
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: statusColor.withValues(alpha: 0.15),
                      border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                    ),
                    child: Icon(
                      Icons.smart_toy_outlined,
                      size: 16,
                      color: statusColor,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        agentName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        domain.toUpperCase(),
                        style: const TextStyle(
                          color: AppTheme.textMutedDark,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.6,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                ),
                child: Text(
                  _getStatusLabel(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),

          if (currentActionDescription.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              currentActionDescription,
              style: const TextStyle(
                color: Color(0xFFCBD5E1),
                fontSize: 12.5,
                height: 1.35,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],

          const SizedBox(height: 12),

          // 2. Metrics Bar (Plan x/y | Tools N | Verification x/y)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF131D38),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildMetricItem(
                  icon: Icons.alt_route,
                  label: 'Kế hoạch',
                  value: planTotalSteps > 0 ? '$planCurrentStep/$planTotalSteps' : 'N/A',
                  color: const Color(0xFF38BDF8),
                ),
                Container(width: 1, height: 24, color: const Color(0xFF1E293B)),
                _buildMetricItem(
                  icon: Icons.construction_outlined,
                  label: 'Công cụ',
                  value: '$toolsCount',
                  color: const Color(0xFF818CF8),
                ),
                Container(width: 1, height: 24, color: const Color(0xFF1E293B)),
                _buildMetricItem(
                  icon: Icons.verified_outlined,
                  label: 'Kiểm chứng',
                  value: verificationTotal > 0 ? '$verificationPassed/$verificationTotal' : 'OK',
                  color: const Color(0xFF10B981),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          // 3. Action Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (onTogglePause != null)
                TextButton.icon(
                  onPressed: onTogglePause,
                  icon: Icon(
                    isPaused ? Icons.play_arrow : Icons.pause,
                    size: 15,
                    color: isPaused ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                  ),
                  label: Text(
                    isPaused ? 'Tiếp tục' : 'Tạm dừng',
                    style: TextStyle(
                      fontSize: 12,
                      color: isPaused ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                    ),
                  ),
                ),
              const SizedBox(width: 8),
              if (onOpen != null)
                ElevatedButton.icon(
                  onPressed: onOpen,
                  icon: const Icon(Icons.visibility_outlined, size: 14),
                  label: const Text('Chi tiết', style: TextStyle(fontSize: 12)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1E293B),
                    foregroundColor: const Color(0xFF00F0FF),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    minimumSize: const Size(0, 32),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricItem({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: color),
            const SizedBox(width: 4),
            Text(
              value,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            color: AppTheme.textMutedDark,
            fontSize: 10,
          ),
        ),
      ],
    );
  }
}
