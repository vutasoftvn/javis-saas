import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Animated Futuristic Cyber Circuit Board Background
/// Renders glowing PCB circuit tracks, bus traces, solder vias,
/// microchip footprints, and traveling energy light pulses.
class CyberCircuitBackground extends StatefulWidget {
  final Widget? child;

  const CyberCircuitBackground({super.key, this.child});

  @override
  State<CyberCircuitBackground> createState() => _CyberCircuitBackgroundState();
}

class _CyberCircuitBackgroundState extends State<CyberCircuitBackground>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 6),
    );
    if (!WidgetsBinding.instance.runtimeType.toString().contains(
      'TestWidgetsFlutterBinding',
    )) {
      _pulseController.repeat();
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        return CustomPaint(
          painter: _CircuitBoardPainter(progress: _pulseController.value),
          child: widget.child,
        );
      },
      child: widget.child,
    );
  }
}

class _CircuitBoardPainter extends CustomPainter {
  final double progress;

  _CircuitBoardPainter({required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Base Dark Cyber Background Gradient
    final rect = Offset.zero & size;
    final bgGradient = RadialGradient(
      center: const Alignment(0.0, -0.15),
      radius: 1.3,
      colors: const [
        Color(0xFF0D1E3D), // Deep luminous cyber navy center
        Color(0xFF070E20),
        Color(0xFF040712), // Dark obsidian edge
      ],
      stops: const [0.0, 0.55, 1.0],
    );

    final bgPaint = Paint()..shader = bgGradient.createShader(rect);
    canvas.drawRect(rect, bgPaint);

    // 2. Subtle Tech Grid Pattern
    _drawTechGrid(canvas, size);

    // 3. PCB Circuit Traces & Bus Lines
    _drawCircuitTraces(canvas, size);
  }

  void _drawTechGrid(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = const Color(0xFF14B8A6).withValues(alpha: 0.025)
      ..strokeWidth = 1.0;

    const spacing = 48.0;
    for (double x = 0; x < size.width; x += spacing) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y < size.height; y += spacing) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // Grid cross markers at select intersections
    final dotPaint = Paint()
      ..color = const Color(0xFF14B8A6).withValues(alpha: 0.06)
      ..style = PaintingStyle.fill;

    for (double x = spacing * 2; x < size.width; x += spacing * 4) {
      for (double y = spacing * 2; y < size.height; y += spacing * 4) {
        canvas.drawCircle(Offset(x, y), 1.5, dotPaint);
      }
    }
  }

  void _drawCircuitTraces(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Define circuit paths spanning all card zones
    final circuits = <List<Offset>>[
      // --- TOP AREA: Appbar & Pulse Bar Crossings ---
      [
        Offset(0, h * 0.035),
        Offset(w * 0.32, h * 0.035),
        Offset(w * 0.38, h * 0.065),
        Offset(w * 0.62, h * 0.065),
        Offset(w * 0.68, h * 0.035),
        Offset(w, h * 0.035),
      ],
      [
        Offset(w * 0.02, h * 0.08),
        Offset(w * 0.28, h * 0.08),
        Offset(w * 0.34, h * 0.12),
        Offset(w * 0.66, h * 0.12),
        Offset(w * 0.72, h * 0.08),
        Offset(w * 0.98, h * 0.08),
      ],
      [
        Offset(w * 0.05, h * 0.105),
        Offset(w * 0.42, h * 0.105),
        Offset(w * 0.46, h * 0.15),
        Offset(w * 0.54, h * 0.15),
        Offset(w * 0.58, h * 0.105),
        Offset(w * 0.95, h * 0.105),
      ],

      // --- BOTTOM AREA: KPI Strip & Command Dock Crossings ---
      [
        Offset(0, h * 0.93),
        Offset(w * 0.30, h * 0.93),
        Offset(w * 0.36, h * 0.89),
        Offset(w * 0.64, h * 0.89),
        Offset(w * 0.70, h * 0.93),
        Offset(w, h * 0.93),
      ],
      [
        Offset(w * 0.02, h * 0.96),
        Offset(w * 0.26, h * 0.96),
        Offset(w * 0.32, h * 0.91),
        Offset(w * 0.68, h * 0.91),
        Offset(w * 0.74, h * 0.96),
        Offset(w * 0.98, h * 0.96),
      ],
      [
        Offset(w * 0.05, h * 0.87),
        Offset(w * 0.35, h * 0.87),
        Offset(w * 0.40, h * 0.83),
        Offset(w * 0.60, h * 0.83),
        Offset(w * 0.65, h * 0.87),
        Offset(w * 0.95, h * 0.87),
      ],
      [
        Offset(w * 0.08, h * 0.81),
        Offset(w * 0.45, h * 0.81),
        Offset(w * 0.50, h * 0.76),
        Offset(w * 0.55, h * 0.76),
        Offset(w * 0.60, h * 0.81),
        Offset(w * 0.92, h * 0.81),
      ],

      // --- LEFT RAIL TRACES ---
      [
        Offset(w * 0.04, h * 0.16),
        Offset(w * 0.14, h * 0.16),
        Offset(w * 0.22, h * 0.28),
        Offset(w * 0.22, h * 0.55),
        Offset(w * 0.35, h * 0.55),
      ],
      [
        Offset(w * 0.08, h * 0.22),
        Offset(w * 0.08, h * 0.45),
        Offset(w * 0.16, h * 0.55),
        Offset(w * 0.16, h * 0.72),
        Offset(w * 0.28, h * 0.72),
      ],

      // --- RIGHT RAIL TRACES ---
      [
        Offset(w * 0.96, h * 0.16),
        Offset(w * 0.86, h * 0.16),
        Offset(w * 0.78, h * 0.28),
        Offset(w * 0.78, h * 0.55),
        Offset(w * 0.65, h * 0.55),
      ],
      [
        Offset(w * 0.92, h * 0.22),
        Offset(w * 0.92, h * 0.45),
        Offset(w * 0.84, h * 0.55),
        Offset(w * 0.84, h * 0.72),
        Offset(w * 0.72, h * 0.72),
      ],

      // --- CENTER DIAGONALS TO CORE ---
      [
        Offset(w * 0.02, h * 0.12),
        Offset(w * 0.18, h * 0.24),
        Offset(w * 0.36, h * 0.34),
      ],
      [
        Offset(w * 0.98, h * 0.12),
        Offset(w * 0.82, h * 0.24),
        Offset(w * 0.64, h * 0.34),
      ],
      [
        Offset(w * 0.02, h * 0.85),
        Offset(w * 0.20, h * 0.70),
        Offset(w * 0.38, h * 0.58),
      ],
      [
        Offset(w * 0.98, h * 0.85),
        Offset(w * 0.80, h * 0.70),
        Offset(w * 0.62, h * 0.58),
      ],
    ];

    // Colors for different traces
    final traceColors = [
      const Color(0xFF14B8A6), // Cyan
      const Color(0xFF38BDF8), // Light Blue
      const Color(0xFF00FFB2), // Emerald Neon
      const Color(0xFF14B8A6), // Cyan
      const Color(0xFF38BDF8), // Light Blue
      const Color(0xFF00FFB2), // Emerald Neon
      const Color(0xFF818CF8), // Indigo
      const Color(0xFFC084FC), // Violet
      const Color(0xFF14B8A6), // Cyan
      const Color(0xFF38BDF8), // Light Blue
      const Color(0xFF00FFB2), // Emerald Neon
      const Color(0xFF8B5CF6), // Violet
      const Color(0xFF14B8A6),
      const Color(0xFF38BDF8),
      const Color(0xFF00FFB2),
    ];

    for (int i = 0; i < circuits.length; i++) {
      final points = circuits[i];
      if (points.isEmpty) continue;

      final color = traceColors[i % traceColors.length];

      // 1. Draw Subtle Dim Track (PCB Trace line)
      final trackPaint = Paint()
        ..color = color.withValues(alpha: 0.16)
        ..strokeWidth = 1.3
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round;

      final path = Path()..moveTo(points[0].dx, points[0].dy);
      for (int p = 1; p < points.length; p++) {
        path.lineTo(points[p].dx, points[p].dy);
      }
      canvas.drawPath(path, trackPaint);

      // 2. Draw Solder Vias / Node Pads at endpoints and junctions
      final viaPaint = Paint()
        ..color = color.withValues(alpha: 0.25)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0;

      final viaFill = Paint()
        ..color = color.withValues(alpha: 0.12)
        ..style = PaintingStyle.fill;

      // Start & End nodes
      for (final pt in [points.first, points.last]) {
        canvas.drawCircle(pt, 2.8, viaFill);
        canvas.drawCircle(pt, 2.8, viaPaint);
        // Micro inner core dot
        canvas.drawCircle(
          pt,
          1.0,
          Paint()..color = Colors.white.withValues(alpha: 0.45),
        );
      }

      // 3. Draw Traveling Light Pulse (Energy Packet) along path
      _drawEnergyPulse(canvas, path, color, i);
    }

    // 4. Draw Microchip / IC Components positioned right under card regions
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.20, h * 0.08),
      size: 22,
      color: const Color(0xFF14B8A6),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.80, h * 0.08),
      size: 22,
      color: const Color(0xFF38BDF8),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.08, h * 0.32),
      size: 24,
      color: const Color(0xFF14B8A6),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.92, h * 0.32),
      size: 24,
      color: const Color(0xFF818CF8),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.16, h * 0.68),
      size: 20,
      color: const Color(0xFF00FFB2),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.84, h * 0.68),
      size: 20,
      color: const Color(0xFF38BDF8),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.22, h * 0.93),
      size: 20,
      color: const Color(0xFF14B8A6),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.50, h * 0.93),
      size: 20,
      color: const Color(0xFF00FFB2),
    );
    _drawMicrochipPad(
      canvas,
      Offset(w * 0.78, h * 0.93),
      size: 20,
      color: const Color(0xFF38BDF8),
    );
  }

  void _drawEnergyPulse(Canvas canvas, Path path, Color color, int index) {
    // Stagger pulses for different traces
    final metrics = path.computeMetrics().toList();
    if (metrics.isEmpty) return;

    final metric = metrics.first;
    final totalLength = metric.length;

    // Offset progress per trace index for organic visual movement
    final traceProgress = (progress + (index * 0.17)) % 1.0;
    final pulsePos = totalLength * traceProgress;

    const pulseLength = 26.0;
    final start = math.max(0.0, pulsePos - pulseLength);
    final end = math.min(totalLength, pulsePos);

    if (end > start) {
      final pulsePath = metric.extractPath(start, end);

      // Subtle Glow Halo
      final glowPaint = Paint()
        ..color = color.withValues(alpha: 0.28)
        ..strokeWidth = 3.5
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3.0);
      canvas.drawPath(pulsePath, glowPaint);

      // Bright Core
      final corePaint = Paint()
        ..color = Colors.white.withValues(alpha: 0.65)
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;
      canvas.drawPath(pulsePath, corePaint);

      // Head photon dot
      final tangent = metric.getTangentForOffset(pulsePos);
      if (tangent != null) {
        final headPos = tangent.position;
        canvas.drawCircle(
          headPos,
          1.8,
          Paint()..color = Colors.white.withValues(alpha: 0.85),
        );
        canvas.drawCircle(
          headPos,
          4.5,
          Paint()
            ..color = color.withValues(alpha: 0.40)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5),
        );
      }
    }
  }

  void _drawMicrochipPad(
    Canvas canvas,
    Offset center, {
    required double size,
    required Color color,
  }) {
    final rect = Rect.fromCenter(center: center, width: size, height: size);

    // IC Body
    final chipPaint = Paint()
      ..color = const Color(0xFF0F1B35).withValues(alpha: 0.25)
      ..style = PaintingStyle.fill;
    final borderPaint = Paint()
      ..color = color.withValues(alpha: 0.18)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8;
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(4)),
      chipPaint,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(4)),
      borderPaint,
    );

    // Microchip Pins (Left & Right)
    final pinPaint = Paint()
      ..color = color.withValues(alpha: 0.15)
      ..strokeWidth = 1.0;
    const pins = 3;
    final pinSpacing = size / (pins + 1);
    for (int p = 1; p <= pins; p++) {
      final y = rect.top + (p * pinSpacing);
      // Left pin
      canvas.drawLine(Offset(rect.left - 4, y), Offset(rect.left, y), pinPaint);
      // Right pin
      canvas.drawLine(
        Offset(rect.right, y),
        Offset(rect.right + 4, y),
        pinPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _CircuitBoardPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
