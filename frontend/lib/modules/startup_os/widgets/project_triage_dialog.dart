import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/network/api_result.dart';
import '../../../core/widgets/app_toast.dart';
import '../controllers/startup_os_controller.dart';
import '../models/startup_os_models.dart';

/// Triage dự án khám phá cuối chu kỳ (plan 2026-09-18 Task 4.4).
///
/// Hỗ trợ 3 hành động: giữ làm R&D, lưu trữ, hoặc nâng thành Objective của một
/// Goal. "Liên kết vào Objective có sẵn" chưa có vì Company chưa có endpoint liệt
/// kê Objective để chọn — không cho nhập id tay.
class ProjectTriageDialog extends StatelessWidget {
  const ProjectTriageDialog({super.key, required this.controller});

  final StartupOsController controller;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Rà soát dự án khám phá'),
      content: SizedBox(
        width: 480,
        child: Obx(() {
          final projects = controller.pendingProjects;
          if (projects.isEmpty) {
            return const Text('Không còn dự án nào chờ rà soát.');
          }
          return ListView(
            shrinkWrap: true,
            children: [
              for (final p in projects) _TriageRow(project: p, controller: controller),
            ],
          );
        }),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Đóng'))],
    );
  }
}

class _TriageRow extends StatefulWidget {
  const _TriageRow({required this.project, required this.controller});

  final PendingProject project;
  final StartupOsController controller;

  @override
  State<_TriageRow> createState() => _TriageRowState();
}

class _TriageRowState extends State<_TriageRow> {
  TriageAction? _action;
  String? _goalId;
  final _objectiveTitle = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _objectiveTitle.dispose();
    super.dispose();
  }

  bool get _ready {
    if (_action == null) return false;
    if (_action == TriageAction.rollToNewGoal) {
      return _goalId != null && _objectiveTitle.text.trim().isNotEmpty;
    }
    return true;
  }

  Future<void> _apply() async {
    final action = _action;
    if (action == null) return;
    setState(() => _busy = true);
    final result = await widget.controller.triageProject(
      projectId: widget.project.id,
      action: action,
      newGoalId: action == TriageAction.rollToNewGoal ? _goalId : null,
      newObjectiveTitle: action == TriageAction.rollToNewGoal ? _objectiveTitle.text.trim() : null,
    );
    if (!mounted) return;
    setState(() => _busy = false);
    switch (result) {
      case ApiSuccess():
        AppToast.success('Đã rà soát "${widget.project.title}".');
      case ApiFailure(:final failure):
        AppToast.error(startupOsFailureMessage(failure));
    }
  }

  @override
  Widget build(BuildContext context) {
    final goals = widget.controller.flatGoals.where((g) => g.isActive).toList(growable: false);
    return Card(
      key: Key('triage-${widget.project.id}'),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.project.title, style: const TextStyle(fontWeight: FontWeight.w600)),
            if (widget.project.description != null) Text(widget.project.description!),
            const SizedBox(height: 8),
            DropdownButtonFormField<TriageAction>(
              isExpanded: true,
              initialValue: _action,
              decoration: const InputDecoration(labelText: 'Quyết định'),
              items: [
                for (final a in TriageAction.values) DropdownMenuItem(value: a, child: Text(a.label)),
              ],
              onChanged: (a) => setState(() => _action = a),
            ),
            if (_action == TriageAction.rollToNewGoal) ...[
              const SizedBox(height: 8),
              if (goals.isEmpty)
                const Text('Chưa có mục tiêu đang hoạt động để gắn Objective.')
              else
                DropdownButtonFormField<String>(
                  isExpanded: true,
                  initialValue: _goalId,
                  decoration: const InputDecoration(labelText: 'Mục tiêu'),
                  items: [
                    for (final g in goals)
                      DropdownMenuItem(value: g.id, child: Text(g.title, overflow: TextOverflow.ellipsis)),
                  ],
                  onChanged: (id) => setState(() => _goalId = id),
                ),
              TextField(
                controller: _objectiveTitle,
                decoration: const InputDecoration(labelText: 'Tên Objective mới'),
                onChanged: (_) => setState(() {}),
              ),
            ],
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton(
                onPressed: _ready && !_busy ? _apply : null,
                child: const Text('Áp dụng'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
