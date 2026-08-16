import 'package:flutter/material.dart';

class StrategicTimelineCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final Function(int weekNo)? onStepTap;
  final VoidCallback? onOpenDashboard;
  final Function(int weekNo)? onTalkToStep;

  const StrategicTimelineCard({
    super.key,
    required this.data,
    this.onStepTap,
    this.onOpenDashboard,
    this.onTalkToStep,
  });

  Color _getFunctionColor(String fn) {
    switch (fn.toUpperCase()) {
      case 'TECH':
        return const Color(0xFF00F0FF); // Cyan
      case 'LEGAL':
        return const Color(0xFFF59E0B); // Amber
      case 'MARKETING':
        return const Color(0xFFEC4899); // Pink
      case 'SALES':
        return const Color(0xFF10B981); // Emerald
      case 'FINANCE':
        return const Color(0xFF8B5CF6); // Purple
      default:
        return const Color(0xFF818CF8); // Indigo
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'done':
        return const Color(0xFF10B981);
      case 'in_progress':
      case 'running':
        return const Color(0xFF00F0FF);
      case 'blocked':
      case 'failed':
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF64748B);
    }
  }

  @override
  Widget build(BuildContext context) {
    final projectName = data['project_name']?.toString() ?? 'Dự án';
    final totalWeeks = data['total_weeks'] ?? 13;
    final theme = data['theme']?.toString() ?? '';
    final steps = (data['timeline_steps'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.40),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
          BoxShadow(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.06),
            blurRadius: 18,
            spreadRadius: 0.5,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header Row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.auto_graph_rounded,
                  color: Color(0xFF00F0FF),
                  size: 20,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      projectName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (theme.isNotEmpty)
                      Text(
                        theme,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFF10B981).withValues(alpha: 0.4),
                  ),
                ),
                child: Text(
                  '$totalWeeks TUẦN',
                  style: const TextStyle(
                    color: Color(0xFF10B981),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Timeline Steps List
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: steps.length,
            separatorBuilder: (context, index) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final step = steps[index] as Map<String, dynamic>;
              final weekNo = step['week_no'] ?? (index + 1);
              final weekRange = step['week_range']?.toString() ?? 'Tuần $weekNo';
              final title = step['title']?.toString() ?? '';
              final status = step['status']?.toString() ?? 'pending';
              final progress = (step['progress_percent'] as num?)?.toDouble() ?? 0.0;
              final functions = (step['owner_functions'] as List<dynamic>?) ?? [];
              final statusColor = _getStatusColor(status);

              return InkWell(
                onTap: () => onStepTap?.call(weekNo),
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B).withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: status == 'in_progress'
                          ? const Color(0xFF00F0FF).withValues(alpha: 0.5)
                          : const Color(0xFF334155),
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Status Node Indicator
                      Container(
                        margin: const EdgeInsets.only(top: 2),
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: statusColor.withValues(alpha: 0.2),
                          border: Border.all(color: statusColor, width: 1.5),
                        ),
                        child: Icon(
                          status == 'completed'
                              ? Icons.check
                              : (status == 'in_progress' ? Icons.sync : Icons.circle),
                          size: 10,
                          color: statusColor,
                        ),
                      ),
                      const SizedBox(width: 10),

                      // Step Details
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  weekRange.toUpperCase(),
                                  style: TextStyle(
                                    color: statusColor,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    title,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                if (progress > 0)
                                  Text(
                                    '${progress.toInt()}%',
                                    style: TextStyle(
                                      color: statusColor,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 6),

                            // Function Badges
                            Wrap(
                              spacing: 6,
                              runSpacing: 4,
                              children: functions.map((fn) {
                                final fnStr = fn.toString();
                                final fnColor = _getFunctionColor(fnStr);
                                return Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: fnColor.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(4),
                                    border: Border.all(
                                      color: fnColor.withValues(alpha: 0.3),
                                    ),
                                  ),
                                  child: Text(
                                    fnStr,
                                    style: TextStyle(
                                      color: fnColor,
                                      fontSize: 10,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      ),

                      // Quick Voice Button for Step
                      if (onTalkToStep != null)
                        IconButton(
                          icon: const Icon(Icons.mic, size: 16),
                          color: const Color(0xFF00F0FF),
                          tooltip: 'Chỉ đạo tuần $weekNo',
                          onPressed: () => onTalkToStep?.call(weekNo),
                        ),
                    ],
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 12),

          // Bottom Action Bar
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'COSA Execution Loop',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                ),
              ),
              if (onOpenDashboard != null)
                TextButton.icon(
                  onPressed: onOpenDashboard,
                  icon: const Icon(
                    Icons.dashboard_customize_rounded,
                    size: 14,
                    color: Color(0xFF00F0FF),
                  ),
                  label: const Text(
                    'Mở Dashboard 12WY',
                    style: TextStyle(
                      color: Color(0xFF00F0FF),
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
