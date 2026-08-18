import 'package:flutter/material.dart';
import '../../data/models/evidence_model.dart';

class EvidenceLadderBadge extends StatelessWidget {
  final EvidenceLadderLevel level;
  final bool isCompact;
  final bool showFullTitle;

  const EvidenceLadderBadge({
    super.key,
    required this.level,
    this.isCompact = false,
    this.showFullTitle = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = level.color;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? 6.0 : 10.0,
        vertical: isCompact ? 2.5 : 4.5,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withValues(alpha: 0.45),
          width: 1.0,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            level.code,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: isCompact ? 10 : 11,
              letterSpacing: 0.5,
            ),
          ),
          if (!isCompact || showFullTitle) ...[
            Text(
              ' • ${showFullTitle ? level.titleVi : level.shortLabelVi}',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.85),
                fontSize: isCompact ? 10 : 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
