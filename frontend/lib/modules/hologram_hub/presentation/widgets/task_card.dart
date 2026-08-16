import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'hud_card.dart';

/// Task Card Component for Hologram Hub (Harness Spec §22.2).
///
/// Displays canonical task execution metrics:
/// - Status, Assigned Agent, Project Ref
/// - Progress indicator & Step details
/// - Risk Profile (L0-L3A) & Approval Gate status
/// - Interactive controls [Approve], [Reject], [Pause/Resume]
class TaskCard extends StatelessWidget {
  final String title;
  final String status;
  final String? assignedAgent;
  final String? projectName;
  final double progressPercent;
  final String riskLevel; // 'L0', 'L1', 'L2', 'L3', 'L3A'
  final String? currentStepText;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;
  final VoidCallback? onTogglePause;
  final VoidCallback? onTap;

  const TaskCard({
    super.key,
    required this.title,
    required this.status,
    this.assignedAgent,
    this.projectName,
    this.progressPercent = 0.0,
    this.riskLevel = 'L0',
    this.currentStepText,
    this.onApprove,
    this.onReject,
    this.onTogglePause,
    this.onTap,
  });

  Color _getStatusColor() {
    switch (status.toLowerCase()) {
      case 'in_progress':
      case 'executing':
        return const Color(0xFF00F0FF);
      case 'waiting_approval':
        return const Color(0xFFF59E0B);
      case 'blocked':
      case 'paused':
        return const Color(0xFFEF4444);
      case 'done':
      case 'completed':
        return const Color(0xFF10B981);
      case 'todo':
      default:
        return const Color(0xFF38BDF8);
    }
  }

  String _getStatusLabel() {
    switch (status.toLowerCase()) {
      case 'in_progress':
      case 'executing':
        return 'Đang thực hiện';
      case 'waiting_approval':
        return 'Chờ phê duyệt';
      case 'blocked':
      case 'paused':
        return 'Tạm dừng / Nghẽn';
      case 'done':
      case 'completed':
        return 'Đã hoàn thành';
      case 'todo':
      default:
        return 'Cần làm';
    }
  }

  Color _getRiskColor() {
    switch (riskLevel.toUpperCase()) {
      case 'L3A':
      case 'L3':
        return const Color(0xFFEF4444);
      case 'L2':
        return const Color(0xFFF59E0B);
      case 'L1':
        return const Color(0xFF38BDF8);
      case 'L0':
      default:
        return const Color(0xFF10B981);
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _getStatusColor();
    final riskColor = _getRiskColor();
    final isWaitingApproval = status.toLowerCase() == 'waiting_approval';
    final isBlocked = status.toLowerCase() == 'blocked' || status.toLowerCase() == 'paused';
    final isInProgress = status.toLowerCase() == 'in_progress' || status.toLowerCase() == 'executing';

    return hudCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Header: Status + Risk Badge
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.circle, size: 6, color: statusColor),
                    const SizedBox(width: 5),
                    Text(
                      _getStatusLabel(),
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: riskColor.withValues(alpha: 0.4)),
                ),
                child: Text(
                  'Risk $riskLevel',
                  style: TextStyle(
                    color: riskColor,
                    fontSize: 10.5,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 10),

          // 2. Title & Project/Agent info
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.bold,
              height: 1.3,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),

          const SizedBox(height: 6),

          Row(
            children: [
              if (projectName != null && projectName!.isNotEmpty) ...[
                const Icon(Icons.folder_outlined, size: 12, color: AppTheme.textMutedDark),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    projectName!,
                    style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11.5),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
              if (assignedAgent != null && assignedAgent!.isNotEmpty) ...[
                const SizedBox(width: 8),
                const Icon(Icons.smart_toy_outlined, size: 12, color: Color(0xFF00F0FF)),
                const SizedBox(width: 4),
                Text(
                  assignedAgent!,
                  style: const TextStyle(color: Color(0xFF00F0FF), fontSize: 11.5, fontWeight: FontWeight.w500),
                ),
              ],
            ],
          ),

          const SizedBox(height: 10),

          // 3. Progress Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (progressPercent / 100.0).clamp(0.0, 1.0),
              backgroundColor: const Color(0xFF1E293B),
              valueColor: AlwaysStoppedAnimation<Color>(statusColor),
              minHeight: 5,
            ),
          ),

          if (currentStepText != null && currentStepText!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              currentStepText!,
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],

          const SizedBox(height: 10),

          // 4. Governance & Lifecycle Actions
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (isWaitingApproval && onReject != null)
                TextButton(
                  onPressed: onReject,
                  style: TextButton.styleFrom(
                    foregroundColor: const Color(0xFFEF4444),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    minimumSize: const Size(0, 30),
                  ),
                  child: const Text('Từ chối', style: TextStyle(fontSize: 12)),
                ),
              if (isWaitingApproval && onApprove != null) ...[
                const SizedBox(width: 6),
                ElevatedButton.icon(
                  onPressed: onApprove,
                  icon: const Icon(Icons.check, size: 14),
                  label: const Text('Phê duyệt', style: TextStyle(fontSize: 12)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: const Color(0xFF04070E),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    minimumSize: const Size(0, 30),
                  ),
                ),
              ],
              if ((isInProgress || isBlocked) && onTogglePause != null)
                ElevatedButton.icon(
                  onPressed: onTogglePause,
                  icon: Icon(isBlocked ? Icons.play_arrow : Icons.pause, size: 14),
                  label: Text(isBlocked ? 'Tiếp tục' : 'Tạm dừng', style: const TextStyle(fontSize: 12)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: isBlocked ? const Color(0xFF10B981) : const Color(0xFF1E293B),
                    foregroundColor: isBlocked ? const Color(0xFF04070E) : const Color(0xFFEF4444),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    minimumSize: const Size(0, 30),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
