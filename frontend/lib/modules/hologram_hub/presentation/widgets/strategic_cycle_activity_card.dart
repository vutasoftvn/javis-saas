import 'package:flutter/material.dart';
import 'hud_card.dart';

/// Card Nhật Ký Hoạt Động Chiến Lược & Tiến Độ Thực Thi (Live Strategic Activity HUD)
/// Hiển thị chu kỳ đang chạy, tiến độ các tuần và dòng nhật ký tác vụ của 5 phòng ban AI theo thời gian thực.
class StrategicCycleActivityCard extends StatelessWidget {
  final Map<String, dynamic>? cycleTimeline;
  final List<dynamic>? recentActivities;
  final VoidCallback? onOpenFullTimeline;
  final Function(int weekNo)? onSelectWeek;

  const StrategicCycleActivityCard({
    super.key,
    this.cycleTimeline,
    this.recentActivities,
    this.onOpenFullTimeline,
    this.onSelectWeek,
  });

  Color _getFunctionColor(String fn) {
    switch (fn.toUpperCase()) {
      case 'TECH':
        return const Color(0xFF14B8A6); // Cyan
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

  @override
  Widget build(BuildContext context) {
    final timelineData = cycleTimeline?['data'] as Map<String, dynamic>?;
    final projectName = timelineData?['project_name']?.toString() ?? 'Chu kỳ Thực thi';
    final totalWeeks = timelineData?['total_weeks'] ?? 13;
    final currentWeek = timelineData?['current_week'] ?? 1;
    final steps = (timelineData?['timeline_steps'] as List<dynamic>?) ?? [];

    // Calculate overall progress
    double totalProgress = 0;
    if (steps.isNotEmpty) {
      double sum = 0;
      for (var s in steps) {
        sum += ((s['progress_percent'] as num?)?.toDouble() ?? 0.0);
      }
      totalProgress = (sum / (steps.length * 100.0)).clamp(0.0, 1.0);
    }

    return hudCard(
      onTap: onOpenFullTimeline,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          hudCardHeader(
            title: 'TIẾN ĐỘ CHU KỲ CHIẾN LƯỢC',
            badgeText: '$totalWeeks TUẦN • TUẦN $currentWeek',
            badgeColor: const Color(0xFF14B8A6),
          ),
          const SizedBox(height: 10),

          // Project Title & Overall Progress
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  projectName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${(totalProgress * 100).toInt()}%',
                style: const TextStyle(
                  color: Color(0xFF14B8A6),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),

          // Progress Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: totalProgress,
              minHeight: 5,
              backgroundColor: const Color(0xFF1E293B),
              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF14B8A6)),
            ),
          ),
          const SizedBox(height: 12),

          // Mini Timeline Stepper Nodes
          if (steps.isNotEmpty)
            SizedBox(
              height: 36,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: steps.length,
                separatorBuilder: (context, index) => Container(
                  width: 12,
                  height: 1,
                  color: const Color(0xFF334155),
                  margin: const EdgeInsets.only(top: 14),
                ),
                itemBuilder: (context, index) {
                  final step = steps[index] as Map<String, dynamic>;
                  final weekNo = step['week_no'] ?? (index + 1);
                  final status = step['status']?.toString() ?? 'pending';
                  final isDone = status == 'completed';
                  final isRunning = status == 'in_progress';

                  final nodeColor = isDone
                      ? const Color(0xFF10B981)
                      : (isRunning ? const Color(0xFF14B8A6) : const Color(0xFF475569));

                  return InkWell(
                    onTap: () => onSelectWeek?.call(weekNo),
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: nodeColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: nodeColor.withValues(alpha: isRunning ? 0.8 : 0.4),
                          width: isRunning ? 1.5 : 1.0,
                        ),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            'T$weekNo',
                            style: TextStyle(
                              color: nodeColor,
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          Icon(
                            isDone ? Icons.check : (isRunning ? Icons.play_arrow_rounded : Icons.circle),
                            size: 10,
                            color: nodeColor,
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

          const SizedBox(height: 12),
          const Divider(height: 1, color: Color(0xFF1E293B)),
          const SizedBox(height: 8),

          // Realtime Live Activity Feed
          const Text(
            'NHẬT KÝ 5 PHÒNG BAN AI',
            style: TextStyle(
              color: Color(0xFF64748B),
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 6),

          if (recentActivities == null || recentActivities!.isEmpty)
            const Text(
              'Đang lắng nghe tác vụ từ 5 phòng ban AI...',
              style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
            )
          else
            ...recentActivities!.take(3).map((act) {
              final actMap = act is Map<String, dynamic> ? act : <String, dynamic>{};
              final fn = actMap['function']?.toString() ?? 'SYSTEM';
              final title = actMap['title']?.toString() ?? actMap['description']?.toString() ?? 'Hoạt động';
              final time = actMap['time']?.toString() ?? '';
              final fnColor = _getFunctionColor(fn);

              return Padding(
                padding: const EdgeInsets.only(bottom: 6.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: fnColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: fnColor.withValues(alpha: 0.3)),
                      ),
                      child: Text(
                        fn,
                        style: TextStyle(
                          color: fnColor,
                          fontSize: 9,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(
                          color: Color(0xFFCBD5E1),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (time.isNotEmpty) ...[
                      const SizedBox(width: 6),
                      Text(
                        time,
                        style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                      ),
                    ],
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}
