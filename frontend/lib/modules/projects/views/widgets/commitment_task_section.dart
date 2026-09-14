import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

/// Task 4 (2026-09-14 remediation) — `commitments` và `tasks` là 2 mảng GỐC
/// độc lập (không lồng trong cycle/week). Section này tự nhóm task theo
/// `weeklyCommitmentId` để hiển thị, thay vì đọc lồng nhau từ 1 nguồn không
/// tồn tại ở backend.
class CommitmentTaskSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final LoopWeek? currentWeek;
  final List<LoopCommitment> commitments;
  final List<LoopTask> tasks;

  const CommitmentTaskSection({
    super.key,
    required this.controller,
    this.currentWeek,
    this.commitments = const [],
    this.tasks = const [],
  });

  static const _taskStatuses = ['todo', 'in_progress', 'blocked', 'done'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  'Weekly Commitments & Tasks',
                  style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 8),
              if (currentWeek != null)
                ElevatedButton.icon(
                  key: const Key('add_commitment_button'),
                  icon: const Icon(Icons.add_task, size: 18),
                  label: const Text('Add Commitment'),
                  onPressed: () => _showAddCommitmentDialog(context, currentWeek!.id),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (commitments.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Center(
                  child: Text(
                    currentWeek == null
                        ? 'Create an operating cycle and week first before adding commitments.'
                        : 'No weekly commitments added yet. Add a commitment to assign tasks.',
                    style: theme.textTheme.bodyMedium?.copyWith(color: theme.hintColor),
                  ),
                ),
              ),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: commitments.length,
              itemBuilder: (context, index) {
                final commitment = commitments[index];
                final commitmentTasks =
                    tasks.where((t) => t.weeklyCommitmentId == commitment.id).toList();
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ExpansionTile(
                    key: Key('commitment_${commitment.id}'),
                    initiallyExpanded: true,
                    title: Text(
                      commitment.title,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text('Status: ${commitment.status.toUpperCase()}'),
                    trailing: IconButton(
                      icon: const Icon(Icons.add, size: 20),
                      tooltip: 'Add Task to Commitment',
                      onPressed: () => _showAddTaskDialog(context, commitment.id),
                    ),
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (commitmentTasks.isEmpty)
                              Padding(
                                padding: const EdgeInsets.all(8.0),
                                child: Text(
                                  'No tasks attached to this commitment yet.',
                                  style: theme.textTheme.bodySmall?.copyWith(color: theme.hintColor),
                                ),
                              )
                            else
                              ...commitmentTasks.map((task) => _TaskRow(
                                    task: task,
                                    statuses: _taskStatuses,
                                    onStatusChanged: (newStatus) =>
                                        controller.updateTaskStatus(task.id, newStatus),
                                  )),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  void _showAddCommitmentDialog(BuildContext context, String weeklyPlanId) {
    final titleController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Weekly Commitment'),
        content: TextField(
          controller: titleController,
          decoration: const InputDecoration(
            labelText: 'Commitment Title',
            hintText: 'e.g. Ship v1 onboarding flow',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (titleController.text.trim().isNotEmpty) {
                controller.createCommitment(weeklyPlanId, titleController.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _showAddTaskDialog(BuildContext context, String commitmentId) {
    final titleController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Task to Commitment'),
        content: TextField(
          controller: titleController,
          decoration: const InputDecoration(
            labelText: 'Task Title',
            hintText: 'e.g. Write integration test',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (titleController.text.trim().isNotEmpty) {
                controller.createTask(titleController.text.trim(), commitmentId);
                Navigator.of(ctx).pop();
              }
            },
            child: const Text('Add Task'),
          ),
        ],
      ),
    );
  }
}

class _TaskRow extends StatelessWidget {
  const _TaskRow({
    required this.task,
    required this.statuses,
    required this.onStatusChanged,
  });

  final LoopTask task;
  final List<String> statuses;
  final ValueChanged<String> onStatusChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      key: Key('task_${task.id}'),
      margin: const EdgeInsets.only(bottom: 8.0),
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        border: Border.all(color: theme.dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            task.status == 'done' ? Icons.check_box : Icons.check_box_outline_blank,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  task.title,
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                Text(
                  'Priority: ${task.priority.toUpperCase()}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
          DropdownButton<String>(
            key: Key('task_status_${task.id}'),
            value: statuses.contains(task.status) ? task.status : null,
            hint: Text(task.status.toUpperCase()),
            items: statuses
                .map((s) => DropdownMenuItem(value: s, child: Text(s.toUpperCase())))
                .toList(),
            onChanged: (val) {
              if (val != null && val != task.status) {
                onStatusChanged(val);
              }
            },
          ),
        ],
      ),
    );
  }
}
