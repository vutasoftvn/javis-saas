import 'package:flutter/material.dart';

class WeeklyExecutionGauge extends StatelessWidget {
  final double score; // 0.0 -> 100.0%
  final int weekNumber;

  const WeeklyExecutionGauge({
    super.key,
    required this.score,
    required this.weekNumber,
  });

  Color get scoreColor {
    if (score >= 85.0) return const Color(0xFF10B981); // Emerald Green
    if (score >= 60.0) return const Color(0xFFF59E0B); // Amber Warning
    return const Color(0xFFEF4444); // Crimson Alert
  }

  String get velocityGrade {
    if (score >= 85.0) return 'Kỷ Luật Xuất Sắc (>=85%)';
    if (score >= 60.0) return 'Vận Tốc Khá (60-84%)';
    return 'Cảnh Báo Chậm Trễ (<60%)';
  }

  IconData get velocityIcon {
    if (score >= 85.0) return Icons.speed;
    if (score >= 60.0) return Icons.timelapse;
    return Icons.warning_amber_rounded;
  }

  @override
  Widget build(BuildContext context) {
    final color = scoreColor;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.4), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.1),
            blurRadius: 12,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Row(
        children: [
          // Circular gauge
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withValues(alpha: 0.12),
              border: Border.all(color: color, width: 3),
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${score.toInt()}%',
                    style: TextStyle(color: color, fontSize: 17, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    'Tuần $weekNumber',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 9),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 14),

          // Details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(velocityIcon, color: color, size: 16),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        velocityGrade,
                        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  'Chuẩn 12-Week Year: Điểm thực thi tuần (Weekly Execution Score) >= 85% đảm bảo 90% khả năng đạt mục tiêu quý.',
                  style: TextStyle(color: Colors.white70, fontSize: 11, height: 1.3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
