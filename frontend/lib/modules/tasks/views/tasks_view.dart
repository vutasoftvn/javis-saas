import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/tasks_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import 'tabs/task_kanban_tab.dart';
import 'tabs/work_overview_tab.dart';
import 'widgets/add_task_dialog.dart';

class TasksView extends GetView<TasksController> {
  const TasksView({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Container(
        color: Colors.transparent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            CosaFloatingAppBar(
              title: 'Công việc & Vận hành',
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
            const TabBar(
              isScrollable: true,
              labelColor: AppTheme.primary,
              unselectedLabelColor: AppTheme.textMutedDark,
              indicatorColor: AppTheme.primary,
              tabs: [
                Tab(text: 'Tổng quan'),
                Tab(text: 'Kanban'),
              ],
            ),
            const SizedBox(height: 12),
            const Expanded(
              child: TabBarView(
                children: [
                  WorkOverviewTab(),
                  TaskKanbanTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
