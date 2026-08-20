import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/tasks_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import 'widgets/kanban_column_widget.dart';
import 'widgets/add_task_dialog.dart';

class TasksView extends GetView<TasksController> {
  const TasksView({super.key});

  static const List<Map<String, dynamic>> columns = [
    {'title': 'Cần làm', 'status': 'todo', 'color': Color(0xFF38BDF8)},
    {'title': 'Đang làm', 'status': 'in_progress', 'color': Color(0xFF00F0FF)},
    {'title': 'Chờ duyệt', 'status': 'waiting_approval', 'color': Color(0xFFF59E0B)},
    {'title': 'Tạm dừng / Nghẽn', 'status': 'blocked', 'color': Color(0xFFEF4444)},
    {'title': 'Hoàn thành', 'status': 'done', 'color': Color(0xFF10B981)},
  ];

  @override
  Widget build(BuildContext context) {
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
                  onPressed: () => AddTaskDialog.show(context, controller, 'todo'),
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
                              child: KanbanColumnWidget(
                                title: columns[i]['title'] as String,
                                status: columns[i]['status'] as String,
                                columnColor: columns[i]['color'] as Color,
                                controller: controller,
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
                          child: KanbanColumnWidget(
                            title: columns[index]['title'] as String,
                            status: columns[index]['status'] as String,
                            columnColor: columns[index]['color'] as Color,
                            controller: controller,
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
}
