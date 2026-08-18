import 'package:flutter/material.dart';

class TwelveWeekTimelineBar extends StatelessWidget {
  final int currentWeek;
  final int selectedWeek;
  final Map<int, double> weeklyScores;
  final ValueChanged<int> onSelectWeek;

  const TwelveWeekTimelineBar({
    super.key,
    required this.currentWeek,
    required this.selectedWeek,
    required this.weeklyScores,
    required this.onSelectWeek,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: 12,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final weekNo = index + 1;
          final isSelected = weekNo == selectedWeek;
          final isCurrent = weekNo == currentWeek;
          final score = weeklyScores[weekNo] ?? 0.0;

          Color scoreColor = Colors.white38;
          if (score >= 85.0) {
            scoreColor = const Color(0xFF10B981);
          } else if (score >= 60.0) {
            scoreColor = const Color(0xFFF59E0B);
          } else if (score > 0.0) {
            scoreColor = const Color(0xFFEF4444);
          }

          return InkWell(
            onTap: () => onSelectWeek(weekNo),
            borderRadius: BorderRadius.circular(10),
            child: Container(
              width: 54,
              decoration: BoxDecoration(
                color: isSelected
                    ? const Color(0xFF38BDF8).withValues(alpha: 0.2)
                    : const Color(0xFF1E293B).withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: isSelected
                      ? const Color(0xFF38BDF8)
                      : isCurrent
                          ? const Color(0xFFF59E0B)
                          : Colors.white.withValues(alpha: 0.1),
                  width: isSelected || isCurrent ? 1.5 : 1.0,
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'W$weekNo',
                        style: TextStyle(
                          color: isSelected
                              ? const Color(0xFF38BDF8)
                              : isCurrent
                                  ? const Color(0xFFF59E0B)
                                  : Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (isCurrent) ...[
                        const SizedBox(width: 2),
                        Container(
                          width: 4,
                          height: 4,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: Color(0xFFF59E0B),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${score.toInt()}%',
                    style: TextStyle(
                      color: scoreColor,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
