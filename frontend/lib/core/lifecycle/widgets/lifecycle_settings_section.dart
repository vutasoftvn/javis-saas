import 'package:flutter/material.dart';
import '../lifecycle_service.dart';

// Task 13 — danh sách stage cứng chỉ dùng để hiển thị dropdown/nút chuyển
// giai đoạn ở UI. Copy đúng 6 giá trị Workspace (workspace-lifecycle.service.ts:11-18)
// và 7 giá trị Project (project-lifecycle.service.ts:13-21) — không tự bịa
// thêm/bớt giá trị nào ở đây, backend là nguồn sự thật duy nhất cho thứ tự
// và tên stage.
const _workspaceStages = [
  'W0_IDEA',
  'W1_PROBLEM_VALIDATION',
  'W2_SOLUTION_VALIDATION',
  'W3_MVP_BUILD',
  'W4_PRODUCT_MARKET_FIT',
  'W5_SCALE',
];

const _projectStages = [
  'P0_DISCOVERY',
  'P1_PROBLEM_VALIDATION',
  'P2_SOLUTION_VALIDATION',
  'P3_BUILD_VALIDATE',
  'P4_GO_TO_MARKET',
  'P5_OPERATE_GROWTH',
  'P6_SCALE_GOVERN',
];

/// Task 13 — UI dùng chung cho lifecycle transition của Workspace và Project.
/// Nguyên tắc bắt buộc (CLAUDE.md #5/#8 + task brief): chuyển giai đoạn luôn
/// là hành động người dùng chủ động bấm — tiến (advance) 1 tap, lùi
/// (backward) bắt buộc nhập rationale trước khi xác nhận; không có đường nào
/// tự động chuyển stage mà không qua widget này.
class LifecycleSettingsSection extends StatefulWidget {
  const LifecycleSettingsSection({
    super.key,
    required this.entityType,
    required this.entityId,
    required this.currentStage,
    required this.currentStageVersion,
    this.onTransitioned,
  });

  final LifecycleEntityType entityType;
  final String entityId;
  final String currentStage;
  final int currentStageVersion;
  final void Function(String newStage)? onTransitioned;

  @override
  State<LifecycleSettingsSection> createState() => _LifecycleSettingsSectionState();
}

class _LifecycleSettingsSectionState extends State<LifecycleSettingsSection> {
  final _service = LifecycleService();
  bool _busy = false;

  List<String> get _stages =>
      widget.entityType == LifecycleEntityType.workspace ? _workspaceStages : _projectStages;

  Future<void> _transitionTo(String toStage) async {
    final isBackward = _stages.indexOf(toStage) < _stages.indexOf(widget.currentStage);
    String? rationale;
    if (isBackward) {
      rationale = await showDialog<String>(
        context: context,
        builder: (dialogContext) {
          final controller = TextEditingController();
          return AlertDialog(
            title: const Text('Lý do lùi giai đoạn'),
            content: TextField(controller: controller, autofocus: true, maxLines: 3),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: const Text('Huỷ'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(dialogContext).pop(controller.text.trim()),
                child: const Text('Xác nhận'),
              ),
            ],
          );
        },
      );
      if (rationale == null || rationale.isEmpty) return;
    }

    setState(() => _busy = true);
    try {
      await _service.transition(
        widget.entityType,
        widget.entityId,
        toStage: toStage,
        expectedStageVersion: widget.currentStageVersion,
        rationale: rationale,
      );
      widget.onTransitioned?.call(toStage);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Không chuyển được giai đoạn: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentIndex = _stages.indexOf(widget.currentStage);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Giai đoạn hiện tại: ${widget.currentStage}', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                if (currentIndex >= 0 && currentIndex < _stages.length - 1)
                  ElevatedButton(
                    onPressed: _busy ? null : () => _transitionTo(_stages[currentIndex + 1]),
                    child: Text('Tiến sang ${_stages[currentIndex + 1]}'),
                  ),
                if (currentIndex > 0)
                  OutlinedButton(
                    onPressed: _busy ? null : () => _showBackwardMenu(context, currentIndex),
                    child: const Text('Lùi giai đoạn'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showBackwardMenu(BuildContext context, int currentIndex) async {
    final target = await showMenu<String>(
      context: context,
      position: const RelativeRect.fromLTRB(0, 0, 0, 0),
      items: [
        for (var i = 0; i < currentIndex; i++)
          PopupMenuItem(value: _stages[i], child: Text(_stages[i])),
      ],
    );
    if (target != null) await _transitionTo(target);
  }
}
