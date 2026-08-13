import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

/// Shared HUD-style bordered card used across the Hologram Hub panels
/// (system health, memory core, agents, build mode).
Widget hudCard({
  required Widget child,
  VoidCallback? onTap,
}) {
  if (onTap != null) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: AppTheme.hudCardDecoration,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: child,
          ),
        ),
      ),
    );
  }

  return Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.all(14),
    decoration: AppTheme.hudCardDecoration,
    child: child,
  );
}

Widget hudCardHeader({
  required String title,
  required String badgeText,
  Color badgeColor = AppTheme.success,
}) {
  return Row(
    mainAxisAlignment: MainAxisAlignment.spaceBetween,
    children: [
      Expanded(
        child: Text(
          title,
          overflow: TextOverflow.ellipsis,
          maxLines: 1,
          style: const TextStyle(
            color: AppTheme.textDark,
            fontSize: 12.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
          ),
        ),
      ),
      const SizedBox(width: 8),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: badgeColor.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: badgeColor.withValues(alpha: 0.4),
            width: 0.8,
          ),
        ),
        child: Text(
          badgeText,
          style: TextStyle(
            color: badgeColor,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.8,
          ),
        ),
      ),
    ],
  );
}
