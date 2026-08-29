import 'package:flutter/material.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/glassmorphism.dart';

class TwelveWyPlanCard extends StatelessWidget {
  final dynamic plan;
  final StrategyController controller;
  final VoidCallback onReview;
  final VoidCallback onCompile;
  final VoidCallback onMission;
  final VoidCallback onAddCommitment;

  const TwelveWyPlanCard({
    super.key,
    required this.plan,
    required this.controller,
    required this.onReview,
    required this.onCompile,
    required this.onMission,
    required this.onAddCommitment,
  });

  @override
  Widget build(BuildContext context) {
    final planId = plan['id']?.toString() ?? '';
    final weekNo = plan['week_no'] ?? plan['week_number'] ?? 1;
    final focus = plan['focus'] ?? plan['theme'] ?? 'Trọng tâm tuần';
    final mission = plan['mission']?.toString();
    final outcomeScore = (plan['outcome_score'] as num?)?.toDouble();
    final commitments = controller.getCommitmentsForPlan(planId);

    final startDateStr = plan['start_date']?.toString();
    final endDateStr = plan['end_date']?.toString();

    String? dateRangeText;
    if (startDateStr != null && startDateStr.isNotEmpty) {
      try {
        final startDt = DateTime.parse(startDateStr);
        final endDt = (endDateStr != null && endDateStr.isNotEmpty)
            ? DateTime.parse(endDateStr)
            : startDt.add(const Duration(days: 6));
        final startFmt = '${startDt.day.toString().padLeft(2, '0')}/${startDt.month.toString().padLeft(2, '0')}';
        final endFmt = '${endDt.day.toString().padLeft(2, '0')}/${endDt.month.toString().padLeft(2, '0')}/${endDt.year}';
        dateRangeText = 'Thứ 2, $startFmt – CN, $endFmt';
      } catch (_) {}
    }

    return Glassmorphism(
      blur: 12,
      opacity: 0.12,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: const Border(
            left: BorderSide(color: AppTheme.accentLight, width: 4),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.accent.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text('TUẦN $weekNo', style: const TextStyle(color: AppTheme.accentLight, fontWeight: FontWeight.bold, fontSize: 12)),
                      ),
                      if (dateRangeText != null) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.calendar_today_outlined, size: 11, color: AppTheme.textMutedDark),
                              const SizedBox(width: 4),
                              Text(
                                dateRangeText,
                                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11, fontWeight: FontWeight.w500),
                              ),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          focus,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                Row(
                  children: [
                    TextButton.icon(
                      onPressed: onReview,
                      icon: const Icon(Icons.rate_review_outlined, size: 16, color: Colors.tealAccent),
                      label: const Text('Review', style: TextStyle(color: Colors.tealAccent)),
                    ),
                    const SizedBox(width: 4),
                    TextButton.icon(
                      onPressed: onCompile,
                      icon: const Icon(Icons.bolt_rounded, size: 16, color: Colors.amberAccent),
                      label: const Text('Compile', style: TextStyle(color: Colors.amberAccent)),
                    ),
                    const SizedBox(width: 4),
                    TextButton.icon(
                      onPressed: onMission,
                      icon: const Icon(Icons.flag_circle_rounded, size: 16, color: AppTheme.primaryLight),
                      label: const Text('Mission', style: TextStyle(color: AppTheme.primaryLight)),
                    ),
                    const SizedBox(width: 4),
                    TextButton.icon(
                      onPressed: onAddCommitment,
                      icon: const Icon(Icons.add_task_rounded, size: 16),
                      label: const Text('Cam kết', style: TextStyle(color: AppTheme.accentLight)),
                      style: TextButton.styleFrom(foregroundColor: AppTheme.accentLight),
                    ),
                  ],
                ),
              ],
            ),

            if (mission != null && mission.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.flag_rounded, size: 18, color: AppTheme.primaryLight),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Weekly Mission (Nhiệm vụ trọng điểm):', style: TextStyle(fontSize: 11, color: AppTheme.primaryLight, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 2),
                          Text(mission, style: const TextStyle(fontSize: 13, color: Colors.white)),
                        ],
                      ),
                    ),
                    if (outcomeScore != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: (outcomeScore >= 0.7 ? Colors.green : Colors.orange).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: outcomeScore >= 0.7 ? Colors.greenAccent : Colors.orangeAccent),
                        ),
                        child: Text(
                          'Outcome: ${(outcomeScore * 100).toInt()}%',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: outcomeScore >= 0.7 ? Colors.greenAccent : Colors.orangeAccent),
                        ),
                      ),
                  ],
                ),
              ),
            ],

            if (commitments.isNotEmpty) ...[
              const SizedBox(height: 12),
              ...commitments.map((c) {
                final isDone = c['status'] == 'done';
                final ownerType = c['commitment_owner_type'] ?? 'FOUNDER';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      Checkbox(
                        value: isDone,
                        activeColor: AppTheme.success,
                        onChanged: (_) => controller.toggleCommitmentStatus(c['id'], c['status'] ?? 'todo'),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: ownerType == 'AI_AGENT' ? Colors.cyan.withValues(alpha: 0.2) : Colors.purple.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: ownerType == 'AI_AGENT' ? Colors.cyanAccent.withValues(alpha: 0.5) : Colors.purpleAccent.withValues(alpha: 0.5)),
                        ),
                        child: Text(
                          ownerType,
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: ownerType == 'AI_AGENT' ? Colors.cyanAccent : Colors.purpleAccent),
                        ),
                      ),
                      Expanded(
                        child: Text(
                          c['title'] ?? '',
                          style: TextStyle(
                            color: isDone ? Colors.white38 : Colors.white,
                            decoration: isDone ? TextDecoration.lineThrough : null,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: () => controller.deleteWeeklyCommitment(c['id']),
                        icon: const Icon(Icons.close_rounded, size: 16, color: Colors.white24),
                        splashRadius: 14,
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
