import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class EpistemicBadge extends StatelessWidget {
  final String status;
  final bool isCompact;

  const EpistemicBadge({
    super.key,
    required this.status,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    final cleanStatus = status.toLowerCase().replaceAll(' ', '_');
    Color bg;
    Color fg;
    String label;
    IconData icon;

    switch (cleanStatus) {
      case 'evidence_backed':
      case 'supported':
        bg = AppTheme.success.withValues(alpha: 0.15);
        fg = AppTheme.success;
        label = 'Evidence-backed';
        icon = Icons.verified_rounded;
        break;
      case 'testing':
        bg = Colors.blueAccent.withValues(alpha: 0.15);
        fg = Colors.blueAccent;
        label = 'Testing';
        icon = Icons.science_rounded;
        break;
      case 'partially_supported':
        bg = Colors.tealAccent.withValues(alpha: 0.15);
        fg = Colors.tealAccent;
        label = 'Partially Supported';
        icon = Icons.rule_rounded;
        break;
      case 'contradicted':
        bg = AppTheme.error.withValues(alpha: 0.15);
        fg = AppTheme.error;
        label = 'Contradicted';
        icon = Icons.gpp_bad_rounded;
        break;
      case 'hypothesis':
      case 'assumption':
        bg = Colors.amberAccent.withValues(alpha: 0.15);
        fg = Colors.amberAccent;
        label = 'Hypothesis';
        icon = Icons.lightbulb_outline_rounded;
        break;
      case 'draft':
      case 'untested':
      default:
        bg = Colors.grey.withValues(alpha: 0.15);
        fg = Colors.grey.shade400;
        label = cleanStatus == 'untested' ? 'Untested' : 'Draft';
        icon = Icons.edit_note_rounded;
        break;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? 6 : 8,
        vertical: isCompact ? 2 : 4,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: fg.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: isCompact ? 12 : 14, color: fg),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: isCompact ? 11 : 12,
              fontWeight: FontWeight.w600,
              color: fg,
            ),
          ),
        ],
      ),
    );
  }
}
