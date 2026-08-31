import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/chat_controller.dart';
import '../../models/chat_models.dart';

class ChatActivityCards extends StatelessWidget {
  final ChatController controller;

  const ChatActivityCards({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final reasoning = controller.reasoningStatus.value;
      final activities = controller.toolActivities;
      final approvals = controller.pendingApprovals;

      if (reasoning.isEmpty && activities.isEmpty && approvals.isEmpty) {
        return const SizedBox.shrink();
      }

      return Container(
        margin: const EdgeInsets.only(bottom: 16),
        constraints: const BoxConstraints(maxWidth: 720),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (reasoning.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDarkLighter,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(strokeWidth: 1.5, color: AppTheme.secondary),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      reasoning,
                      style: const TextStyle(color: AppTheme.secondaryLight, fontSize: 12),
                    ),
                  ],
                ),
              ),

            // Tool Activity Cards
            ...activities.map((act) => _buildToolActivityCard(act)),

            // Approval Cards
            ...approvals.map((appr) => _buildApprovalCard(appr)),
          ],
        ),
      );
    });
  }

  Widget _buildToolActivityCard(ChatToolActivity act) {
    Color statusColor = act.status == 'completed'
        ? AppTheme.success
        : (act.status == 'failed' ? AppTheme.error : AppTheme.secondary);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Icon(Icons.build_circle_outlined, size: 16, color: statusColor),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Tool: ${act.toolName}',
              style: const TextStyle(color: AppTheme.textDark, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              act.status.toUpperCase(),
              style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildApprovalCard(ChatApproval appr) {
    final isPending = appr.status == 'PENDING';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.warning.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.gavel, color: AppTheme.warning, size: 18),
              const SizedBox(width: 8),
              const Text(
                'Approval Required',
                style: TextStyle(color: AppTheme.warning, fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: (isPending ? AppTheme.warning : (appr.status == 'APPROVED' ? AppTheme.success : AppTheme.error))
                      .withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  appr.status,
                  style: TextStyle(
                    color: isPending ? AppTheme.warning : (appr.status == 'APPROVED' ? AppTheme.success : AppTheme.error),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Action: ${appr.action}',
            style: const TextStyle(color: AppTheme.textDark, fontSize: 12, fontWeight: FontWeight.w600),
          ),
          if (appr.subject.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Subject: ${appr.subject}',
              style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
            ),
          ],
          if (isPending) ...[
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: () => controller.handleApprovalDecision(appr.id, false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.error,
                    side: const BorderSide(color: AppTheme.error),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  ),
                  child: const Text('Reject'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => controller.handleApprovalDecision(appr.id, true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.success,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  ),
                  child: const Text('Approve'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
