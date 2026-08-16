import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/tasks_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/floating_app_bar.dart';

class TasksView extends GetView<TasksController> {
  const TasksView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<TasksController>()) {
      Get.put(TasksController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Floating AppBar Card
          JavisFloatingAppBar(
            title: 'Bảng công việc Kanban (Harness Vòng đời 6 Bước)',
            subtitle: 'Quản lý tiến độ nhiệm vụ, phê duyệt và điều phối tự động',
            actions: [
              Container(
                decoration: const BoxDecoration(
                  color: AppTheme.primary,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  tooltip: 'Thêm công việc',
                  icon: const Icon(Icons.add, color: Colors.white, size: 20),
                  onPressed: () => _showAddTaskDialog(context, 'todo'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // 2. Kanban Board (5 main operational columns)
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              final columns = [
                {'title': 'Cần làm', 'status': 'todo', 'color': const Color(0xFF38BDF8)},
                {'title': 'Đang làm', 'status': 'in_progress', 'color': const Color(0xFF00F0FF)},
                {'title': 'Chờ duyệt', 'status': 'waiting_approval', 'color': const Color(0xFFF59E0B)},
                {'title': 'Tạm dừng / Nghẽn', 'status': 'blocked', 'color': const Color(0xFFEF4444)},
                {'title': 'Hoàn thành', 'status': 'done', 'color': const Color(0xFF10B981)},
              ];

              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth >= 1400;
                    if (isWide) {
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          for (int i = 0; i < columns.length; i++) ...[
                            if (i > 0) const SizedBox(width: 12),
                            Expanded(
                              child: _buildColumn(
                                context,
                                columns[i]['title'] as String,
                                columns[i]['status'] as String,
                                columns[i]['color'] as Color,
                              ),
                            ),
                          ],
                        ],
                      );
                    }

                    // Horizontal scrolling Kanban board for standard screens
                    return ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: columns.length,
                      separatorBuilder: (_, _) => const SizedBox(width: 14),
                      itemBuilder: (context, index) {
                        return SizedBox(
                          width: 290,
                          child: _buildColumn(
                            context,
                            columns[index]['title'] as String,
                            columns[index]['status'] as String,
                            columns[index]['color'] as Color,
                          ),
                        );
                      },
                    );
                  },
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildColumn(BuildContext context, String title, String status, Color columnColor) {
    return Glassmorphism(
      blur: 20,
      opacity: 0.15,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border(
            top: BorderSide(
              color: columnColor,
              width: 4,
            ),
          ),
        ),
        child: DragTarget<Map<String, dynamic>>(
          onWillAcceptWithDetails: (details) {
            return details.data['status'] != status;
          },
          onAcceptWithDetails: (details) {
            controller.moveTask(details.data['id'], status);
          },
          builder: (context, candidateData, rejectedData) {
            final columnTasks = controller.tasks.where((t) => t['status'] == status).toList();

            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Column Header
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: columnColor,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            title,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 14.5,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.backgroundDark,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: columnColor.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          '${columnTasks.length}',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: columnColor,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Tasks List
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    itemCount: columnTasks.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final task = columnTasks[index];
                      return Draggable<Map<String, dynamic>>(
                        data: task,
                        feedback: Material(
                          color: Colors.transparent,
                          child: SizedBox(
                            width: 270,
                            child: _buildTaskCard(task),
                          ),
                        ),
                        childWhenDragging: Opacity(
                          opacity: 0.4,
                          child: _buildTaskCard(task),
                        ),
                        child: _buildTaskCard(task),
                      );
                    },
                  ),
                ),

                // Quick Add
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: TextButton.icon(
                    onPressed: () => _showAddTaskDialog(context, status),
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Thêm công việc', style: TextStyle(fontSize: 13)),
                    style: TextButton.styleFrom(
                      foregroundColor: AppTheme.textMutedDark,
                      alignment: Alignment.centerLeft,
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildTaskCard(Map<String, dynamic> task) {
    final status = task['status'] as String? ?? 'todo';
    final taskId = task['id']?.toString() ?? '';

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
            task['title'] ?? '',
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w500, color: Colors.white),
          ),
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
                      color: _getPriorityColor(task['priority']).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _getPriorityLabel(task['priority']),
                      style: TextStyle(fontSize: 10, color: _getPriorityColor(task['priority']), fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (task['due_at'] != null) ...[
                    const SizedBox(width: 6),
                    const Icon(Icons.calendar_today, size: 11, color: AppTheme.textMutedDark),
                    const SizedBox(width: 3),
                    Text(
                      _formatDate(task['due_at']),
                      style: const TextStyle(fontSize: 10, color: AppTheme.textMutedDark),
                    ),
                  ]
                ],
              ),

              // Action Buttons (Pause, Resume, Approve)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (status == 'in_progress')
                    Tooltip(
                      message: 'Tạm dừng (Pause)',
                      child: InkWell(
                        onTap: () => controller.pauseTask(taskId),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(Icons.pause, size: 14, color: Color(0xFFEF4444)),
                        ),
                      ),
                    ),
                  if (status == 'blocked')
                    Tooltip(
                      message: 'Tiếp tục (Resume)',
                      child: InkWell(
                        onTap: () => controller.resumeTask(taskId),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: const Color(0xFF10B981).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(Icons.play_arrow, size: 14, color: Color(0xFF10B981)),
                        ),
                      ),
                    ),
                  if (status == 'waiting_approval')
                    Tooltip(
                      message: 'Phê duyệt nhanh (Approve)',
                      child: InkWell(
                        onTap: () => controller.approveTask(taskId),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
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
              ),
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
    switch (priority) {
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
    switch (priority) {
      case 'urgent': return 'Khẩn cấp';
      case 'high': return 'Cao';
      case 'medium': return 'Trung bình';
      case 'low': return 'Thấp';
      default: return 'Bình thường';
    }
  }

  void _showAddTaskDialog(BuildContext context, String initialStatus) {
    final textController = TextEditingController();
    Get.dialog(
      AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Công việc mới'),
        content: TextField(
          controller: textController,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'Cần làm những gì?',
          ),
          onSubmitted: (val) {
            controller.addTask(val, initialStatus);
            Get.back();
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            onPressed: () {
              controller.addTask(textController.text, initialStatus);
              Get.back();
            },
            child: const Text('Thêm'),
          ),
        ],
      ),
    );
  }
}

