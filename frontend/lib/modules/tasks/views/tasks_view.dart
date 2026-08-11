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
          // 1. Floating AppBar Card (Title without icon, action button rounded icon only)
          JavisFloatingAppBar(
            title: 'Bảng công việc Kanban',
            subtitle: 'Quản lý tiến độ nhiệm vụ và phân công tự động',
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
          
          // 2. Kanban Board (3 columns filling and evenly dividing the content container)
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(child: _buildColumn(context, 'Cần làm', 'todo')),
                    const SizedBox(width: 16),
                    Expanded(child: _buildColumn(context, 'Đang làm', 'in_progress')),
                    const SizedBox(width: 16),
                    Expanded(child: _buildColumn(context, 'Hoàn thành', 'done')),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildColumn(BuildContext context, String title, String status) {
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
              color: status == 'todo'
                  ? AppTheme.primary
                  : (status == 'in_progress' ? AppTheme.warning : AppTheme.success),
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
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.backgroundDark,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${columnTasks.length}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                        ),
                      ),
                    ],
                  ),
                ),
                
                // Tasks List
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: columnTasks.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final task = columnTasks[index];
                      return Draggable<Map<String, dynamic>>(
                        data: task,
                        feedback: Material(
                          color: Colors.transparent,
                          child: SizedBox(
                            width: 280,
                            child: _buildTaskCard(task),
                          ),
                        ),
                        childWhenDragging: Opacity(
                          opacity: 0.5,
                          child: _buildTaskCard(task),
                        ),
                        child: _buildTaskCard(task),
                      );
                    },
                  ),
                ),
                
                // Quick Add
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: TextButton.icon(
                    onPressed: () => _showAddTaskDialog(context, status),
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Thêm công việc'),
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
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
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
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.white),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: _getPriorityColor(task['priority']).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _getPriorityLabel(task['priority']),
                      style: TextStyle(fontSize: 10, color: _getPriorityColor(task['priority'])),
                    ),
                  ),
                  if (task['due_at'] != null) ...[
                    const SizedBox(width: 8),
                    const Icon(Icons.calendar_today, size: 12, color: AppTheme.textMutedDark),
                    const SizedBox(width: 4),
                    Text(
                      _formatDate(task['due_at']),
                      style: const TextStyle(fontSize: 10, color: AppTheme.textMutedDark),
                    ),
                  ]
                ],
              ),
              const CircleAvatar(
                radius: 10,
                backgroundColor: AppTheme.backgroundDark,
                child: Icon(Icons.person, size: 12, color: AppTheme.textMutedDark),
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
