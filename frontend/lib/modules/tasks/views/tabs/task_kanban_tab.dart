import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/tasks_controller.dart';
import '../widgets/kanban_column_widget.dart';

class TaskKanbanTab extends GetView<TasksController> {
  const TaskKanbanTab({super.key});

  static const List<Map<String, dynamic>> columns = [
    {'title': 'Cần làm', 'status': 'todo', 'color': Color(0xFF38BDF8)},
    {'title': 'Đang làm', 'status': 'in_progress', 'color': Color(0xFF00F0FF)},
    {'title': 'Chờ duyệt', 'status': 'waiting_approval', 'color': Color(0xFFF59E0B)},
    {'title': 'Tạm dừng / Nghẽn', 'status': 'blocked', 'color': Color(0xFFEF4444)},
    {'title': 'Hoàn thành', 'status': 'done', 'color': Color(0xFF10B981)},
  ];

  @override
  Widget build(BuildContext context) {
    return Obx(() {
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
    });
  }
}
