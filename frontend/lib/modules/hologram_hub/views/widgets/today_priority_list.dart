import 'package:flutter/material.dart';

class TodayPriorityList extends StatelessWidget {
  final List<dynamic> priorities;
  final Function(String taskId)? onToggleTask;
  final Function(String taskId)? onTapTask;

  const TodayPriorityList({
    super.key,
    required this.priorities,
    this.onToggleTask,
    this.onTapTask,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1527).withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFF3B82F6).withValues(alpha: 0.25),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF1E3A8A).withValues(alpha: 0.1),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.stars_rounded,
                  color: Color(0xFF60A5FA),
                  size: 18,
                ),
              ),
              const SizedBox(width: 10),
              const Text(
                'VIỆC ƯU TIÊN HÔM NAY',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${priorities.length} mục',
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (priorities.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 24),
              alignment: Alignment.center,
              child: const Column(
                children: [
                  Icon(
                    Icons.check_circle_outline_rounded,
                    color: Color(0xFF10B981),
                    size: 28,
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Không có việc tồn đọng hôm nay!',
                    style: TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: priorities.length,
              separatorBuilder: (context, index) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = priorities[index] as Map<String, dynamic>;
                return _buildPriorityItem(context, item);
              },
            ),
        ],
      ),
    );
  }

  Widget _buildPriorityItem(BuildContext context, Map<String, dynamic> item) {
    final id = item['id']?.toString() ?? '';
    final title = item['title']?.toString() ?? 'Nhiệm vụ';
    final priority = (item['priority']?.toString() ?? 'high').toLowerCase();
    final status = (item['status']?.toString() ?? 'todo').toLowerCase();
    final dueTime = item['due_time']?.toString() ?? '17:00';
    final agent = item['agent_assigned']?.toString() ?? 'COSA AI';

    final isDone = status == 'done' || status == 'completed';

    Color priorityColor;
    String priorityText;
    switch (priority) {
      case 'urgent':
        priorityColor = const Color(0xFFEF4444);
        priorityText = 'KHẨN';
        break;
      case 'high':
        priorityColor = const Color(0xFFF59E0B);
        priorityText = 'CAO';
        break;
      default:
        priorityColor = const Color(0xFF38BDF8);
        priorityText = 'VỪA';
    }

    return InkWell(
      onTap: () => onTapTask?.call(id),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF131D35),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDone
                ? const Color(0xFF10B981).withValues(alpha: 0.3)
                : const Color(0xFF1E293B),
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              onTap: () => onToggleTask?.call(id),
              child: Container(
                margin: const EdgeInsets.only(top: 2),
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: isDone
                      ? const Color(0xFF10B981)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(5),
                  border: Border.all(
                    color: isDone
                        ? const Color(0xFF10B981)
                        : const Color(0xFF475569),
                    width: 1.5,
                  ),
                ),
                child: isDone
                    ? const Icon(
                        Icons.check,
                        size: 13,
                        color: Colors.black,
                      )
                    : null,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: isDone ? const Color(0xFF64748B) : Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      decoration: isDone ? TextDecoration.lineThrough : null,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: priorityColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: priorityColor.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          priorityText,
                          style: TextStyle(
                            color: priorityColor,
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.access_time_rounded,
                        size: 11,
                        color: const Color(0xFF64748B),
                      ),
                      const SizedBox(width: 3),
                      Text(
                        dueTime,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 11,
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.smart_toy_outlined,
                              size: 11,
                              color: Color(0xFF38BDF8),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              agent,
                              style: const TextStyle(
                                color: Color(0xFF38BDF8),
                                fontSize: 10,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
