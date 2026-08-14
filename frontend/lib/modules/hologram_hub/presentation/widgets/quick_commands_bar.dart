import 'dart:math' as math;

import 'package:flutter/material.dart';

class QuickCommandsBar extends StatelessWidget {
  final Function(String command) onCommandTap;

  const QuickCommandsBar({super.key, required this.onCommandTap});

  static const List<({String label, IconData icon})> _commands = [
    (label: 'Tổng quan hôm nay', icon: Icons.today_outlined),
    (label: 'Kiểm tra công việc', icon: Icons.task_alt_outlined),
    (label: 'Mở Kho tri thức', icon: Icons.auto_stories_outlined),
    (label: 'Báo cáo tài chính', icon: Icons.account_balance_wallet_outlined),
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isLandscape =
            MediaQuery.orientationOf(context) == Orientation.landscape;
        final screenWidth = MediaQuery.sizeOf(context).width;
        final showLabels = isLandscape || constraints.maxWidth > 900;
        final useCompactLabels =
            showLabels && (screenWidth < 1100 || constraints.maxWidth < 900);
        const minGap = 4.0;
        const maxGap = 24.0;
        const minButtonPadding = 4.0;
        const minRowHorizontalPadding = 0.0;
        const maxRowHorizontalPadding = 48.0;
        final maxButtonPadding = useCompactLabels ? 14.0 : 22.0;
        final labelStyle = TextStyle(
          color: const Color(0xFFCBD5E1),
          fontSize: 14,
          fontWeight: FontWeight.w600,
        );
        final textScaler = MediaQuery.textScalerOf(context);
        final labelledContentWidth = _commands.fold<double>(0, (sum, command) {
          return sum +
              16 +
              6 +
              _textWidth(context, command.label, labelStyle, textScaler);
        });
        final minimumLabelledRowWidth =
            labelledContentWidth +
            (_commands.length * minButtonPadding * 2) +
            ((_commands.length - 1) * minGap);
        final rowHorizontalPadding = math.min(
          maxRowHorizontalPadding,
          math.max(
            minRowHorizontalPadding,
            (constraints.maxWidth - minimumLabelledRowWidth) / 2,
          ),
        );
        final contentWidth = math.max(
          0.0,
          constraints.maxWidth - (rowHorizontalPadding * 2),
        );
        final displayLabels = showLabels;
        final horizontalPadding = displayLabels
            ? math.min(
                maxButtonPadding,
                math.max(
                  minButtonPadding,
                  (contentWidth -
                          labelledContentWidth -
                          ((_commands.length - 1) * minGap)) /
                      (_commands.length * 2),
                ),
              )
            : minButtonPadding;
        final renderedButtonsWidth = displayLabels
            ? labelledContentWidth + (_commands.length * horizontalPadding * 2)
            : _commands.length * (16 + horizontalPadding * 2);
        final buttonGap = math.min(
          maxGap,
          math.max(
            minGap,
            (contentWidth - renderedButtonsWidth) / (_commands.length - 1),
          ),
        );
        return Padding(
          padding: EdgeInsets.symmetric(horizontal: rowHorizontalPadding),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.center,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: _commands.indexed.expand((entry) {
                final index = entry.$1;
                final command = entry.$2;
                return [
                  _buildButton(
                    command,
                    showLabel: displayLabels,
                    compactLabel: useCompactLabels,
                    horizontalPadding: horizontalPadding,
                  ),
                  if (index != _commands.length - 1) SizedBox(width: buttonGap),
                ];
              }).toList(),
            ),
          ),
        );
      },
    );
  }

  double _textWidth(
    BuildContext context,
    String label,
    TextStyle style,
    TextScaler textScaler,
  ) {
    final painter = TextPainter(
      text: TextSpan(text: label, style: style),
      textDirection: Directionality.of(context),
      textScaler: textScaler,
    )..layout();
    return painter.width;
  }

  Widget _buildButton(
    ({String label, IconData icon}) command, {
    required bool showLabel,
    required bool compactLabel,
    required double horizontalPadding,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => onCommandTap(command.label),
        borderRadius: BorderRadius.circular(100),
        child: Container(
          padding: EdgeInsets.symmetric(
            horizontal: horizontalPadding,
            vertical: compactLabel ? 10 : 11,
          ),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A).withValues(alpha: 0.8),
            borderRadius: BorderRadius.circular(100),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(command.icon, size: 16, color: const Color(0xFF38BDF8)),
              if (showLabel) ...[
                SizedBox(width: compactLabel ? 4 : 6),
                Text(
                  command.label,
                  style: TextStyle(
                    color: Color(0xFFCBD5E1),
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
