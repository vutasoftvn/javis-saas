import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

class CycleWeekSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final LoopActiveCycle? activeCycle;

  const CycleWeekSection({
    super.key,
    required this.controller,
    this.activeCycle,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cycle = activeCycle;

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
                  'Operating Cycle & Weekly Plans',
                  style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 8),
              if (cycle == null)
                ElevatedButton.icon(
                  key: const Key('start_cycle_button'),
                  icon: const Icon(Icons.play_arrow, size: 18),
                  label: const Text('Start Cycle'),
                  onPressed: () => _showStartCycleDialog(context),
                )
              else
                ElevatedButton.icon(
                  key: const Key('add_week_button'),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Add Week'),
                  onPressed: () => _showAddWeekDialog(context, cycle.id, cycle.weeklyPlans.length + 1),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (cycle == null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Center(
                  child: Text(
                    'No active operating cycle. Start a 1-12 week cycle to begin weekly execution.',
                    style: theme.textTheme.bodyMedium?.copyWith(color: theme.hintColor),
                  ),
                ),
              ),
            )
          else ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Active Cycle (${cycle.durationWeeks} Weeks)',
                      style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 8),
                    Text('Start: ${cycle.startDate} · End: ${cycle.endDate} · Rev: ${cycle.revision}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Weekly Plans (${cycle.weeklyPlans.length})',
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            if (cycle.weeklyPlans.isEmpty)
              Padding(
                padding: const EdgeInsets.all(12.0),
                child: Text(
                  'No weekly plans added yet.',
                  style: theme.textTheme.bodySmall?.copyWith(color: theme.hintColor),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: cycle.weeklyPlans.length,
                itemBuilder: (context, index) {
                  final plan = cycle.weeklyPlans[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: CircleAvatar(
                        child: Text('${plan.weekNo}'),
                      ),
                      title: Text('Week ${plan.weekNo}: ${plan.focus ?? 'Focus not set'}'),
                      subtitle: Text('${plan.commitments.length} commitments'),
                    ),
                  );
                },
              ),
          ],
        ],
      ),
    );
  }

  void _showStartCycleDialog(BuildContext context) {
    int durationWeeks = 12;
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Start Operating Cycle'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Select cycle duration (1-12 weeks):'),
              DropdownButton<int>(
                value: durationWeeks,
                items: List.generate(12, (i) => i + 1)
                    .map((w) => DropdownMenuItem(value: w, child: Text('$w weeks')))
                    .toList(),
                onChanged: (val) {
                  if (val != null) setState(() => durationWeeks = val);
                },
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
                final now = DateTime.now().toIso8601String().split('T').first;
                controller.createCycle(durationWeeks, now);
                Navigator.of(ctx).pop();
              },
              child: const Text('Start'),
            ),
          ],
        ),
      ),
    );
  }

  void _showAddWeekDialog(BuildContext context, String cycleId, int defaultWeekNo) {
    final focusController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Add Week $defaultWeekNo'),
        content: TextField(
          controller: focusController,
          decoration: const InputDecoration(
            labelText: 'Weekly Focus',
            hintText: 'Enter week focus...',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              controller.createWeek(
                cycleId,
                defaultWeekNo,
                focus: focusController.text.trim().isNotEmpty
                    ? focusController.text.trim()
                    : null,
              );
              Navigator.of(ctx).pop();
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }
}
