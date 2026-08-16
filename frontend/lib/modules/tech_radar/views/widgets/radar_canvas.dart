import 'dart:math';
import 'package:flutter/material.dart';

class RadarCanvas extends StatelessWidget {
  final List<Map<String, dynamic>> items;
  final Function(Map<String, dynamic>) onItemTap;

  const RadarCanvas({
    super.key,
    required this.items,
    required this.onItemTap,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = min(constraints.maxWidth, constraints.maxHeight);
        return Center(
          child: SizedBox(
            width: size,
            height: size,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CustomPaint(
                  size: Size(size, size),
                  painter: _RadarGridPainter(),
                ),
                ..._buildItemPointers(size),
              ],
            ),
          ),
        );
      },
    );
  }

  List<Widget> _buildItemPointers(double size) {
    final center = size / 2;
    final maxRadius = (size / 2) - 30;

    // Radius rings mapping
    // ADOPT: 0.15 - 0.35 * maxRadius
    // TRIAL: 0.40 - 0.60 * maxRadius
    // ASSESS: 0.65 - 0.80 * maxRadius
    // WATCH: 0.85 - 0.98 * maxRadius

    final List<Widget> widgets = [];

    for (int i = 0; i < items.length; i++) {
      final item = items[i];
      final status = (item['status']?.toString() ?? 'WATCH').toUpperCase();
      
      double minR = 0.85;
      double maxR = 0.98;
      Color color = const Color(0xFFA855F7); // purple

      if (status == 'ADOPT') {
        minR = 0.15;
        maxR = 0.35;
        color = const Color(0xFF10B981); // green
      } else if (status == 'TRIAL') {
        minR = 0.40;
        maxR = 0.60;
        color = const Color(0xFF00E5FF); // cyan
      } else if (status == 'ASSESS') {
        minR = 0.65;
        maxR = 0.80;
        color = const Color(0xFFF59E0B); // amber
      }

      // Hash deterministic angle
      final name = item['name']?.toString() ?? '$i';
      final hash = name.codeUnits.fold<int>(0, (prev, elem) => prev + elem) + (i * 37);
      final angle = (hash % 360) * (pi / 180);
      final radius = maxRadius * (minR + ((hash % 100) / 100.0) * (maxR - minR));

      final x = center + radius * cos(angle);
      final y = center + radius * sin(angle);

      widgets.add(
        Positioned(
          left: x - 12,
          top: y - 12,
          child: Tooltip(
            message: '${item['name']} [${item['category']}]\nStatus: $status | Maturity: ${item['maturity']}',
            child: InkWell(
              onTap: () => onItemTap(item),
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.25),
                  shape: BoxShape.circle,
                  border: Border.all(color: color, width: 1.5),
                  boxShadow: [
                    BoxShadow(
                      color: color.withValues(alpha: 0.4),
                      blurRadius: 6,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                child: Center(
                  child: Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }

    return widgets;
  }
}

class _RadarGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = (size.width / 2) - 30;

    final rings = [
      {'ratio': 0.35, 'label': 'ADOPT', 'color': const Color(0xFF10B981)},
      {'ratio': 0.60, 'label': 'TRIAL', 'color': const Color(0xFF00E5FF)},
      {'ratio': 0.80, 'label': 'ASSESS', 'color': const Color(0xFFF59E0B)},
      {'ratio': 0.98, 'label': 'WATCH', 'color': const Color(0xFFA855F7)},
    ];

    // Background circle glow
    final bgPaint = Paint()
      ..color = const Color(0xFF0D1527)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, maxRadius, bgPaint);

    // Crosshairs
    final linePaint = Paint()
      ..color = const Color(0xFF1E293B).withValues(alpha: 0.8)
      ..strokeWidth = 1;
    canvas.drawLine(Offset(center.dx - maxRadius, center.dy), Offset(center.dx + maxRadius, center.dy), linePaint);
    canvas.drawLine(Offset(center.dx, center.dy - maxRadius), Offset(center.dx, center.dy + maxRadius), linePaint);

    // Diagonal lines
    canvas.drawLine(
      Offset(center.dx - maxRadius * 0.707, center.dy - maxRadius * 0.707),
      Offset(center.dx + maxRadius * 0.707, center.dy + maxRadius * 0.707),
      linePaint,
    );
    canvas.drawLine(
      Offset(center.dx - maxRadius * 0.707, center.dy + maxRadius * 0.707),
      Offset(center.dx + maxRadius * 0.707, center.dy - maxRadius * 0.707),
      linePaint,
    );

    // Rings
    for (final ring in rings) {
      final r = maxRadius * (ring['ratio'] as double);
      final color = ring['color'] as Color;

      final ringPaint = Paint()
        ..color = color.withValues(alpha: 0.3)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2;

      canvas.drawCircle(center, r, ringPaint);

      // Label text
      final textSpan = TextSpan(
        text: ring['label'] as String,
        style: TextStyle(
          color: color.withValues(alpha: 0.85),
          fontSize: 10,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.5,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(center.dx - textPainter.width / 2, center.dy - r + 4));
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
