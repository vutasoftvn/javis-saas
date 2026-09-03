import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../controllers/work_overview_controller.dart';

class WorkOverviewTab extends GetView<WorkOverviewController> {
  const WorkOverviewTab({super.key});

  static const _statusColors = {
    TaskKanbanStatus.todo: Color(0xFF38BDF8),
    TaskKanbanStatus.inProgress: Color(0xFF00F0FF),
    TaskKanbanStatus.waitingApproval: Color(0xFFF59E0B),
    TaskKanbanStatus.blocked: Color(0xFFEF4444),
    TaskKanbanStatus.done: Color(0xFF10B981),
    TaskKanbanStatus.cancelled: AppTheme.textMutedDark,
  };

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildStatusCounts(),
          const SizedBox(height: 20),
          _buildTodayTasks(),
        ],
      ),
    );
  }

  Widget _buildStatusCounts() {
    return Obx(() {
      final counts = controller.statusCounts;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: TaskKanbanStatus.values
            .where((s) => s != TaskKanbanStatus.cancelled)
            .map((status) {
          return Container(
            width: 150,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _statusColors[status]!.withValues(alpha: 0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${counts[status] ?? 0}',
                  style: TextStyle(
                    color: _statusColors[status],
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  status.title,
                  style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                ),
              ],
            ),
          );
        }).toList(),
      );
    });
  }

  Widget _buildTodayTasks() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Việc hôm nay',
            style: TextStyle(color: AppTheme.textDark, fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Obx(() {
            final tasks = controller.todayTasks;
            if (tasks.isEmpty) {
              return const Text(
                'Không có việc nào đến hạn hôm nay.',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              );
            }
            return Column(
              children: tasks.map((task) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Builder(
                    builder: (context) => Row(
                      children: [
                        Icon(Icons.circle, size: 8, color: _statusColors[task.status]),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            task.title,
                            style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                          ),
                        ),
                        TextButton(
                          onPressed: () => DefaultTabController.of(context).animateTo(1),
                          child: const Text('Xem ở Kanban'),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            );
          }),
        ],
      ),
    );
  }
}
