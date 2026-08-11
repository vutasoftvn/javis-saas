import 'dart:math' as math;
import 'package:flutter/material.dart';

enum HologramRuntimeState {
  idle,
  listening,
  thinking,
  retrieving,
  acting,
  waitingApproval,
  success,
  warning,
  error,
  offline,
}

class MivaHologramCore extends StatefulWidget {
  final HologramRuntimeState runtimeState;
  final VoidCallback onTalkPressed;
  final VoidCallback onDashboardPressed;

  const MivaHologramCore({
    super.key,
    this.runtimeState = HologramRuntimeState.idle,
    required this.onTalkPressed,
    required this.onDashboardPressed,
  });

  @override
  State<MivaHologramCore> createState() => _MivaHologramCoreState();
}

class _MivaHologramCoreState extends State<MivaHologramCore> with TickerProviderStateMixin {
  late AnimationController _rotationController;
  late AnimationController _pulseController;
  late AnimationController _particlesController;

  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2500),
    )..repeat(reverse: true);

    _particlesController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..repeat();
  }

  @override
  void dispose() {
    _rotationController.dispose();
    _pulseController.dispose();
    _particlesController.dispose();
    super.dispose();
  }

  Color _getStateColor() {
    switch (widget.runtimeState) {
      case HologramRuntimeState.listening:
        return const Color(0xFF00F0FF); // Cyan
      case HologramRuntimeState.thinking:
        return const Color(0xFF818CF8); // Indigo/Purple
      case HologramRuntimeState.retrieving:
        return const Color(0xFF38BDF8); // Sky blue
      case HologramRuntimeState.acting:
        return const Color(0xFF10B981); // Emerald
      case HologramRuntimeState.waitingApproval:
        return const Color(0xFFF59E0B); // Amber
      case HologramRuntimeState.success:
        return const Color(0xFF00FFB2); // Neon Mint
      case HologramRuntimeState.warning:
        return const Color(0xFFF97316); // Orange
      case HologramRuntimeState.error:
        return const Color(0xFFEF4444); // Red
      case HologramRuntimeState.idle:
        return const Color(0xFF00F0FF); // Core Cyan
      case HologramRuntimeState.offline:
        return const Color(0xFF64748B); // Muted Slate
    }
  }

  @override
  Widget build(BuildContext context) {
    final stateColor = _getStateColor();

    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;
        final orbWidth = math.min(380.0, constraints.maxWidth);
        final orbHeight = orbWidth * (280.0 / 380.0);

        if (isMobile) {
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: orbWidth,
                height: orbHeight,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    AnimatedBuilder(
                      animation: Listenable.merge([
                        _rotationController,
                        _pulseController,
                        _particlesController,
                      ]),
                      builder: (context, child) {
                        return CustomPaint(
                          size: Size(orbWidth, orbHeight),
                          painter: _HologramOrbPainter(
                            rotation: _rotationController.value,
                            pulse: _pulseController.value,
                            particlePhase: _particlesController.value,
                            stateColor: stateColor,
                            runtimeState: widget.runtimeState,
                          ),
                        );
                      },
                    ),
                    // Center Typography
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ShaderMask(
                          shaderCallback: (bounds) => LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [Colors.white, stateColor, const Color(0xFF818CF8)],
                            stops: const [0.0, 0.65, 1.0],
                          ).createShader(bounds),
                          child: const Text(
                            'COSA',
                            style: TextStyle(
                              fontSize: 48,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 4.0,
                              color: Colors.white,
                              height: 1.0,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'COMPANY ONE SYSTEM AI',
                          style: TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.8,
                            color: stateColor.withValues(alpha: 0.9),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              // Mobile System Status Indicator (Active Dot & ACTIVE text)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedBuilder(
                    animation: _pulseController,
                    builder: (context, child) {
                      final pulse = _pulseController.value;
                      return Container(
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF10B981).withValues(alpha: 0.5 + 0.5 * pulse),
                              blurRadius: 6 + 4 * pulse,
                              spreadRadius: 1 + pulse,
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'ACTIVE',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.6,
                      color: Color(0xFF10B981),
                    ),
                  ),
                ],
              ),
            ],
          );
        }

        // ── DESKTOP / TABLET: original layout ─────────────────────────
        return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // STARK-CLASS badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1C34).withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: stateColor.withValues(alpha: 0.35), width: 1),
                  boxShadow: [
                    BoxShadow(
                      color: stateColor.withValues(alpha: 0.15),
                      blurRadius: 12,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'STARK-CLASS  PERSONAL  INTELLIGENCE',
                      style: TextStyle(
                        color: stateColor.withValues(alpha: 0.95),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 2.2,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Central Hologram Orb
              SizedBox(
                width: orbWidth,
                height: orbHeight,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    AnimatedBuilder(
                      animation: Listenable.merge([
                        _rotationController,
                        _pulseController,
                        _particlesController,
                      ]),
                      builder: (context, child) {
                        return CustomPaint(
                          size: Size(orbWidth, orbHeight),
                          painter: _HologramOrbPainter(
                            rotation: _rotationController.value,
                            pulse: _pulseController.value,
                            particlePhase: _particlesController.value,
                            stateColor: stateColor,
                            runtimeState: widget.runtimeState,
                          ),
                        );
                      },
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ShaderMask(
                          shaderCallback: (bounds) => LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [Colors.white, stateColor, const Color(0xFF818CF8)],
                            stops: const [0.0, 0.65, 1.0],
                          ).createShader(bounds),
                          child: const Text(
                            'COSA',
                            style: TextStyle(
                              fontSize: 64,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 6.0,
                              color: Colors.white,
                              height: 1.0,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'COMPANY ONE SYSTEM AI',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 3.0,
                            color: stateColor.withValues(alpha: 0.9),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Description + Status pill (desktop only)
              const SizedBox(height: 8),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 24),
                child: Text(
                  'COSA là hệ điều hành AI toàn diện.\nTôi giúp bạn suy nghĩ, lập kế hoạch, hành động và tạo ra kết quả.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14.5, height: 1.5, color: Color(0xFF94A3B8)),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF10B981).withValues(alpha: 0.8),
                          blurRadius: 8,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'SYSTEM STATUS: ACTIVE',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                      color: Color(0xFF10B981),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Desktop buttons row
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: widget.onTalkPressed,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF00D2FF), Color(0xFF0072FF)],
                          ),
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF00D2FF).withValues(alpha: 0.4),
                              blurRadius: 18,
                              spreadRadius: 1,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.mic, color: Color(0xFF04070E), size: 20),
                            SizedBox(width: 10),
                            Text(
                              'TALK TO COSA',
                              style: TextStyle(
                                color: Color(0xFF04070E),
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: widget.onDashboardPressed,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0D172A).withValues(alpha: 0.8),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: const Color(0xFF00F0FF).withValues(alpha: 0.4),
                            width: 1.2,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.3),
                              blurRadius: 12,
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.dashboard_customize_outlined, color: Color(0xFF00F0FF), size: 20),
                            SizedBox(width: 10),
                            Text(
                              'OPEN DASHBOARD',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          );

      },
    );
  }
}

class _HologramOrbPainter extends CustomPainter {
  final double rotation;
  final double pulse;
  final double particlePhase;
  final Color stateColor;
  final HologramRuntimeState runtimeState;

  _HologramOrbPainter({
    required this.rotation,
    required this.pulse,
    required this.particlePhase,
    required this.stateColor,
    required this.runtimeState,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = math.min(size.width, size.height) * 0.45;

    // 1. Ambient Background Glow
    final glowPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          stateColor.withValues(alpha: 0.25 + 0.15 * pulse),
          stateColor.withValues(alpha: 0.08),
          Colors.transparent,
        ],
        stops: const [0.0, 0.55, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: maxRadius * 1.4));
    canvas.drawCircle(center, maxRadius * 1.4, glowPaint);

    // 2. Outer Rotating HUD Rings with tick marks
    _drawHudRing(canvas, center, maxRadius * 1.15, rotation * 2 * math.pi, 24, 0.3);
    _drawHudRing(canvas, center, maxRadius * 0.95, -rotation * 3 * math.pi, 16, 0.45);
    _drawDashedRing(canvas, center, maxRadius * 0.78, rotation * 1.5 * math.pi, 0.3);

    // 3. 3D Particle Cloud Swarm
    _drawParticleCloud(canvas, center, maxRadius * 0.85);

    // 4. Inner Radiant Core Ring
    final coreRingPaint = Paint()
      ..color = stateColor.withValues(alpha: 0.6 + 0.3 * pulse)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8;
    canvas.drawCircle(center, maxRadius * 0.65 * (0.95 + 0.05 * pulse), coreRingPaint);
  }

  void _drawHudRing(Canvas canvas, Offset center, double radius, double angle, int ticks, double opacity) {
    final ringPaint = Paint()
      ..color = stateColor.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    canvas.drawCircle(center, radius, ringPaint);

    // Draw tech tick marks
    final tickPaint = Paint()
      ..color = stateColor.withValues(alpha: opacity * 1.2)
      ..strokeWidth = 1.5;

    for (int i = 0; i < ticks; i++) {
      final tickAngle = angle + (i * 2 * math.pi / ticks);
      final p1 = Offset(
        center.dx + math.cos(tickAngle) * (radius - 4),
        center.dy + math.sin(tickAngle) * (radius - 4),
      );
      final p2 = Offset(
        center.dx + math.cos(tickAngle) * (radius + 4),
        center.dy + math.sin(tickAngle) * (radius + 4),
      );
      canvas.drawLine(p1, p2, tickPaint);
    }
  }

  void _drawDashedRing(Canvas canvas, Offset center, double radius, double angle, double opacity) {
    final arcPaint = Paint()
      ..color = stateColor.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    const segmentCount = 6;
    const sweep = (2 * math.pi / segmentCount) * 0.55;

    for (int i = 0; i < segmentCount; i++) {
      final startAngle = angle + (i * 2 * math.pi / segmentCount);
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweep,
        false,
        arcPaint,
      );
    }
  }

  void _drawParticleCloud(Canvas canvas, Offset center, double radius) {
    final particlePaint = Paint()..style = PaintingStyle.fill;
    const int count = 120;

    for (int i = 0; i < count; i++) {
      final seed = i * 137.508; // Golden angle
      final t = (particlePhase + (i / count)) % 1.0;

      final theta = seed + t * 2 * math.pi;
      final phi = math.acos(1 - 2 * ((i + 0.5) / count));
      final r = radius * (0.4 + 0.6 * math.sin(seed + particlePhase * 3 * math.pi).abs());

      // 3D sphere projection to 2D screen with rotation
      final x3d = r * math.sin(phi) * math.cos(theta);
      final y3d = r * math.sin(phi) * math.sin(theta);
      final z3d = r * math.cos(phi);

      final rotAngle = rotation * 2 * math.pi;
      final xRot = x3d * math.cos(rotAngle) - z3d * math.sin(rotAngle);
      final zRot = x3d * math.sin(rotAngle) + z3d * math.cos(rotAngle);

      final depthAlpha = ((zRot / radius) + 1.0) / 2.0; // 0.0 (far) to 1.0 (near)
      final pSize = 1.2 + 2.2 * depthAlpha;

      particlePaint.color = Color.lerp(
        const Color(0xFF38BDF8),
        stateColor,
        (i % 3) / 2.0,
      )!.withValues(alpha: 0.2 + 0.75 * depthAlpha);

      canvas.drawCircle(
        Offset(center.dx + xRot, center.dy + y3d),
        pSize,
        particlePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _HologramOrbPainter oldDelegate) {
    return oldDelegate.rotation != rotation ||
        oldDelegate.pulse != pulse ||
        oldDelegate.particlePhase != particlePhase ||
        oldDelegate.stateColor != stateColor;
  }
}
