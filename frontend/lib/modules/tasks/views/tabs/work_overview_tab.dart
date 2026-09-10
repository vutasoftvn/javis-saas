import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../controllers/work_overview_controller.dart';

class WorkOverviewTab extends StatefulWidget {
  const WorkOverviewTab({super.key});

  @override
  State<WorkOverviewTab> createState() => _WorkOverviewTabState();
}

class _WorkOverviewTabState extends State<WorkOverviewTab> {
  final WorkOverviewController controller = Get.find<WorkOverviewController>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      controller.loadOkrSummary();
    });
  }

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
          _buildOkrSummary(),
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

  /// Khối rút gọn "OKR chu kỳ hiện tại" (tỉ lệ hoàn thành key result).
  Widget _buildOkrSummary() {
    return Obx(() {
      final isLoading = controller.isOkrSummaryLoading.value;
      final error = controller.okrSummaryError.value;
      final okr = controller.okrCompletionRatio.value;
      final isEn = Get.locale?.languageCode == 'en';
      if (isLoading) {
        return const Center(child: CircularProgressIndicator());
      }
      if (error != null) {
        return Text(
          isEn ? 'Failed to load OKR summary: $error' : 'Không tải được OKR: $error',
          style: const TextStyle(color: AppTheme.error, fontSize: 13),
        );
      }
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(isEn ? 'Current Cycle OKRs' : 'OKR chu kỳ hiện tại',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
            const SizedBox(height: 6),
            Text(
              okr != null ? '${(okr * 100).round()}%' : '—',
              style: const TextStyle(color: AppTheme.primary, fontSize: 22, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildTodayTasks() {
    final isEn = Get.locale?.languageCode == 'en';
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
          Text(
            isEn ? "Today's Tasks" : 'Việc hôm nay',
            style: const TextStyle(color: AppTheme.textDark, fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Obx(() {
            final tasks = controller.todayTasks;
            if (tasks.isEmpty) {
              return Text(
                isEn ? 'No tasks due today.' : 'Không có việc nào đến hạn hôm nay.',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
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
                          child: Text(isEn ? 'View in Kanban' : 'Xem ở Kanban'),
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
