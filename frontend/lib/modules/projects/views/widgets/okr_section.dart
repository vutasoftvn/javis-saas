import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

class OkrSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final List<LoopObjective> objectives;

  const OkrSection({
    super.key,
    required this.controller,
    required this.objectives,
  });

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
                  'Objectives & Key Results',
                  style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                key: const Key('add_objective_button'),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Add Objective'),
                onPressed: () => _showAddObjectiveDialog(context),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (objectives.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Center(
                  child: Text(
                    'No objectives created for this project yet.',
                    style: theme.textTheme.bodyMedium?.copyWith(color: theme.hintColor),
                  ),
                ),
              ),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: objectives.length,
              itemBuilder: (context, index) {
                final obj = objectives[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ExpansionTile(
                    key: Key('objective_${obj.id}'),
                    title: Text(obj.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('Status: ${obj.status.toUpperCase()}'),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(12.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (obj.keyResults.isEmpty)
                              const Text('No key results linked yet.')
                            else
                              ...obj.keyResults.map((kr) => Padding(
                                    padding: const EdgeInsets.only(bottom: 8.0),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.check_circle_outline, size: 16),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            '${kr.title} (${kr.currentValue ?? 0} / ${kr.targetValue ?? 0} ${kr.metricUnit ?? ''})',
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

  void _showAddObjectiveDialog(BuildContext context) {
    final titleController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New Objective'),
        content: TextField(
          controller: titleController,
          decoration: const InputDecoration(
            labelText: 'Objective Title',
            hintText: 'Enter strategic objective...',
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
                controller.createObjective(titleController.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }
}
