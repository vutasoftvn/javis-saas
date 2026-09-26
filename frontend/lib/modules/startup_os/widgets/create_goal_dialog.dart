import 'package:flutter/material.dart';

import '../../../core/network/api_result.dart';
import '../controllers/startup_os_controller.dart';
import '../models/startup_os_models.dart';

/// Tạo Goal trong cây phân tầng. Trả về [CreatedGoal] chỉ khi server xác nhận
/// (có goalId); lỗi hiển thị ngay trong dialog, không đóng dialog.
class CreateGoalDialog extends StatefulWidget {
  const CreateGoalDialog({super.key, required this.controller});

  final StartupOsController controller;

  @override
  State<CreateGoalDialog> createState() => _CreateGoalDialogState();
}

class _CreateGoalDialogState extends State<CreateGoalDialog> {
  final _title = TextEditingController();
  final _description = TextEditingController();
  GoalType _type = GoalType.strategic;
  String? _parentId;
  DateTimeRange? _range;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    super.dispose();
  }

  String _date(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _pickRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 6),
      initialDateRange: _range,
    );
    if (picked != null) setState(() => _range = picked);
  }

  Future<void> _submit() async {
    final title = _title.text.trim();
    if (title.isEmpty) {
      setState(() => _error = 'Cần nhập tên mục tiêu.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    final description = _description.text.trim();
    final result = await widget.controller.createGoal(
      title: title,
      goalType: _type,
      parentId: _parentId,
      description: description.isEmpty ? null : description,
      startDate: _range == null ? null : _date(_range!.start),
      endDate: _range == null ? null : _date(_range!.end),
    );
    if (!mounted) return;
    switch (result) {
      case ApiSuccess(:final data):
        Navigator.of(context).pop(data);
      case ApiFailure(:final failure):
        setState(() {
          _submitting = false;
          _error = startupOsFailureMessage(failure);
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    final parents = widget.controller.flatGoals;
    return AlertDialog(
      title: const Text('Thêm mục tiêu'),
      content: SizedBox(
        width: 420,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                key: const Key('goal-title-field'),
                controller: _title,
                decoration: const InputDecoration(labelText: 'Tên mục tiêu'),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<GoalType>(
                key: const Key('goal-type-field'),
                isExpanded: true,
                initialValue: _type,
                decoration: const InputDecoration(labelText: 'Loại mục tiêu'),
                items: [
                  for (final t in GoalType.values) DropdownMenuItem(value: t, child: Text(goalTypeLabel(t))),
                ],
                onChanged: (t) => setState(() => _type = t ?? _type),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String?>(
                isExpanded: true,
                initialValue: _parentId,
                decoration: const InputDecoration(labelText: 'Thuộc mục tiêu cha (tuỳ chọn)'),
                items: [
                  const DropdownMenuItem<String?>(value: null, child: Text('— Không có —')),
                  for (final g in parents)
                    DropdownMenuItem<String?>(
                      value: g.id,
                      child: Text('${'  ' * g.depth}${g.title}', overflow: TextOverflow.ellipsis),
                    ),
                ],
                onChanged: (id) => setState(() => _parentId = id),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _description,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Mô tả (tuỳ chọn)'),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: const Icon(Icons.date_range, size: 18),
                label: Text(_range == null
                    ? 'Chọn thời gian (tuỳ chọn)'
                    : '${_date(_range!.start)} → ${_date(_range!.end)}'),
                onPressed: _pickRange,
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, key: const Key('create-goal-error'), style: const TextStyle(color: Colors.redAccent)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: _submitting ? null : () => Navigator.pop(context), child: const Text('Huỷ')),
        ElevatedButton(
          key: const Key('create-goal-submit'),
          onPressed: _submitting ? null : _submit,
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Tạo'),
        ),
      ],
    );
  }
}
