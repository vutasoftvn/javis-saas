import 'package:flutter/material.dart';
import '../../models/project_operating_loop.dart';
import '../../controllers/project_operating_loop_controller.dart';

/// Task 4 (2026-09-14 remediation) — `activeCycle` và `currentWeek` là 2
/// field gốc SIBLING (không phải `activeCycle.weeklyPlans[]`). Section này
/// hiển thị đúng 1 cycle + đúng 1 tuần hiện tại như backend thật trả về,
/// không còn danh sách weeklyPlans giả tưởng.
class CycleWeekSection extends StatelessWidget {
  final ProjectOperatingLoopController controller;
  final LoopActiveCycle? activeCycle;
  final LoopWeek? currentWeek;

  const CycleWeekSection({
    super.key,
    required this.controller,
    this.activeCycle,
    this.currentWeek,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cycle = activeCycle;
    final week = currentWeek;

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
                  'Operating Cycle & Current Week',
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
                  onPressed: () => _showAddWeekDialog(context, cycle.id, cycle.currentWeek),
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
                    Text(
                      'Start: ${cycle.startDate ?? '—'} · End: ${cycle.endDate ?? '—'} · Week: ${cycle.currentWeek}',
                    ),
                    if (cycle.theme != null) ...[
                      const SizedBox(height: 4),
                      Text('Theme: ${cycle.theme}'),
                    ],
                    const SizedBox(height: 4),
                    Text(
                      'Status: ${cycle.status}',
                      key: const Key('cycle_status_text'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Current Week',
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            if (week == null)
              Padding(
                padding: const EdgeInsets.all(12.0),
                child: Text(
                  'No week added to this cycle yet.',
                  style: theme.textTheme.bodySmall?.copyWith(color: theme.hintColor),
                ),
              )
            else
              Card(
                key: Key('week_${week.id}'),
                child: ListTile(
                  leading: CircleAvatar(
                    child: Text('${week.weekNo}'),
                  ),
                  title: Text('Week ${week.weekNo}: ${week.focus ?? 'Focus not set'}'),
                  subtitle: week.mission != null ? Text(week.mission!) : null,
                ),
              ),
            // Task 6 (2026-09-14 remediation) — Weekly close là hành động
            // Founder-initiated duy nhất, không timer/không auto-advance.
            // Ẩn hẳn khi cycle đã COMPLETED (backend tự set ở tuần cuối).
            if (week != null && cycle.status != 'COMPLETED') ...[
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: ElevatedButton.icon(
                  key: const Key('close_week_button'),
                  icon: const Icon(Icons.flag_outlined, size: 18),
                  label: const Text('Close Week'),
                  onPressed: () => _showCloseWeekDialog(context, cycle, week),
                ),
              ),
            ],
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

  // Task 6 (2026-09-14 remediation) — "explicit review" là gate bắt buộc:
  // reflection do Founder tự gõ (không prefill, không auto-generate), submit
  // bị khoá khi rỗng và trong lúc request đang chạy để chặn double-submit.
  // Không có timer/auto-advance nào ở đây — tuần chỉ đóng khi Founder bấm
  // nút này. `expectedCurrentWeek` luôn lấy từ `cycle.currentWeek` đã load
  // (CAS thật), không hardcode.
  void _showCloseWeekDialog(BuildContext context, LoopActiveCycle cycle, LoopWeek week) {
    final reflectionController = TextEditingController();
    final executionController = TextEditingController();
    final outcomeController = TextEditingController();
    bool submitting = false;
    String reflectionText = '';
    String? dialogError;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setState) {
          final canSubmit = !submitting && reflectionText.trim().isNotEmpty;
          return AlertDialog(
            title: Text('Close Week ${cycle.currentWeek}'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Cycle: ${cycle.durationWeeks} weeks total'),
                  Text('Current week: ${cycle.currentWeek}'),
                  Text('Status: ${cycle.status}'),
                  const SizedBox(height: 12),
                  TextField(
                    key: const Key('close_week_reflection_field'),
                    controller: reflectionController,
                    enabled: !submitting,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Reflection (required)',
                      hintText: 'What happened this week?',
                    ),
                    onChanged: (value) => setState(() => reflectionText = value),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    key: const Key('close_week_execution_score_field'),
                    controller: executionController,
                    enabled: !submitting,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Execution score (optional)'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    key: const Key('close_week_outcome_score_field'),
                    controller: outcomeController,
                    enabled: !submitting,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Outcome score (optional)'),
                  ),
                  if (dialogError != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      dialogError!,
                      key: const Key('close_week_error_text'),
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: submitting ? null : () => Navigator.of(dialogContext).pop(),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                key: const Key('close_week_submit_button'),
                onPressed: canSubmit
                    ? () async {
                        setState(() {
                          submitting = true;
                          dialogError = null;
                        });
                        final ok = await controller.closeCurrentWeek(
                          cycle.id,
                          expectedCurrentWeek: cycle.currentWeek,
                          reflection: reflectionText.trim(),
                          executionScore: double.tryParse(executionController.text.trim()),
                          outcomeScore: double.tryParse(outcomeController.text.trim()),
                        );
                        if (ok) {
                          if (dialogContext.mounted) {
                            Navigator.of(dialogContext).pop();
                          }
                        } else {
                          setState(() {
                            submitting = false;
                            dialogError = controller.errorMessage.value;
                          });
                        }
                      }
                    : null,
                child: submitting
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Close Week'),
              ),
            ],
          );
        },
      ),
    );
  }
}
