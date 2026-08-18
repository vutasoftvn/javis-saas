import 'dart:math' as math;
import 'package:flutter/material.dart';

class AudioWaveformPainter extends CustomPainter {
  final double animationValue;
  final Color primaryColor;
  final Color secondaryColor;
  final int barCount;
  final bool isOscilloscope;

  AudioWaveformPainter({
    required this.animationValue,
    this.primaryColor = const Color(0xFF14B8A6),
    this.secondaryColor = const Color(0xFF3B82F6),
    this.barCount = 24,
    this.isOscilloscope = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (isOscilloscope) {
      _drawOscilloscope(canvas, size);
    } else {
      _drawBars(canvas, size);
    }
  }

  void _drawOscilloscope(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = LinearGradient(
        colors: [primaryColor.withValues(alpha: 0.2), primaryColor, secondaryColor],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final glowPaint = Paint()
      ..color = primaryColor.withValues(alpha: 0.35)
      ..strokeWidth = 5.0
      ..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

    final path = Path();
    final midY = size.height / 2;

    for (double x = 0; x <= size.width; x += 2) {
      final progress = x / size.width;
      final wave1 = math.sin((progress * 4 * math.pi) + (animationValue * 2 * math.pi)) * (size.height * 0.35);
      final wave2 = math.cos((progress * 7 * math.pi) - (animationValue * 3 * math.pi)) * (size.height * 0.15);
      final y = midY + wave1 + wave2;

      if (x == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, glowPaint);
    canvas.drawPath(path, paint);
  }

  void _drawBars(Canvas canvas, Size size) {
    final barWidth = (size.width / (barCount * 1.6)).clamp(2.0, 5.0);
    final gap = (size.width - (barCount * barWidth)) / (barCount - 1);
    final midY = size.height / 2;

    final paint = Paint()..style = PaintingStyle.fill;

    for (int i = 0; i < barCount; i++) {
      final x = i * (barWidth + gap);
      final normalizedPos = (i - barCount / 2).abs() / (barCount / 2);
      final freqMultiplier = 1.0 - (normalizedPos * 0.5);

      final phase = (i / barCount) * 2 * math.pi;
      final wave = (math.sin((animationValue * 2 * math.pi) + phase) + 1) / 2;
      final randomFactor = (math.sin(i * 13.5 + animationValue * 5) + 1) / 2;

      final barHeight = (size.height * 0.8 * (0.2 + 0.8 * wave * randomFactor) * freqMultiplier).clamp(4.0, size.height);

      final rect = RRect.fromRectAndRadius(
        Rect.fromCenter(
          center: Offset(x + barWidth / 2, midY),
          width: barWidth,
          height: barHeight,
        ),
        Radius.circular(barWidth / 2),
      );

      final gradient = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          primaryColor,
          secondaryColor,
        ],
      );

      paint.shader = gradient.createShader(rect.outerRect);
      canvas.drawRRect(rect, paint);
    }
  }

  @override
  bool shouldRepaint(covariant AudioWaveformPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue;
  }
}
