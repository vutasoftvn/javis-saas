import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

/// Task 4 (2026-09-14 remediation) — walk đúng wrapper
/// `{objective, keyResults: [{keyResult, initiatives}]}` thay vì
/// `LoopObjective.keyResults`/`LoopKeyResult.initiatives` lồng trực tiếp
/// (hình dạng cũ không khớp backend thật).
class OkrSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final List<LoopObjectiveTree> objectives;

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
                final objectiveTree = objectives[index];
                final obj = objectiveTree.objective;
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ExpansionTile(
                    key: Key('objective_${obj.id}'),
                    title: Text(obj.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('Status: ${obj.status.toUpperCase()}'),
                    trailing: IconButton(
                      icon: const Icon(Icons.add, size: 20),
                      tooltip: 'Add Key Result',
                      onPressed: () => _showAddKeyResultDialog(context, obj.id),
                    ),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(12.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (objectiveTree.keyResults.isEmpty)
                              const Text('No key results linked yet.')
                            else
                              ...objectiveTree.keyResults.map(
                                (krTree) => _KeyResultTile(
                                  krTree: krTree,
                                  onAddInitiative: () => _showAddInitiativeDialog(
                                    context,
                                    krTree.keyResult.id,
                                  ),
                                ),
                              ),
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

  void _showAddKeyResultDialog(BuildContext context, String objectiveId) {
    final titleController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New Key Result'),
        content: TextField(
          controller: titleController,
          decoration: const InputDecoration(
            labelText: 'Key Result Title',
            hintText: 'e.g. 10 paying customers',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            key: const Key('create_key_result_button'),
            onPressed: () {
              if (titleController.text.trim().isNotEmpty) {
                controller.createKeyResult(objectiveId, titleController.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _showAddInitiativeDialog(BuildContext context, String keyResultId) {
    final titleController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New Initiative'),
        content: TextField(
          controller: titleController,
          decoration: const InputDecoration(
            labelText: 'Initiative Title',
            hintText: 'e.g. Customer discovery interviews',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            key: const Key('create_initiative_button'),
            onPressed: () {
              if (titleController.text.trim().isNotEmpty) {
                controller.createInitiative(keyResultId, titleController.text.trim());
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

class _KeyResultTile extends StatelessWidget {
  const _KeyResultTile({required this.krTree, required this.onAddInitiative});

  final LoopKeyResultTree krTree;
  final VoidCallback onAddInitiative;

  @override
  Widget build(BuildContext context) {
    final kr = krTree.keyResult;
    return Padding(
      key: Key('key_result_${kr.id}'),
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle_outline, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${kr.title ?? ''} (${kr.currentValue ?? 0} / ${kr.targetValue ?? 0} ${kr.unit ?? ''})',
                ),
              ),
              IconButton(
                icon: const Icon(Icons.add, size: 16),
                tooltip: 'Add Initiative',
                onPressed: onAddInitiative,
              ),
            ],
          ),
          if (krTree.initiatives.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: krTree.initiatives
                    .map(
                      (initiative) => Text(
                        key: Key('initiative_${initiative.id}'),
                        '• ${initiative.title} (${initiative.status})',
                      ),
                    )
                    .toList(),
              ),
            ),
        ],
      ),
    );
  }
}
