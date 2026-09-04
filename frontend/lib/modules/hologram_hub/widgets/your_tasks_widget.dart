import 'package:flutter/material.dart';

import '../../../data/models/execution_plan_model.dart';

/// WGA #6a — "Việc của bạn": task founder tự làm (FOUNDER_ONLY) + task AI bị
/// chặn (blocked), đều từ kế hoạch triển khai đã duyệt.
class YourTasksWidget extends StatelessWidget {
  final List<FounderInboxTask> tasks;

  const YourTasksWidget({super.key, required this.tasks});

  @override
  Widget build(BuildContext context) {
    if (tasks.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.person_pin_circle_outlined,
                  color: Color(0xFF60A5FA), size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Việc của bạn',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
              ),
              Text('${tasks.length}',
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
            ],
          ),
          const SizedBox(height: 10),
          ...tasks.map(
            (t) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  Icon(
                    t.isBlocked ? Icons.block : Icons.check_box_outline_blank,
                    size: 15,
                    color: t.isBlocked
                        ? const Color(0xFFF87171)
                        : const Color(0xFF60A5FA),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      t.title,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                  ),
                  Text(
                    t.isBlocked ? 'Bị chặn' : 'Cần bạn làm',
                    style: TextStyle(
                      color: t.isBlocked
                          ? const Color(0xFFF87171)
                          : const Color(0xFF60A5FA),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
