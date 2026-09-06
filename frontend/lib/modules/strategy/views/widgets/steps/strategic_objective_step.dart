import 'package:flutter/material.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/modules/strategy/models/strategy_workflow_models.dart';

class StrategicObjectiveStep extends StatefulWidget {
  final List<StrategicObjectiveModel> objectives;
  final StrategicObjectiveModel? selectedObjective;
  final ValueChanged<StrategicObjectiveModel?> onObjectiveSelected;
  final Future<StrategicObjectiveModel?> Function(
    String title,
    String? successDefinition,
    String? timeHorizonEnd,
  )? onCreateObjective;
  final VoidCallback onNext;

  const StrategicObjectiveStep({
    super.key,
    required this.objectives,
    required this.selectedObjective,
    required this.onObjectiveSelected,
    this.onCreateObjective,
    required this.onNext,
  });

  @override
  State<StrategicObjectiveStep> createState() => _StrategicObjectiveStepState();
}

class _StrategicObjectiveStepState extends State<StrategicObjectiveStep> {
  bool _isCreating = false;
  final _titleController = TextEditingController();
  final _successDefController = TextEditingController();
  final _timeHorizonController = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _titleController.dispose();
    _successDefController.dispose();
    _timeHorizonController.dispose();
    super.dispose();
  }

  Future<void> _handleCreate() async {
    final title = _titleController.text.trim();
    if (title.isEmpty) return;
    if (widget.onCreateObjective == null) return;

    setState(() => _isSubmitting = true);
    try {
      final created = await widget.onCreateObjective!(
        title,
        _successDefController.text.trim().isEmpty ? null : _successDefController.text.trim(),
        _timeHorizonController.text.trim().isEmpty ? null : _timeHorizonController.text.trim(),
      );
      if (created != null && mounted) {
        widget.onObjectiveSelected(created);
        setState(() {
          _isCreating = false;
          _titleController.clear();
          _successDefController.clear();
          _timeHorizonController.clear();
        });
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bước 1: Mục tiêu chiến lược cấp cao',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Chọn hoặc tạo mục tiêu dài hạn để làm định hướng phân tích BSC & TOWS',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Colors.white70,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              if (!_isCreating && widget.onCreateObjective != null)
                ElevatedButton.icon(
                  key: const Key('btn_add_objective'),
                  onPressed: () => setState(() => _isCreating = true),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Tạo mục tiêu mới'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryColor,
                    foregroundColor: Colors.white,
                  ),
                ),
            ],
          ),
        const SizedBox(height: 16),
        if (_isCreating) _buildCreateForm(),
        if (!_isCreating && widget.objectives.isEmpty) _buildEmptyState(),
        if (!_isCreating && widget.objectives.isNotEmpty) _buildObjectivesList(),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            ElevatedButton.icon(
              key: const Key('btn_next_step'),
              onPressed: widget.selectedObjective != null ? widget.onNext : null,
              icon: const Icon(Icons.arrow_forward, size: 18),
              label: const Text('Tiếp tục: Trọng tâm BSC'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

  Widget _buildEmptyState() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        children: [
          const Icon(Icons.flag_outlined, size: 48, color: Colors.white38),
          const SizedBox(height: 12),
          const Text(
            'Chưa có mục tiêu chiến lược nào cho dự án này',
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Hãy tạo mục tiêu chiến lược đầu tiên để bắt đầu định hướng và phân tích ma trận TOWS.',
            style: TextStyle(color: Colors.white70, fontSize: 13),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: () => setState(() => _isCreating = true),
            icon: const Icon(Icons.add),
            label: const Text('Tạo mục tiêu chiến lược ngay'),
          ),
        ],
      ),
    );
  }

  Widget _buildCreateForm() {
    return Container(
      padding: const EdgeInsets.all(16),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.primaryColor.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Thêm mục tiêu chiến lược',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.white54, size: 20),
                onPressed: () => setState(() => _isCreating = false),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('input_objective_title'),
            controller: _titleController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Tên mục tiêu chiến lược (*)',
              hintText: 'Ví dụ: Đạt điểm hòa vốn và mở rộng sang thị trường Đông Nam Á',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('input_objective_success_def'),
            controller: _successDefController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Định nghĩa thành công (Success Definition)',
              hintText: 'Ví dụ: ARR đạt 1,000,000 USD, Net Retention Rate > 110%',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('input_objective_time_horizon'),
            controller: _timeHorizonController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Khung thời gian kết thúc (Time Horizon End)',
              hintText: 'Ví dụ: 2026-12-31 hoặc Q4/2026',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => setState(() => _isCreating = false),
                child: const Text('Hủy'),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                key: const Key('btn_submit_objective'),
                onPressed: _isSubmitting ? null : _handleCreate,
                child: _isSubmitting
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Lưu mục tiêu'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildObjectivesList() {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: widget.objectives.length,
      itemBuilder: (context, index) {
        final obj = widget.objectives[index];
        final isSelected = widget.selectedObjective?.id == obj.id;

        return Card(
          key: Key('card_objective_${obj.id}'),
          color: isSelected ? const Color(0xFF1E3A8A) : const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: isSelected ? Colors.blueAccent : Colors.white10,
              width: isSelected ? 2 : 1,
            ),
          ),
          margin: const EdgeInsets.only(bottom: 12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => widget.onObjectiveSelected(obj),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ignore: deprecated_member_use
                  Radio<String>(
                    value: obj.id,
                    // ignore: deprecated_member_use
                    groupValue: widget.selectedObjective?.id,
                    // ignore: deprecated_member_use
                    onChanged: (_) => widget.onObjectiveSelected(obj),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                obj.title,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                                ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.blue.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                obj.status,
                                style: const TextStyle(color: Colors.lightBlueAccent, fontSize: 11),
                              ),
                            ),
                          ],
                        ),
                        if (obj.successDefinition != null && obj.successDefinition!.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            'Tiêu chí: ${obj.successDefinition!}',
                            style: const TextStyle(color: Colors.white70, fontSize: 13),
                          ),
                        ],
                        if (obj.timeHorizonEnd != null && obj.timeHorizonEnd!.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            'Thời hạn: ${obj.timeHorizonEnd!}',
                            style: const TextStyle(color: Colors.white54, fontSize: 12),
                          ),
                        ],
                        if (obj.bscFocusScopes.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 6,
                            runSpacing: 4,
                            children: obj.bscFocusScopes.map((scope) {
                              return Chip(
                                label: Text(
                                  '${scope.perspective.displayNameVi}: ${scope.focusDescription}',
                                  style: const TextStyle(fontSize: 11, color: Colors.white),
                                ),
                                backgroundColor: const Color(0xFF334155),
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              );
                            }).toList(),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
