import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/module_routes.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../../hologram_hub/controllers/founder_command_center_controller.dart';
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
      controller.loadOkrAndTwelveWySummary();
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
          _buildOkrTwelveWySummary(),
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

  /// Khối rút gọn "OKR chu kỳ hiện tại" + "Điểm thực thi tuần (12WY)", bấm
  /// vào điều hướng sang tab Chiến lược (`WorkspaceModule.strategy.path`).
  Widget _buildOkrTwelveWySummary() {
    return Obx(() {
      final okr = controller.okrCompletionRatio.value;
      final wy = controller.twelveWyExecutionScore.value;
      return Row(
        children: [
          Expanded(
            child: InkWell(
              onTap: () => Get.toNamed(WorkspaceModule.strategy.path),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.borderDark),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('OKR chu kỳ hiện tại', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                    const SizedBox(height: 6),
                    Text(
                      okr != null ? '${(okr * 100).round()}%' : '—',
                      style: const TextStyle(color: AppTheme.primary, fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: InkWell(
              onTap: () => Get.toNamed(WorkspaceModule.strategy.path),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.borderDark),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Điểm thực thi tuần (12WY)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                    const SizedBox(height: 6),
                    Text(
                      wy != null ? '${(wy * 100).round()}%' : '—',
                      style: const TextStyle(color: AppTheme.primary, fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
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

      // Guard: `selectedProjectId` có thể trỏ tới 1 project không còn nằm
      // trong `projectsList` hiện tại (vd `projectsList` bị `assignAll` lại
      // ở nơi khác trong lúc đang chọn project đó) — `DropdownButton.value`
      // bắt buộc phải khớp 1 `item.value` trong `items`, nếu không sẽ
      // assert/throw. Khi lệch, coi như chưa chọn gì và rơi về project đầu.
      final projectIds = projects.map((p) => p['id']?.toString()).toSet();
      final currentSelection = controller.selectedProjectId.value;
      final selectedId = (currentSelection != null && projectIds.contains(currentSelection))
          ? currentSelection
          : projects.first['id']?.toString();

      // Chỉ gọi lại selectProject khi thật sự cần (chưa chọn gì, hoặc lựa
      // chọn hiện tại đã lệch khỏi danh sách) — tránh gọi lại API mỗi lần
      // Obx rebuild dù project đang chọn vẫn hợp lệ.
      if (selectedId != null && selectedId != currentSelection) {
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
