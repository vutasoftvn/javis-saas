import 'package:flutter/material.dart';

enum ExecutionModeType {
  autonomousSafe,
  approvedWorkflow,
  interactive,
}

class ExecutionModeBadge extends StatelessWidget {
  final ExecutionModeType mode;
  final ValueChanged<ExecutionModeType>? onModeChanged;
  final bool isCavemanMode;
  final ValueChanged<bool>? onCavemanModeToggled;

  const ExecutionModeBadge({
    super.key,
    this.mode = ExecutionModeType.interactive,
    this.onModeChanged,
    this.isCavemanMode = false,
    this.onCavemanModeToggled,
  });

  Color _getModeColor() {
    switch (mode) {
      case ExecutionModeType.autonomousSafe:
        return const Color(0xFF10B981); // Emerald Green
      case ExecutionModeType.approvedWorkflow:
        return const Color(0xFFF59E0B); // Amber Yellow
      case ExecutionModeType.interactive:
        return const Color(0xFF3B82F6); // Electric Blue
    }
  }

  String _getModeLabel() {
    switch (mode) {
      case ExecutionModeType.autonomousSafe:
        return 'AUTONOMOUS SAFE';
      case ExecutionModeType.approvedWorkflow:
        return 'APPROVED WORKFLOW';
      case ExecutionModeType.interactive:
        return 'INTERACTIVE';
    }
  }

  IconData _getModeIcon() {
    switch (mode) {
      case ExecutionModeType.autonomousSafe:
        return Icons.shield_rounded;
      case ExecutionModeType.approvedWorkflow:
        return Icons.verified_user_rounded;
      case ExecutionModeType.interactive:
        return Icons.touch_app_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _getModeColor();

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        PopupMenuButton<dynamic>(
          initialValue: mode,
          onSelected: (val) {
            if (val is ExecutionModeType) {
              onModeChanged?.call(val);
            } else if (val == 'toggle_caveman') {
              onCavemanModeToggled?.call(!isCavemanMode);
            }
          },
          tooltip: 'Execution & Optimization Mode',
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
          ),
          itemBuilder: (ctx) => [
            const PopupMenuItem(
              value: ExecutionModeType.interactive,
              child: Row(
                children: [
                  Icon(Icons.touch_app_rounded, color: Color(0xFF3B82F6), size: 18),
                  SizedBox(width: 8),
                  Text('Interactive (Confirm external)', style: TextStyle(color: Colors.white, fontSize: 13)),
                ],
              ),
            ),
            const PopupMenuItem(
              value: ExecutionModeType.approvedWorkflow,
              child: Row(
                children: [
                  Icon(Icons.verified_user_rounded, color: Color(0xFFF59E0B), size: 18),
                  SizedBox(width: 8),
                  Text('Approved Workflow (Auto-run)', style: TextStyle(color: Colors.white, fontSize: 13)),
                ],
              ),
            ),
            const PopupMenuItem(
              value: ExecutionModeType.autonomousSafe,
              child: Row(
                children: [
                  Icon(Icons.shield_rounded, color: Color(0xFF10B981), size: 18),
                  SizedBox(width: 8),
                  Text('Autonomous Safe (Read only)', style: TextStyle(color: Colors.white, fontSize: 13)),
                ],
              ),
            ),
            const PopupMenuDivider(height: 8),
            PopupMenuItem(
              value: 'toggle_caveman',
              child: Row(
                children: [
                  Icon(
                    isCavemanMode ? Icons.flash_on_rounded : Icons.flash_off_rounded,
                    color: isCavemanMode ? const Color(0xFFF59E0B) : Colors.grey,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    isCavemanMode ? 'Caveman Mode: ON (-65% output)' : 'Caveman Mode: OFF',
                    style: TextStyle(
                      color: isCavemanMode ? const Color(0xFFF59E0B) : Colors.white70,
                      fontSize: 13,
                      fontWeight: isCavemanMode ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ],
              ),
            ),
          ],
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: color.withValues(alpha: 0.4), width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(_getModeIcon(), color: color, size: 14),
                const SizedBox(width: 6),
                Text(
                  _getModeLabel(),
                  style: TextStyle(
                    color: color,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(width: 4),
                Icon(Icons.arrow_drop_down, color: color.withValues(alpha: 0.7), size: 16),
              ],
            ),
          ),
        ),
        if (isCavemanMode) ...[
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.4)),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.bolt_rounded, color: Color(0xFFF59E0B), size: 12),
                SizedBox(width: 2),
                Text(
                  'CAVEMAN',
                  style: TextStyle(
                    color: Color(0xFFF59E0B),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
