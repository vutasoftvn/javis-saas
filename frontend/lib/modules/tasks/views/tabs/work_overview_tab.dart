import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../../hologram_hub/controllers/founder_command_center_controller.dart';
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
          _buildProjectAdminInfo(),
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

  /// Dropdown chọn project (nguồn `FounderCommandCenterController.projectsList`)
  /// + khối hiển thị `ProjectOperatingSetup` (giai đoạn, trạng thái setup) của
  /// project đang chọn.
  Widget _buildProjectAdminInfo() {
    final fcc = Get.find<FounderCommandCenterController>();
    return Obx(() {
      final projects = fcc.projectsList;
      if (projects.isEmpty) return const SizedBox.shrink();

      final selectedId =
          controller.selectedProjectId.value ?? projects.first['id']?.toString();
      if (controller.selectedProjectId.value == null && selectedId != null) {
        WidgetsBinding.instance
            .addPostFrameCallback((_) => controller.selectProject(selectedId));
      }

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
            Row(
              children: [
                const Text(
                  'Thông tin quản trị project',
                  style: TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                DropdownButton<String>(
                  value: selectedId,
                  dropdownColor: AppTheme.surfaceDark,
                  items: projects.map((p) {
                    final id = p['id']?.toString() ?? '';
                    final title = p['title']?.toString() ?? id;
                    return DropdownMenuItem(
                      value: id,
                      child: Text(
                        title,
                        style: const TextStyle(color: AppTheme.textDark),
                      ),
                    );
                  }).toList(),
                  onChanged: (id) {
                    if (id != null) controller.selectProject(id);
                  },
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (controller.isProjectInfoLoading.value)
              const Center(child: CircularProgressIndicator())
            else if (controller.projectInfoError.value != null)
              Text(
                'Không tải được thông tin project: ${controller.projectInfoError.value}',
                style: const TextStyle(color: AppTheme.error, fontSize: 13),
              )
            else if (controller.projectSetup.value != null) ...[
              _infoRow(
                'Giai đoạn',
                controller.projectSetup.value!.selectedStage?.name ?? 'Chưa chọn',
              ),
              _infoRow('Trạng thái setup', controller.projectSetup.value!.status.name),
            ],
          ],
        ),
      );
    });
  }

  Widget _infoRow(String label, String value) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          children: [
            SizedBox(
              width: 140,
              child: Text(
                label,
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ),
            Expanded(
              child: Text(
                value,
                style: const TextStyle(color: AppTheme.textDark, fontSize: 13),
              ),
            ),
          ],
        ),
      );

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
