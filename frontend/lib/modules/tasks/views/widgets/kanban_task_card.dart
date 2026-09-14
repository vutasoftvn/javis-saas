import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/runtime/mutation_gate.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../controllers/tasks_controller.dart';

class KanbanTaskCard extends StatelessWidget {
  final TaskKanbanModel task;
  final TasksController controller;

  const KanbanTaskCard({
    super.key,
    required this.task,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            task.title,
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w500, color: Colors.white),
          ),
          if (task.projectId != null ||
              task.weeklyCommitmentId != null ||
              task.weeklyPlanId != null ||
              task.keyResultId != null) ...[
            const SizedBox(height: 6),
            Wrap(
              spacing: 4,
              children: [
                if (task.projectId != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      'P: ${task.projectId}',
                      style: const TextStyle(fontSize: 9.5, color: Color(0xFF38BDF8)),
                    ),
                  ),
                if (task.weeklyCommitmentId != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      'Commitment: ${task.weeklyCommitmentId}',
                      style: const TextStyle(fontSize: 9.5, color: Color(0xFF10B981)),
                    ),
                  ),
                // Task 4 (workspace/project/OKR/weekly foundation) — badge nhỏ
                // hiển thị liên kết Week/KR đã denormalize từ backend (Task 3),
                // chỉ đọc lại, không có action.
                if (task.weeklyPlanId != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFA78BFA).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      'Week: ${task.weeklyPlanId}',
                      style: const TextStyle(fontSize: 9.5, color: Color(0xFFA78BFA)),
                    ),
                  ),
                if (task.keyResultId != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF472B6).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      'KR: ${task.keyResultId}',
                      style: const TextStyle(fontSize: 9.5, color: Color(0xFFF472B6)),
                    ),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Priority & Due date
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                      color: _getPriorityColor(task.priority).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _getPriorityLabel(task.priority),
                      style: TextStyle(
                        fontSize: 10,
                        color: _getPriorityColor(task.priority),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  if (task.dueDate != null) ...[
                    const SizedBox(width: 6),
                    const Icon(Icons.calendar_today, size: 11, color: AppTheme.textMutedDark),
                    const SizedBox(width: 3),
                    Text(
                      _formatDate(task.dueDate!),
                      style: const TextStyle(fontSize: 10, color: AppTheme.textMutedDark),
                    ),
                  ],
                ],
              ),

              // Action Buttons (Pause, Resume, Approve)
              // Task 5 — bọc Obx để tự disable + đổi tooltip ngay khi runtime
              // đổi (offline/read-only), thay vì để người dùng bấm rồi mới
              // thấy lỗi.
              Obx(() {
                final permission = controller.mutationPermission();
                final blocked = permission.isHardBlocked;

                Future<void> runGated(
                  Future<void> Function({required bool confirmed}) action,
                  String actionLabel,
                ) async {
                  if (blocked) return;
                  if (permission == MutationPermission.confirmDegraded) {
                    final ok = await confirmDegradedMutation(context, actionLabel: actionLabel);
                    if (!ok) return;
                    await action(confirmed: true);
                    return;
                  }
                  await action(confirmed: false);
                }

                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (task.status == TaskKanbanStatus.inProgress)
                      Tooltip(
                        message: blocked ? permission.blockedTooltip : 'Tạm dừng (Pause)',
                        child: InkWell(
                          onTap: blocked
                              ? null
                              : () => runGated(
                                    ({required confirmed}) =>
                                        controller.pauseTask(task.id, confirmed: confirmed),
                                    'tạm dừng công việc',
                                  ),
                          borderRadius: BorderRadius.circular(6),
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: const Color(0xFFEF4444).withValues(alpha: blocked ? 0.05 : 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Icon(Icons.pause, size: 14, color: Color(0xFFEF4444)),
                          ),
                        ),
                      ),
                    if (task.status == TaskKanbanStatus.blocked)
                      Tooltip(
                        message: blocked ? permission.blockedTooltip : 'Tiếp tục (Resume)',
                        child: InkWell(
                          onTap: blocked
                              ? null
                              : () => runGated(
                                    ({required confirmed}) =>
                                        controller.resumeTask(task.id, confirmed: confirmed),
                                    'tiếp tục công việc',
                                  ),
                          borderRadius: BorderRadius.circular(6),
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: const Color(0xFF10B981).withValues(alpha: blocked ? 0.05 : 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Icon(Icons.play_arrow, size: 14, color: Color(0xFF10B981)),
                          ),
                        ),
                      ),
                    if (task.status == TaskKanbanStatus.waitingApproval)
                      Tooltip(
                        message: blocked ? permission.blockedTooltip : 'Phê duyệt nhanh (Approve)',
                        child: InkWell(
                          onTap: blocked
                              ? null
                              : () => runGated(
                                    ({required confirmed}) =>
                                        controller.approveTask(task.id, confirmed: confirmed),
                                    'phê duyệt nhanh công việc',
                                  ),
                          borderRadius: BorderRadius.circular(6),
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF59E0B).withValues(alpha: blocked ? 0.05 : 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Icon(Icons.check, size: 14, color: Color(0xFFF59E0B)),
                          ),
                        ),
                      ),
                    const SizedBox(width: 6),
                    const CircleAvatar(
                      radius: 9,
                      backgroundColor: AppTheme.backgroundDark,
                      child: Icon(Icons.person, size: 11, color: AppTheme.textMutedDark),
                    ),
                  ],
                );
              }),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDate(String isoString) {
    try {
      final date = DateTime.parse(isoString);
      return '${date.day}/${date.month}';
    } catch (_) {
      return '';
    }
  }

  Color _getPriorityColor(String? priority) {
    switch (priority?.toLowerCase()) {
      case 'high':
      case 'urgent':
        return Colors.redAccent;
      case 'medium':
        return Colors.orangeAccent;
      case 'low':
      default:
        return Colors.blueAccent;
    }
  }

  String _getPriorityLabel(String? priority) {
    final isEn = Get.locale?.languageCode == 'en';
    switch (priority?.toLowerCase()) {
      case 'urgent':
        return isEn ? 'Urgent' : 'Khẩn cấp';
      case 'high':
        return isEn ? 'High' : 'Cao';
      case 'medium':
        return isEn ? 'Medium' : 'Trung bình';
      case 'low':
        return isEn ? 'Low' : 'Thấp';
      default:
        return isEn ? 'Normal' : 'Bình thường';
    }
  }
}
