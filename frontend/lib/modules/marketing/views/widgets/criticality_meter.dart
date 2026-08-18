import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class CriticalityMeter extends StatelessWidget {
  final int score; // 1 - 25
  final int impact;
  final int uncertainty;
  final bool showFormula;

  const CriticalityMeter({
    super.key,
    required this.score,
    this.impact = 3,
    this.uncertainty = 3,
    this.showFormula = false,
  });

  @override
  Widget build(BuildContext context) {
    Color color;
    String label;
    IconData icon;

    if (score >= 15) {
      color = AppTheme.error;
      label = 'Critical';
      icon = Icons.warning_amber_rounded;
    } else if (score >= 7) {
      color = Colors.amberAccent;
      label = 'Moderate';
      icon = Icons.bolt_rounded;
    } else {
      color = AppTheme.success;
      label = 'Low';
      icon = Icons.check_circle_outline_rounded;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            '$score/25 $label',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          if (showFormula) ...[
            const SizedBox(width: 4),
            Text(
              '($impact×$uncertainty)',
              style: TextStyle(
                fontSize: 10,
                color: color.withValues(alpha: 0.7),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
