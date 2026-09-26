import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Animated Futuristic Cyber Trống Đồng Centerpiece Background
/// Focuses exclusively on the sacred Vietnamese Bronze Drum (Trống Đồng Đông Sơn) in the center:
/// - A glowing rotating quantum drum core with breathing gold & cyan aura.
/// - Concentric holographic rings hugging the drum's sacred geometric bands.
/// - Rotating Sacred Thái Cực Âm Dương (Yin-Yang) core rotating counter-clockwise at the center.
/// - Counter-rotating holographic HUD arcs and orbiting photon energy nodes around the drum rim.
/// - Clean dark ambient cosmic background with no outer distracting peripheral LED lines.
class CyberCircuitBackground extends StatefulWidget {
  final Widget? child;

  const CyberCircuitBackground({super.key, this.child});

  @override
  State<CyberCircuitBackground> createState() => _CyberCircuitBackgroundState();
}

class _CyberCircuitBackgroundState extends State<CyberCircuitBackground>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _rotationController;

  @override
  void initState() {
    super.initState();
    // Pulse controller for heartbeat and solar ripple waves (4.0s)
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 4000),
    );

    // Majestic slow rotation for the Trống Đồng drum and quantum rings (120s)
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 120),
    );

    if (!WidgetsBinding.instance.runtimeType.toString().contains('TestWidgetsFlutterBinding')) {
      _pulseController.repeat();
      _rotationController.repeat();
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rotationController.dispose();
    super.dispose();
  }

  Widget _buildTrongDongImage() {
    const assetPath = 'assets/images/trongdong.png';
    return Image.asset(
      assetPath,
      fit: BoxFit.contain,
      errorBuilder: (context, error, stackTrace) {
        // Fallback to absolute file path if asset isn't mounted yet
        try {
          final absFile = File('/Volumes/SSD/DEV/miva/trongdong.png');
          if (absFile.existsSync()) {
            return Image.file(absFile, fit: BoxFit.contain);
          }
        } catch (_) {}
        return const SizedBox.shrink();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final h = constraints.maxHeight;
        // Drum size fits comfortably inside the 6/12 center column
        final drumSize = math.min(w * 0.46, h * 0.82).clamp(380.0, 780.0);

        return Stack(
          fit: StackFit.expand,
          children: [
            // 1. Ambient Deep Cyber Cosmic Gradient
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, _) {
                return CustomPaint(
                  painter: _SpaceAmbientPainter(pulseProgress: _pulseController.value),
                );
              },
            ),

            // 2. Sacred Rotating Thái Cực Âm Dương Core (Positioned BEHIND Trống Đồng)
            AnimatedBuilder(
              animation: Listenable.merge([_pulseController, _rotationController]),
              builder: (context, _) {
                return CustomPaint(
                  painter: _TaijiCoreBackgroundPainter(
                    pulseProgress: _pulseController.value,
                    rotationProgress: _rotationController.value,
                    drumRadius: drumSize / 2,
                  ),
                );
              },
            ),

            // 3. The Sacred Trống Đồng Holographic Drum Centerpiece (Overlays on top of Thái Cực)
            AnimatedBuilder(
              animation: Listenable.merge([_pulseController, _rotationController]),
              builder: (context, _) {
                final pulse = math.sin(_pulseController.value * 2 * math.pi) * 0.5 + 0.5;
                final opacity = 0.58 + (pulse * 0.18); // Highly visible & luminous (0.58 -> 0.76)
                final scale = 1.0 + (pulse * 0.012);

                return Center(
                  child: Transform.rotate(
                    angle: _rotationController.value * 2 * math.pi,
                    child: Transform.scale(
                      scale: scale,
                      child: Opacity(
                        opacity: opacity,
                        child: Container(
                          width: drumSize,
                          height: drumSize,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFFE5A93C).withValues(alpha: 0.28 + pulse * 0.16),
                                blurRadius: 45 + pulse * 20,
                                spreadRadius: 2,
                              ),
                              BoxShadow(
                                color: const Color(0xFF00F0FF).withValues(alpha: 0.20 + pulse * 0.14),
                                blurRadius: 60 + pulse * 25,
                                spreadRadius: 1,
                              ),
                              BoxShadow(
                                color: const Color(0xFFD97706).withValues(alpha: 0.14),
                                blurRadius: 90,
                                spreadRadius: 4,
                              ),
                            ],
                          ),
                          child: _buildTrongDongImage(),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),

            // 4. Concentric Drum Hologram Rings & Orbiting Photons Overlay (On top of Trống Đồng)
            AnimatedBuilder(
              animation: Listenable.merge([_pulseController, _rotationController]),
              builder: (context, _) {
                return CustomPaint(
                  painter: _HolographicLedRingsOverlayPainter(
                    pulseProgress: _pulseController.value,
                    rotationProgress: _rotationController.value,
                    drumRadius: drumSize / 2,
                  ),
                );
              },
            ),

            // 4. Foreground Content (Cards & Chat)
            if (widget.child != null) widget.child!,
          ],
        );
      },
    );
  }
}

/// Paints the deep cosmic navy background with subtle ambient radial glow
class _SpaceAmbientPainter extends CustomPainter {
  final double pulseProgress;

  _SpaceAmbientPainter({required this.pulseProgress});

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final pulse = math.sin(pulseProgress * 2 * math.pi) * 0.5 + 0.5;

    // Deep luminous cyber space background
    final bgGradient = RadialGradient(
      center: const Alignment(0.0, 0.0),
      radius: 1.15,
      colors: [
        Color.lerp(const Color(0xFF0C1D3F), const Color(0xFF112957), pulse)!,
        const Color(0xFF060D1E),
        const Color(0xFF03060F),
      ],
      stops: const [0.0, 0.62, 1.0],
    );

    final bgPaint = Paint()..shader = bgGradient.createShader(rect);
    canvas.drawRect(rect, bgPaint);
  }

  @override
  bool shouldRepaint(covariant _SpaceAmbientPainter oldDelegate) {
    return oldDelegate.pulseProgress != pulseProgress;
  }
}

/// Paints Central Rotating Thái Cực Âm Dương (Yin-Yang) Core situated BEHIND Trống Đồng
class _TaijiCoreBackgroundPainter extends CustomPainter {
  final double pulseProgress;
  final double rotationProgress;
  final double drumRadius;

  _TaijiCoreBackgroundPainter({
    required this.pulseProgress,
    required this.rotationProgress,
    required this.drumRadius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    _drawCenterTaijiCore(canvas, center);
  }

  void _drawCenterTaijiCore(Canvas canvas, Offset center) {
    final pulse = math.sin(pulseProgress * 2 * math.pi) * 0.5 + 0.5;

    // Taiji radius scaled to peek beautifully through the star rays behind Trống Đồng
    final taijiRadius = (drumRadius * 0.175).clamp(42.0, 72.0);

    // 1. Expanding Solar Sonar Ripple Waves from the Thái Cực core across the drum face
    for (int i = 0; i < 4; i++) {
      final ringProgress = (pulseProgress + (i * 0.25)) % 1.0;
      final currentRadius = taijiRadius + (ringProgress * (drumRadius * 0.92 - taijiRadius));
      final ringOpacity = (1.0 - ringProgress) * 0.22;

      final waveColor = (i % 2 == 0) ? const Color(0xFFE5A93C) : const Color(0xFF00F0FF);
      final wavePaint = Paint()
        ..color = waveColor.withValues(alpha: ringOpacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2;
      canvas.drawCircle(center, currentRadius, wavePaint);
    }

    // 2. Soft Ambient Glow & Aura around the Thái Cực sphere
    final auraPaint = Paint()
      ..color = const Color(0xFFE5A93C).withValues(alpha: 0.18 + pulse * 0.10)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 18.0 + pulse * 6.0);
    canvas.drawCircle(center, taijiRadius + 4.0, auraPaint);

    final cyanAuraPaint = Paint()
      ..color = const Color(0xFF00F0FF).withValues(alpha: 0.12 + pulse * 0.08)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 28.0);
    canvas.drawCircle(center, taijiRadius + 12.0, cyanAuraPaint);

    // 3. Render Sacred Thái Cực Âm Dương (Rotating Counter-Clockwise / Ngược chiều kim đồng hồ)
    canvas.save();
    canvas.translate(center.dx, center.dy);

    // Counter-clockwise rotation: negative angle
    // Speed: 3x base rotation controller (1 full counter-clockwise revolution every 40s)
    final counterClockwiseAngle = -rotationProgress * 2 * math.pi * 3.0;
    canvas.rotate(counterClockwiseAngle);

    final r = taijiRadius;
    final rLobe = r / 2;
    final rEye = r * 0.16;

    // Softer global layer opacity: hòa quyện êm dịu, phản chiếu phía sau mặt trống
    final layerAlpha = 0.65 + (pulse * 0.15); // Nhạt dịu và thanh thoát (0.65 -> 0.80)
    final layerRect = Rect.fromCircle(center: Offset.zero, radius: r + 4.0);
    canvas.saveLayer(layerRect, Paint()..color = Colors.white.withValues(alpha: layerAlpha));

    // Muted, elegant palette (tông màu nhạt, thanh thoát):
    // Yang (Dương - Muted Champagne Ivory, ánh ngà ấm dịu)
    const yangColor = Color(0xFFF6EEDD);
    // Yin (Âm - Muted Midnight Slate Navy, trầm nhẹ thanh tao)
    const yinColor = Color(0xFF16253B);
    // Sacred Bronze Gold
    const goldColor = Color(0xFFE5A93C);

    // 1. Base circle: Yin (Muted Midnight Slate)
    canvas.drawCircle(
      Offset.zero,
      r,
      Paint()
        ..color = yinColor
        ..style = PaintingStyle.fill,
    );

    // 2. Yang half: Right semicircle from -pi/2 to pi/2
    canvas.drawArc(
      Rect.fromCircle(center: Offset.zero, radius: r),
      -math.pi / 2,
      math.pi,
      true,
      Paint()
        ..color = yangColor
        ..style = PaintingStyle.fill,
    );

    // 3. Top lobe of Yang: circle at (0, -rLobe) with radius rLobe
    canvas.drawCircle(
      Offset(0, -rLobe),
      rLobe,
      Paint()
        ..color = yangColor
        ..style = PaintingStyle.fill,
    );

    // 4. Bottom lobe of Yin: circle at (0, rLobe) with radius rLobe
    canvas.drawCircle(
      Offset(0, rLobe),
      rLobe,
      Paint()
        ..color = yinColor
        ..style = PaintingStyle.fill,
    );

    // 5. Fine S-curve separator stroke for delicate definition
    final sCurvePaint = Paint()
      ..color = goldColor.withValues(alpha: 0.70)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    // Top lobe left arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(0, -rLobe), radius: rLobe),
      math.pi / 2,
      math.pi,
      false,
      sCurvePaint,
    );
    // Bottom lobe right arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(0, rLobe), radius: rLobe),
      -math.pi / 2,
      math.pi,
      false,
      sCurvePaint,
    );

    // 6. Fish eyes (Mắt Thái Cực):
    // Yin eye inside Yang top lobe (at 0, -rLobe)
    canvas.drawCircle(
      Offset(0, -rLobe),
      rEye,
      Paint()
        ..color = yinColor
        ..style = PaintingStyle.fill,
    );
    canvas.drawCircle(
      Offset(0, -rLobe),
      rEye,
      Paint()
        ..color = goldColor.withValues(alpha: 0.80)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.9,
    );

    // Yang eye inside Yin bottom lobe (at 0, rLobe)
    canvas.drawCircle(
      Offset(0, rLobe),
      rEye,
      Paint()
        ..color = yangColor
        ..style = PaintingStyle.fill,
    );
    canvas.drawCircle(
      Offset(0, rLobe),
      rEye,
      Paint()
        ..color = goldColor.withValues(alpha: 0.80)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.9,
    );

    // 7. Outer Bronze Gold Boundary Rim
    canvas.drawCircle(
      Offset.zero,
      r,
      Paint()
        ..color = goldColor.withValues(alpha: 0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );

    // 8. Subtle cyan holographic accent ring
    canvas.drawCircle(
      Offset.zero,
      r - 1.0,
      Paint()
        ..color = const Color(0xFF00F0FF).withValues(alpha: 0.30)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.8,
    );

    canvas.restore(); // Restore layer
    canvas.restore(); // Restore matrix
  }

  @override
  bool shouldRepaint(covariant _TaijiCoreBackgroundPainter oldDelegate) {
    return oldDelegate.pulseProgress != pulseProgress ||
        oldDelegate.rotationProgress != rotationProgress ||
        oldDelegate.drumRadius != drumRadius;
  }
}

/// Paints Concentric Drum Holographic Rings and Orbiting Photons Overlay (On top of Trống Đồng)
class _HolographicLedRingsOverlayPainter extends CustomPainter {
  final double pulseProgress;
  final double rotationProgress;
  final double drumRadius;

  _HolographicLedRingsOverlayPainter({
    required this.pulseProgress,
    required this.rotationProgress,
    required this.drumRadius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    _drawHolographicLedRings(canvas, center);
  }

  void _drawHolographicLedRings(Canvas canvas, Offset center) {
    // Holographic concentric rings aligning precisely with Trống Đồng concentric geometry
    final ringRadii = [
      drumRadius * 0.28, // Inner solar collar
      drumRadius * 0.52, // Mid mythological animal & warrior ring
      drumRadius * 0.78, // Outer concentric geometric band
      drumRadius * 1.01, // Outer drum rim boundary
    ];

    final ringColors = [
      const Color(0xFFE5A93C), // Sacred Bronze Gold
      const Color(0xFF00F0FF), // Quantum Cyan
      const Color(0xFFF59E0B), // Solar Amber
      const Color(0xFF00FFB2), // Emerald Cyan
    ];

    for (int i = 0; i < ringRadii.length; i++) {
      final r = ringRadii[i];
      final color = ringColors[i];

      // Base Track Ring
      final ringPaint = Paint()
        ..color = color.withValues(alpha: 0.12)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2;
      canvas.drawCircle(center, r, ringPaint);

      // Counter-rotating Segmented Hologram HUD Arcs
      final counterAngle = -rotationProgress * 2 * math.pi * (1.1 + i * 0.3);
      final arcPaint = Paint()
        ..color = color.withValues(alpha: 0.30)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6
        ..strokeCap = StrokeCap.round;

      const segments = 4;
      final sweepAngle = (math.pi / 5);
      for (int s = 0; s < segments; s++) {
        final startAngle = counterAngle + (s * (2 * math.pi / segments));
        canvas.drawArc(
          Rect.fromCircle(center: center, radius: r),
          startAngle,
          sweepAngle,
          false,
          arcPaint,
        );
      }

      // Orbiting Hologram Photons along the drum's concentric tracks
      _drawOrbitingPhotons(canvas, center, r, color, i);
    }
  }

  void _drawOrbitingPhotons(Canvas canvas, Offset center, double radius, Color color, int index) {
    final dir = (index % 2 == 0) ? 1.0 : -1.0;
    for (int p = 0; p < 2; p++) {
      final photonProgress = (pulseProgress * dir + (p * 0.5) + (index * 0.23)) % 1.0;
      final angle = photonProgress * 2 * math.pi;
      final pos = Offset(center.dx + math.cos(angle) * radius, center.dy + math.sin(angle) * radius);

      // Core Photon
      canvas.drawCircle(
        pos,
        2.4,
        Paint()..color = Colors.white.withValues(alpha: 0.95),
      );

      // Glowing Halo
      canvas.drawCircle(
        pos,
        5.5,
        Paint()
          ..color = color.withValues(alpha: 0.55)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3.5),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _HolographicLedRingsOverlayPainter oldDelegate) {
    return oldDelegate.pulseProgress != pulseProgress ||
        oldDelegate.rotationProgress != rotationProgress ||
        oldDelegate.drumRadius != drumRadius;
  }
}
