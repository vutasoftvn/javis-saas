import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

class CommitmentTaskSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final LoopActiveCycle? activeCycle;
  final List<LoopTask> tasks;

  const CommitmentTaskSection({
    super.key,
    required this.controller,
    this.activeCycle,
    this.tasks = const [],
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final plans = activeCycle?.weeklyPlans ?? [];

    // Collect all commitments across plans
    final allCommitments = <({LoopCommitment commitment, int weekNo, String planId})>[];
    for (final plan in plans) {
      for (final c in plan.commitments) {
        allCommitments.add((commitment: c, weekNo: plan.weekNo, planId: plan.id));
      }
    }

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
              if (plans.isNotEmpty)
                ElevatedButton.icon(
                  key: const Key('add_commitment_button'),
                  icon: const Icon(Icons.add_task, size: 18),
                  label: const Text('Add Commitment'),
                  onPressed: () => _showAddCommitmentDialog(context, plans),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (allCommitments.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Center(
                  child: Text(
                    plans.isEmpty
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
              itemCount: allCommitments.length,
              itemBuilder: (context, index) {
                final item = allCommitments[index];
                final commitment = item.commitment;
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ExpansionTile(
                    key: Key('commitment_${commitment.id}'),
                    initiallyExpanded: true,
                    title: Text(
                      'Week ${item.weekNo}: ${commitment.title}',
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
                            if (commitment.tasks.isEmpty)
                              Padding(
                                padding: const EdgeInsets.all(8.0),
                                child: Text(
                                  'No tasks attached to this commitment yet.',
                                  style: theme.textTheme.bodySmall?.copyWith(color: theme.hintColor),
                                ),
                              )
                            else
                              ...commitment.tasks.map((task) => Container(
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
                                          task.status == 'done'
                                              ? Icons.check_box
                                              : Icons.check_box_outline_blank,
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
                                                'Status: ${task.status.toUpperCase()} · Priority: ${task.priority.toUpperCase()}',
                                                style: theme.textTheme.bodySmall,
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
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

  void _showAddCommitmentDialog(BuildContext context, List<LoopWeeklyPlan> plans) {
    String selectedPlanId = plans.first.id;
    final titleController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Add Weekly Commitment'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButton<String>(
                value: selectedPlanId,
                isExpanded: true,
                items: plans
                    .map((p) => DropdownMenuItem(
                          value: p.id,
                          child: Text('Week ${p.weekNo}${p.focus != null ? ' (${p.focus})' : ''}'),
                        ))
                    .toList(),
                onChanged: (val) {
                  if (val != null) setState(() => selectedPlanId = val);
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Commitment Title',
                  hintText: 'e.g. Ship v1 onboarding flow',
                ),
                autofocus: true,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                if (titleController.text.trim().isNotEmpty) {
                  controller.createCommitment(selectedPlanId, titleController.text.trim());
                  Navigator.of(ctx).pop();
                }
              },
              child: const Text('Create'),
            ),
          ],
        ),
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
