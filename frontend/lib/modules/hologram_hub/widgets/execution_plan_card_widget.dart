import 'package:flutter/material.dart';

import '../../../data/models/execution_plan_model.dart';

/// WGA — "Kế hoạch đề xuất": agent phân rã mục tiêu tuần thành các việc, mỗi
/// việc gắn lớp quyền hạn (AI tự làm / Cần bạn duyệt / Bạn tự làm). Founder
/// duyệt cả lô hoặc bỏ, có thể đổi class từng item.
class ExecutionPlanCardWidget extends StatelessWidget {
  final ExecutionPlan plan;
  final Future<void> Function(String planId) onAccept;
  final Future<void> Function(String planId) onReject;
  final Future<void> Function(String itemId, AutonomyClass klass) onChangeItemClass;
  final Future<void> Function(String itemId) onDropItem;

  const ExecutionPlanCardWidget({
    super.key,
    required this.plan,
    required this.onAccept,
    required this.onReject,
    required this.onChangeItemClass,
    required this.onDropItem,
  });

  Color _classColor(AutonomyClass c) {
    switch (c) {
      case AutonomyClass.auto:
        return const Color(0xFF22C55E);
      case AutonomyClass.needsApproval:
        return const Color(0xFFF59E0B);
      case AutonomyClass.founderOnly:
        return const Color(0xFF60A5FA);
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = plan.liveItems;
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF6366F1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: Color(0xFF818CF8), size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Kế hoạch đề xuất',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
              ),
              Text(
                '${items.length} việc',
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            plan.goalText,
            style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13),
          ),
          const SizedBox(height: 12),
          ...items.map((it) => _buildItemRow(context, it)),
          const SizedBox(height: 12),
          Row(
            children: [
              ElevatedButton.icon(
                onPressed:
                    plan.canAccept ? () => onAccept(plan.id) : null,
                icon: const Icon(Icons.check, size: 16),
                label: const Text('Chấp nhận cả lô'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  foregroundColor: Colors.white,
                ),
              ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => onReject(plan.id),
                child: const Text('Bỏ', style: TextStyle(color: Color(0xFF94A3B8))),
              ),
              if (!plan.canAccept && items.isNotEmpty)
                const Expanded(
                  child: Text(
                    'Một số việc còn thiếu bằng chứng (evidence).',
                    textAlign: TextAlign.right,
                    style: TextStyle(color: Color(0xFFF87171), fontSize: 11),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildItemRow(BuildContext context, ExecutionPlanItem it) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 8,
            height: 8,
            margin: const EdgeInsets.only(top: 5, right: 10),
            decoration: BoxDecoration(
              color: _classColor(it.autonomyClass),
              shape: BoxShape.circle,
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  it.title,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
                if (it.expectedCapability != null)
                  Text(
                    it.expectedCapability!,
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          DropdownButton<AutonomyClass>(
            value: it.autonomyClass,
            isDense: true,
            dropdownColor: const Color(0xFF0F172A),
            underline: const SizedBox.shrink(),
            style: TextStyle(color: _classColor(it.autonomyClass), fontSize: 11),
            items: AutonomyClass.values
                .map(
                  (c) => DropdownMenuItem(
                    value: c,
                    child: Text(autonomyClassLabel(c)),
                  ),
                )
                .toList(),
            onChanged: (c) {
              if (c != null && c != it.autonomyClass) {
                onChangeItemClass(it.id, c);
              }
            },
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 14, color: Color(0xFF64748B)),
            tooltip: 'Bỏ việc này',
            onPressed: () => onDropItem(it.id),
          ),
        ],
      ),
    );
  }
}
