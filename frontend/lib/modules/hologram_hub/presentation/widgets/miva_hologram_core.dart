import 'dart:math' as math;
import 'package:flutter/material.dart';

enum HologramRuntimeState {
  idle,
  listening,
  thinking,
  retrieving,
  acting,
  speaking,
  waitingApproval,
  success,
  warning,
  error,
  offline,
}

/// Model representation for a 3D neural node in the brain cluster
class _BrainNode3D {
  final double x;
  final double y;
  final double z;
  final double baseRadius;
  final bool isRightHemisphere;
  final int clusterId;

  const _BrainNode3D({
    required this.x,
    required this.y,
    required this.z,
    required this.baseRadius,
    required this.isRightHemisphere,
    required this.clusterId,
  });
}

/// Precomputed synaptic link between two nodes
class _SynapticLink {
  final int fromIndex;
  final int toIndex;
  final double length;

  const _SynapticLink({
    required this.fromIndex,
    required this.toIndex,
    required this.length,
  });
}

class MivaHologramCore extends StatefulWidget {
  final HologramRuntimeState runtimeState;
  final VoidCallback onTalkPressed;
  final VoidCallback onDashboardPressed;
  final VoidCallback? onConversationModePressed;
  final bool isConversationModeActive;

  const MivaHologramCore({
    super.key,
    this.runtimeState = HologramRuntimeState.idle,
    required this.onTalkPressed,
    required this.onDashboardPressed,
    this.onConversationModePressed,
    this.isConversationModeActive = false,
  });

  @override
  State<MivaHologramCore> createState() => _MivaHologramCoreState();
}

class _MivaHologramCoreState extends State<MivaHologramCore>
    with TickerProviderStateMixin {
  late AnimationController _rotationController;
  late AnimationController _pulseController;
  late AnimationController _particlesController;
  late AnimationController _hueController;

  static final List<_BrainNode3D> _staticBrainNodes = _generateBrainGeometry();
  static final List<_SynapticLink> _staticSynapses = _generateSynapticLinks(
    _staticBrainNodes,
  );

  @override
  void initState() {
    super.initState();
    // Continuous 3D orbit rotation
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 18),
    )..repeat();

    // Biological heartbeat / neural breathing pulse
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);

    // Particle phase & action potential electrical sparks
    _particlesController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    // Automatic smooth multi-hue color spectrum transition
    _hueController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 16),
    )..repeat();
  }

  @override
  void dispose() {
    _rotationController.dispose();
    _pulseController.dispose();
    _particlesController.dispose();
    _hueController.dispose();
    super.dispose();
  }

  /// Generates anatomical left & right hemisphere 3D neural coordinates
  static List<_BrainNode3D> _generateBrainGeometry() {
    final List<_BrainNode3D> nodes = [];
    const int totalNodes = 140;
    final math.Random random = math.Random(42); // Deterministic seed

    for (int i = 0; i < totalNodes; i++) {
      final bool isRight = i % 2 == 0;
      // Spherical distribution with hemisphere offset and cerebral cortex curvature
      final double u = (i + 0.5) / totalNodes;
      final double phi = math.acos(1.0 - 2.0 * u);
      final double theta = math.pi * (1.0 + math.sqrt(5.0)) * i;

      // Brain ellipsoid dimensions: width (X), height (Y), depth (Z)
      final double rX = 0.82 + 0.12 * math.cos(3 * theta);
      final double rY = 0.70 + 0.15 * math.sin(2 * phi);
      final double rZ = 0.88 + 0.10 * math.sin(theta);

      final double hemisphereGap = 0.22;
      final double xBase =
          math.sin(phi) * math.cos(theta) * rX +
          (isRight ? hemisphereGap : -hemisphereGap);
      final double yBase = math.sin(phi) * math.sin(theta) * rY;
      final double zBase = math.cos(phi) * rZ;

      // Random jitter for organic neural cluster density
      final double jitterX = (random.nextDouble() - 0.5) * 0.08;
      final double jitterY = (random.nextDouble() - 0.5) * 0.08;
      final double jitterZ = (random.nextDouble() - 0.5) * 0.08;

      nodes.add(
        _BrainNode3D(
          x: (xBase + jitterX).clamp(-1.2, 1.2),
          y: (yBase + jitterY).clamp(-1.0, 1.0),
          z: (zBase + jitterZ).clamp(-1.2, 1.2),
          baseRadius: 1.4 + random.nextDouble() * 2.2,
          isRightHemisphere: isRight,
          clusterId: i % 5,
        ),
      );
    }
    return nodes;
  }

  /// Calculates synaptic links between neighbor neural nodes
  static List<_SynapticLink> _generateSynapticLinks(List<_BrainNode3D> nodes) {
    final List<_SynapticLink> links = [];
    const double maxDistance = 0.42;

    for (int i = 0; i < nodes.length; i++) {
      int connectedCount = 0;
      for (int j = i + 1; j < nodes.length; j++) {
        // Link mainly within same hemisphere or across close corpus callosum
        if (nodes[i].isRightHemisphere != nodes[j].isRightHemisphere &&
            (nodes[i].x.abs() > 0.3 || nodes[j].x.abs() > 0.3)) {
          continue;
        }

        final double dx = nodes[i].x - nodes[j].x;
        final double dy = nodes[i].y - nodes[j].y;
        final double dz = nodes[i].z - nodes[j].z;
        final double dist = math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist <= maxDistance && connectedCount < 3) {
          links.add(_SynapticLink(fromIndex: i, toIndex: j, length: dist));
          connectedCount++;
        }
      }
    }
    return links;
  }

  /// Computes dynamic primary and secondary colors with smooth spectrum cycling
  ({Color primary, Color secondary, Color accent}) _resolveDynamicPalette() {
    final double hueProgress = _hueController.value;

    // Base spectrum hue (cycles smoothly through 0 -> 360)
    final double currentHue = (hueProgress * 360.0) % 360.0;
    final Color dynamicRainbowColor = HSVColor.fromAHSV(
      1.0,
      currentHue,
      0.82,
      0.98,
    ).toColor();

    final Color secondaryDynamicColor = HSVColor.fromAHSV(
      1.0,
      (currentHue + 45.0) % 360.0,
      0.75,
      0.95,
    ).toColor();

    final Color accentDynamicColor = HSVColor.fromAHSV(
      1.0,
      (currentHue + 90.0) % 360.0,
      0.70,
      1.0,
    ).toColor();

    // Specific operational states
    switch (widget.runtimeState) {
      case HologramRuntimeState.listening:
        return (
          primary: const Color(0xFF00F0FF),
          secondary: const Color(0xFF38BDF8),
          accent: const Color(0xFF00FFB2),
        );
      case HologramRuntimeState.thinking:
        return (
          primary: const Color(0xFF818CF8),
          secondary: const Color(0xFFA855F7),
          accent: const Color(0xFF60A5FA),
        );
      case HologramRuntimeState.retrieving:
        return (
          primary: const Color(0xFF38BDF8),
          secondary: const Color(0xFF0284C7),
          accent: const Color(0xFF818CF8),
        );
      case HologramRuntimeState.acting:
        return (
          primary: const Color(0xFF10B981),
          secondary: const Color(0xFF059669),
          accent: const Color(0xFF34D399),
        );
      case HologramRuntimeState.speaking:
        return (
          primary: const Color(0xFF00FFB2),
          secondary: const Color(0xFF00F0FF),
          accent: const Color(0xFF10B981),
        );
      case HologramRuntimeState.waitingApproval:
        return (
          primary: const Color(0xFFF59E0B),
          secondary: const Color(0xFFD97706),
          accent: const Color(0xFFFBBF24),
        );
      case HologramRuntimeState.success:
        return (
          primary: const Color(0xFF00FFB2),
          secondary: const Color(0xFF10B981),
          accent: const Color(0xFF6EE7B7),
        );
      case HologramRuntimeState.warning:
        return (
          primary: const Color(0xFFF97316),
          secondary: const Color(0xFFEA580C),
          accent: const Color(0xFFFBBF24),
        );
      case HologramRuntimeState.error:
        return (
          primary: const Color(0xFFEF4444),
          secondary: const Color(0xFFDC2626),
          accent: const Color(0xFFF87171),
        );
      case HologramRuntimeState.offline:
        return (
          primary: const Color(0xFF64748B),
          secondary: const Color(0xFF475569),
          accent: const Color(0xFF94A3B8),
        );
      case HologramRuntimeState.idle:
        // Idle mode: Full auto-shifting spectrum
        return (
          primary: dynamicRainbowColor,
          secondary: secondaryDynamicColor,
          accent: accentDynamicColor,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;
        final orbWidth = math.min(420.0, constraints.maxWidth);
        final orbHeight = orbWidth * (310.0 / 420.0);

        return AnimatedBuilder(
          animation: Listenable.merge([
            _rotationController,
            _pulseController,
            _particlesController,
            _hueController,
          ]),
          builder: (context, child) {
            final palette = _resolveDynamicPalette();

            return Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // ── Central 3D Neural Brain Orb ─────────────────────────────
                SizedBox(
                  width: orbWidth,
                  height: orbHeight,
                  child: CustomPaint(
                    size: Size(orbWidth, orbHeight),
                    painter: _NeuralBrainHologramPainter(
                      rotation: _rotationController.value,
                      pulse: _pulseController.value,
                      particlePhase: _particlesController.value,
                      primaryColor: palette.primary,
                      secondaryColor: palette.secondary,
                      accentColor: palette.accent,
                      nodes: _staticBrainNodes,
                      synapses: _staticSynapses,
                      runtimeState: widget.runtimeState,
                    ),
                  ),
                ),

                if (!isMobile) ...[
                  const SizedBox(height: 32),

                  // Desktop Action Buttons
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (widget.onConversationModePressed != null) ...[
                        Tooltip(
                          message: widget.isConversationModeActive
                              ? 'Dừng hội thoại'
                              : 'Chế độ Hội thoại',
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: widget.onConversationModePressed,
                              borderRadius: BorderRadius.circular(100),
                              child: Container(
                                width: 50,
                                height: 50,
                                alignment: Alignment.center,
                                decoration: BoxDecoration(
                                  gradient: widget.isConversationModeActive
                                      ? LinearGradient(
                                          colors: [
                                            palette.accent,
                                            palette.primary,
                                          ],
                                        )
                                      : null,
                                  color: widget.isConversationModeActive
                                      ? null
                                      : const Color(
                                          0xFF0D172A,
                                        ).withValues(alpha: 0.85),
                                  borderRadius: BorderRadius.circular(100),
                                  border: Border.all(
                                    color: palette.primary.withValues(
                                      alpha: 0.5,
                                    ),
                                    width: 1.2,
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: palette.primary.withValues(
                                        alpha: widget.isConversationModeActive
                                            ? 0.45
                                            : 0.15,
                                      ),
                                      blurRadius: 16,
                                      spreadRadius: 1,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                                child: Icon(
                                  widget.isConversationModeActive
                                      ? Icons.graphic_eq
                                      : Icons.record_voice_over,
                                  color: widget.isConversationModeActive
                                      ? const Color(0xFF04070E)
                                      : palette.primary,
                                  size: 22,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                      ],
                      Tooltip(
                        message: 'Bảng Điều khiển',
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: widget.onDashboardPressed,
                            borderRadius: BorderRadius.circular(100),
                            child: Container(
                              width: 50,
                              height: 50,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: const Color(
                                  0xFF0D172A,
                                ).withValues(alpha: 0.85),
                                borderRadius: BorderRadius.circular(100),
                                border: Border.all(
                                  color: palette.secondary.withValues(
                                    alpha: 0.45,
                                  ),
                                  width: 1.2,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: palette.secondary.withValues(
                                      alpha: 0.15,
                                    ),
                                    blurRadius: 14,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                              child: Icon(
                                Icons.dashboard_customize_outlined,
                                color: palette.secondary,
                                size: 22,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            );
          },
        );
      },
    );
  }
}

/// CustomPainter that renders the 3D Neural Brain swarm, Synaptic Axons, Action Potentials & Gyroscopic HUD Rings
class _NeuralBrainHologramPainter extends CustomPainter {
  final double rotation;
  final double pulse;
  final double particlePhase;
  final Color primaryColor;
  final Color secondaryColor;
  final Color accentColor;
  final List<_BrainNode3D> nodes;
  final List<_SynapticLink> synapses;
  final HologramRuntimeState runtimeState;

  _NeuralBrainHologramPainter({
    required this.rotation,
    required this.pulse,
    required this.particlePhase,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
    required this.nodes,
    required this.synapses,
    required this.runtimeState,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = Offset(size.width / 2, size.height / 2);
    final double maxRadius = math.min(size.width, size.height) * 0.45;

    // 1. Ambient Background Cosmic Radial Glow
    final Paint ambientGlow = Paint()
      ..shader = RadialGradient(
        colors: [
          primaryColor.withValues(alpha: 0.28 + 0.12 * pulse),
          secondaryColor.withValues(alpha: 0.10 + 0.05 * pulse),
          Colors.transparent,
        ],
        stops: const [0.0, 0.52, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: maxRadius * 1.5));
    canvas.drawCircle(center, maxRadius * 1.5, ambientGlow);

    // 2. Outer Gyroscopic HUD Orbit Rings
    _drawOuterGimbalRings(canvas, center, maxRadius);

    // 3. Render 3D Neural Brain Cluster (Nodes + Synapses + Action Potential Sparks)
    _drawNeuralBrain3D(canvas, center, maxRadius * 0.76);

    // 4. Inner Radiant Core Ring with Breathing Aura
    final Paint coreRingPaint = Paint()
      ..shader = SweepGradient(
        colors: [
          primaryColor.withValues(alpha: 0.8),
          secondaryColor.withValues(alpha: 0.4),
          accentColor.withValues(alpha: 0.8),
          primaryColor.withValues(alpha: 0.8),
        ],
        transform: GradientRotation(rotation * 2 * math.pi),
      ).createShader(Rect.fromCircle(center: center, radius: maxRadius * 0.62))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8;

    canvas.drawCircle(
      center,
      maxRadius * 0.62 * (0.96 + 0.04 * pulse),
      coreRingPaint,
    );
  }

  /// Draws multi-layer HUD rings with tick marks, calipers, and radar arc segments
  void _drawOuterGimbalRings(Canvas canvas, Offset center, double maxRadius) {
    final double primaryAngle = rotation * 2 * math.pi;
    final double counterAngle = -rotation * 2.5 * math.pi;

    // Ring 1: Outermost Caliper Ring with Tech Ticks
    final double r1 = maxRadius * 1.18;
    final Paint ring1Paint = Paint()
      ..color = primaryColor.withValues(alpha: 0.32)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    canvas.drawCircle(center, r1, ring1Paint);

    final Paint tickPaint = Paint()
      ..color = primaryColor.withValues(alpha: 0.5)
      ..strokeWidth = 1.4;

    const int totalTicks = 32;
    for (int i = 0; i < totalTicks; i++) {
      final double tickAngle = primaryAngle + (i * 2 * math.pi / totalTicks);
      final bool isMajor = i % 4 == 0;
      final double tickLen = isMajor ? 7.0 : 3.5;

      final Offset p1 = Offset(
        center.dx + math.cos(tickAngle) * (r1 - tickLen),
        center.dy + math.sin(tickAngle) * (r1 - tickLen),
      );
      final Offset p2 = Offset(
        center.dx + math.cos(tickAngle) * (r1 + tickLen),
        center.dy + math.sin(tickAngle) * (r1 + tickLen),
      );
      canvas.drawLine(p1, p2, tickPaint);
    }

    // Ring 2: Intermediate Dashed Cyber Arc Sweep
    final double r2 = maxRadius * 0.98;
    final Paint arcPaint = Paint()
      ..color = secondaryColor.withValues(alpha: 0.45)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    const int segments = 6;
    const double sweep = (2 * math.pi / segments) * 0.52;
    for (int i = 0; i < segments; i++) {
      final double startAngle = counterAngle + (i * 2 * math.pi / segments);
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: r2),
        startAngle,
        sweep,
        false,
        arcPaint,
      );
    }

    // Ring 3: Inclined Elliptical Gimbal Projection (simulates a tilted 3D orbit)
    final double r3 = maxRadius * 0.82;
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(math.pi / 5 + rotation * 0.5);
    final Rect ellipseRect = Rect.fromCenter(
      center: Offset.zero,
      width: r3 * 2.0,
      height: r3 * 1.3,
    );
    final Paint gimbalPaint = Paint()
      ..color = accentColor.withValues(alpha: 0.28 + 0.1 * pulse)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    canvas.drawOval(ellipseRect, gimbalPaint);
    canvas.restore();
  }

  /// Projects and renders the 3D Neural Brain cluster
  void _drawNeuralBrain3D(Canvas canvas, Offset center, double radius) {
    // 3D rotation angles around Y and X axes
    final double angleY = rotation * 2 * math.pi;
    final double angleX = 0.28 * math.sin(rotation * math.pi); // Gentle tilt

    final double cosY = math.cos(angleY);
    final double sinY = math.sin(angleY);
    final double cosX = math.cos(angleX);
    final double sinX = math.sin(angleX);

    // 1. Transform 3D coordinates to screen space
    final List<Offset> screenPoints = [];
    final List<double> depthList = [];

    for (final node in nodes) {
      // Scale by brain pulse
      final double pulseScale = 1.0 + 0.05 * math.sin(pulse * math.pi);
      final double x0 = node.x * radius * pulseScale;
      final double y0 = node.y * radius * pulseScale;
      final double z0 = node.z * radius * pulseScale;

      // Rotation around Y-axis
      final double x1 = x0 * cosY + z0 * sinY;
      final double z1 = -x0 * sinY + z0 * cosY;

      // Rotation around X-axis
      final double y2 = y0 * cosX - z1 * sinX;
      final double z2 = y0 * sinX + z1 * cosX;

      // Screen 2D projection
      screenPoints.add(Offset(center.dx + x1, center.dy + y2));
      // Normalized depth: 0.0 (farthest behind) to 1.0 (closest in front)
      final double depthAlpha = ((z2 / radius) + 1.0) / 2.0;
      depthList.add(depthAlpha.clamp(0.0, 1.0));
    }

    // 2. Draw Synaptic Links (Filaments between neurons)
    final Paint synapsePaint = Paint()..style = PaintingStyle.stroke;
    for (final link in synapses) {
      final double depthAvg =
          (depthList[link.fromIndex] + depthList[link.toIndex]) / 2.0;
      final double alpha = (0.12 + 0.45 * depthAvg).clamp(0.0, 1.0);

      synapsePaint.color = Color.lerp(
        secondaryColor,
        primaryColor,
        depthAvg,
      )!.withValues(alpha: alpha);
      synapsePaint.strokeWidth = 0.8 + 0.8 * depthAvg;

      final Offset p1 = screenPoints[link.fromIndex];
      final Offset p2 = screenPoints[link.toIndex];
      canvas.drawLine(p1, p2, synapsePaint);
    }

    // 3. Draw Action Potential Sparks (Electric packets traveling along axons)
    final Paint sparkPaint = Paint()..style = PaintingStyle.fill;
    final int activeSparksCount = math.min(18, synapses.length);
    for (int k = 0; k < activeSparksCount; k++) {
      final link = synapses[(k * 7) % synapses.length];
      final double t = (particlePhase * 2.0 + (k / activeSparksCount)) % 1.0;

      final Offset p1 = screenPoints[link.fromIndex];
      final Offset p2 = screenPoints[link.toIndex];
      final Offset sparkPos = Offset.lerp(p1, p2, t)!;
      final double sparkDepth =
          (depthList[link.fromIndex] + depthList[link.toIndex]) / 2.0;

      sparkPaint.color = accentColor.withValues(
        alpha: (0.4 + 0.6 * sparkDepth).clamp(0.0, 1.0),
      );
      canvas.drawCircle(sparkPos, 1.6 + 1.2 * sparkDepth, sparkPaint);
    }

    // 4. Draw Neural Nodes (Brain Nodes)
    final Paint nodePaint = Paint()..style = PaintingStyle.fill;
    final Paint nodeHaloPaint = Paint()..style = PaintingStyle.fill;

    for (int i = 0; i < nodes.length; i++) {
      final Offset pos = screenPoints[i];
      final double depth = depthList[i];
      final _BrainNode3D node = nodes[i];

      final double nodeSize = node.baseRadius * (0.65 + 0.75 * depth);
      final Color nodeColor = Color.lerp(
        secondaryColor,
        primaryColor,
        (i % 3) / 2.0,
      )!;

      // Outer soft halo
      nodeHaloPaint.color = nodeColor.withValues(alpha: 0.18 * depth);
      canvas.drawCircle(pos, nodeSize * 2.2, nodeHaloPaint);

      // Core neural point
      nodePaint.color = Color.lerp(
        nodeColor,
        Colors.white,
        0.35 * depth,
      )!.withValues(alpha: 0.35 + 0.65 * depth);
      canvas.drawCircle(pos, nodeSize, nodePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _NeuralBrainHologramPainter oldDelegate) {
    return oldDelegate.rotation != rotation ||
        oldDelegate.pulse != pulse ||
        oldDelegate.particlePhase != particlePhase ||
        oldDelegate.primaryColor != primaryColor ||
        oldDelegate.secondaryColor != secondaryColor ||
        oldDelegate.accentColor != accentColor;
  }
}
