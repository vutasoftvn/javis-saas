import 'package:flutter/material.dart';
import '../../data/models/stage_model.dart';

class StageBadge extends StatelessWidget {
  final ProjectStage stage;
  final bool showFullName;
  final bool isCompact;
  final VoidCallback? onTap;

  const StageBadge({
    super.key,
    required this.stage,
    this.showFullName = false,
    this.isCompact = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = stage.primaryColor;
    final gradient = stage.gradientColors;

    final badgeContent = Container(
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? 8.0 : 12.0,
        vertical: isCompact ? 3.0 : 6.0,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            gradient.first.withValues(alpha: 0.25),
            gradient.last.withValues(alpha: 0.12),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: color.withValues(alpha: 0.55),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.15),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            stage.icon,
            size: isCompact ? 13 : 16,
            color: color,
          ),
          const SizedBox(width: 6),
          Text(
            stage.code,
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: isCompact ? 11 : 12,
              letterSpacing: 0.5,
            ),
          ),
          if (showFullName) ...[
            Text(
              ' • ${stage.shortNameVi}',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.9),
                fontSize: isCompact ? 11 : 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );

    if (onTap != null) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: badgeContent,
        ),
      );
    }

    return Tooltip(
      message: '${stage.displayNameVi}\nBấm để xem chính sách quản trị',
      child: badgeContent,
    );
  }
}
