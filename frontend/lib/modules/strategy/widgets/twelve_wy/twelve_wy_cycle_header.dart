import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class TwelveWyCycleHeader extends StatelessWidget {
  final Map<String, dynamic> cycle;

  const TwelveWyCycleHeader({super.key, required this.cycle});

  @override
  Widget build(BuildContext context) {
    final theme = cycle['theme']?.toString() ?? 'Chu kỳ thực thi 12 tuần';
    final durationWeeks = cycle['duration_weeks'] ?? 12;
    final startDateStr = cycle['start_date']?.toString();
    final endDateStr = cycle['end_date']?.toString();

    String dateRange = '';
    if (startDateStr != null && startDateStr.isNotEmpty) {
      try {
        final startDt = DateTime.parse(startDateStr);
        final startFmt = '${startDt.day.toString().padLeft(2, '0')}/${startDt.month.toString().padLeft(2, '0')}/${startDt.year}';
        if (endDateStr != null && endDateStr.isNotEmpty) {
          final endDt = DateTime.parse(endDateStr);
          final endFmt = '${endDt.day.toString().padLeft(2, '0')}/${endDt.month.toString().padLeft(2, '0')}/${endDt.year}';
          dateRange = 'Thứ 2, $startFmt – CN, $endFmt ($durationWeeks tuần)';
        } else {
          dateRange = 'Từ Thứ 2, $startFmt ($durationWeeks tuần)';
        }
      } catch (_) {}
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
        gradient: LinearGradient(
          colors: [
            AppTheme.primary.withValues(alpha: 0.08),
            AppTheme.surfaceDark,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.rocket_launch_rounded, color: AppTheme.primary, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        theme,
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.greenAccent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
                      ),
                      child: const Text('Đang thực thi', style: TextStyle(color: Colors.greenAccent, fontSize: 11, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                if (dateRange.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.calendar_month_outlined, size: 13, color: AppTheme.textMutedDark),
                      const SizedBox(width: 6),
                      Text(dateRange, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5)),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
