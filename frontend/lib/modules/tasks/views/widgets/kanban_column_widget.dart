import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/glassmorphism.dart';
import '../../../../data/models/task_kanban_model.dart';
import '../../controllers/tasks_controller.dart';
import 'kanban_task_card.dart';
import 'add_task_dialog.dart';

class KanbanColumnWidget extends StatelessWidget {
  final String title;
  final String status;
  final Color columnColor;
  final TasksController controller;

  const KanbanColumnWidget({
    super.key,
    required this.title,
    required this.status,
    required this.columnColor,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
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
        child: DragTarget<TaskKanbanModel>(
          onWillAcceptWithDetails: (details) {
            return details.data.status.value != status;
          },
          onAcceptWithDetails: (details) {
            controller.moveTask(details.data.id, status);
          },
          builder: (context, candidateData, rejectedData) {
            return Obx(() {
              final targetStatus = TaskKanbanStatus.fromString(status);
              final columnTasks = controller.tasks.where((t) => t.status == targetStatus).toList();

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
                        return Draggable<TaskKanbanModel>(
                          data: task,
                          feedback: Material(
                            color: Colors.transparent,
                            child: SizedBox(
                              width: 270,
                              child: KanbanTaskCard(task: task, controller: controller),
                            ),
                          ),
                          childWhenDragging: Opacity(
                            opacity: 0.4,
                            child: KanbanTaskCard(task: task, controller: controller),
                          ),
                          child: KanbanTaskCard(task: task, controller: controller),
                        );
                      },
                    ),
                  ),

                  // Quick Add Button
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: TextButton.icon(
                      onPressed: () => AddTaskDialog.show(context, controller, status),
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
            });
          },
        ),
      ),
    );
  }
}
