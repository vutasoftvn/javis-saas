import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class ScaleWarningDialog extends StatelessWidget {
  final String title;
  final String message;
  final String recommendation;
  final String recommendedAction;
  final VoidCallback onValidateFirst;
  final VoidCallback onContinueAnyway;

  const ScaleWarningDialog({
    super.key,
    required this.title,
    required this.message,
    required this.recommendation,
    required this.recommendedAction,
    required this.onValidateFirst,
    required this.onContinueAnyway,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.amberAccent.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.warning_amber_rounded, color: Colors.amberAccent, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            message,
            style: const TextStyle(fontSize: 13, color: AppTheme.textMutedDark, height: 1.4),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.lightbulb_outline_rounded, size: 18, color: AppTheme.primaryLight),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    recommendedAction,
                    style: TextStyle(fontSize: 12, color: AppTheme.primaryLight, height: 1.3),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: onContinueAnyway,
          child: const Text(
            'Bỏ qua & Tiếp tục (Continue Anyway)',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
          ),
        ),
        ElevatedButton.icon(
          onPressed: onValidateFirst,
          icon: const Icon(Icons.science_rounded, size: 16),
          label: const Text('Thử nghiệm trước (Validate First)'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
        ),
      ],
    );
  }
}
