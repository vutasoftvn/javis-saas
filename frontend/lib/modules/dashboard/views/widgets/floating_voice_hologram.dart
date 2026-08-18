import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../realtime_voice/domain/hologram_state.dart';
import '../../../realtime_voice/presentation/controllers/voice_session_controller.dart';
import '../../controllers/dashboard_controller.dart';

/// Representation of a 3D neural node for the floating brain orb
class _MiniBrainNode3D {
  final double x;
  final double y;
  final double z;
  final double radius;
  final bool isRight;

  const _MiniBrainNode3D({
    required this.x,
    required this.y,
    required this.z,
    required this.radius,
    required this.isRight,
  });
}

class _MiniSynapse {
  final int from;
  final int to;

  const _MiniSynapse({required this.from, required this.to});
}

/// A compact, draggable Neural Brain entry point for COSA realtime voice on every dashboard tab.
class FloatingVoiceHologram extends StatefulWidget {
  const FloatingVoiceHologram({super.key});

  @override
  State<FloatingVoiceHologram> createState() => _FloatingVoiceHologramState();
}

class _FloatingVoiceHologramState extends State<FloatingVoiceHologram>
    with TickerProviderStateMixin {
  static const _diameter = 76.0;
  static const _rightPadding = 48.0;
  static const _bottomPadding = 120.0;
  Offset? _position;

  late final AnimationController _rotationController;
  late final AnimationController _pulseController;
  late final AnimationController _hueController;

  static final List<_MiniBrainNode3D> _nodes = _generateMiniBrainGeometry();
  static final List<_MiniSynapse> _synapses = _generateMiniSynapses(_nodes);

  VoiceSessionController? get _voice =>
      Get.isRegistered<VoiceSessionController>() ? Get.find<VoiceSessionController>() : null;

  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..repeat();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    _hueController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..repeat();
  }

  @override
  void dispose() {
    _rotationController.dispose();
    _pulseController.dispose();
    _hueController.dispose();
    super.dispose();
  }

  static List<_MiniBrainNode3D> _generateMiniBrainGeometry() {
    final List<_MiniBrainNode3D> nodes = [];
    const int count = 48;
    final math.Random random = math.Random(108);

    for (int i = 0; i < count; i++) {
      final bool isRight = i % 2 == 0;
      final double u = (i + 0.5) / count;
      final double phi = math.acos(1.0 - 2.0 * u);
      final double theta = math.pi * (1.0 + math.sqrt(5.0)) * i;

      final double rX = 0.82 + 0.12 * math.cos(3 * theta);
      final double rY = 0.70 + 0.15 * math.sin(2 * phi);
      final double rZ = 0.86;

      const double hemisphereGap = 0.22;
      final double x =
          math.sin(phi) * math.cos(theta) * rX +
          (isRight ? hemisphereGap : -hemisphereGap);
      final double y = math.sin(phi) * math.sin(theta) * rY;
      final double z = math.cos(phi) * rZ;

      nodes.add(
        _MiniBrainNode3D(
          x: x.clamp(-1.2, 1.2),
          y: y.clamp(-1.0, 1.0),
          z: z.clamp(-1.2, 1.2),
          radius: 1.0 + random.nextDouble() * 1.5,
          isRight: isRight,
        ),
      );
    }
    return nodes;
  }

  static List<_MiniSynapse> _generateMiniSynapses(List<_MiniBrainNode3D> nodes) {
    final List<_MiniSynapse> links = [];
    const double maxDist = 0.55;

    for (int i = 0; i < nodes.length; i++) {
      int connected = 0;
      for (int j = i + 1; j < nodes.length; j++) {
        if (nodes[i].isRight != nodes[j].isRight &&
            (nodes[i].x.abs() > 0.3 || nodes[j].x.abs() > 0.3)) {
          continue;
        }
        final double dx = nodes[i].x - nodes[j].x;
        final double dy = nodes[i].y - nodes[j].y;
        final double dz = nodes[i].z - nodes[j].z;
        final double dist = math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist <= maxDist && connected < 2) {
          links.add(_MiniSynapse(from: i, to: j));
          connected++;
        }
      }
    }
    return links;
  }

  Future<void> _toggleVoice() async {
    final voice = _voice;
    if (voice == null) return;
    if (voice.isActive.value) {
      await voice.stopVoiceSession();
      return;
    }
    await voice.startVoiceSession(
      deviceType: GetPlatform.isDesktop ? 'desktop' : 'mobile',
      onNavigate: _handleVoiceNavigation,
    );
  }

  void _handleVoiceNavigation(String target, Map<String, dynamic> _) {
    final pageByTarget = <String, int>{
      'chat': 0,
      'tasks': 1,
      'vault': 2,
      'strategy': 3,
      'okrs': 27,
      'twelve_week_year': 28,
      'projects': 29,
      'needs_you': 24,
      'workflows': 10,
      'plugins': 12,
      'settings': 15,
      'dashboard': 0,
    };
    final index = pageByTarget[target.toLowerCase()];
    if (index != null && Get.isRegistered<DashboardController>()) {
      Get.find<DashboardController>().changePage(index, 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final double maxX = math.max(0.0, constraints.maxWidth - _diameter);
          final double maxY = math.max(0.0, constraints.maxHeight - _diameter);
          final defaultPosition = Offset(
            math.max(0.0, constraints.maxWidth - _diameter - _rightPadding),
            math.max(0.0, constraints.maxHeight - _diameter - _bottomPadding),
          );
          final Offset currentPos = _position ?? defaultPosition;
          final Offset boundedPosition = Offset(
            currentPos.dx.clamp(0.0, maxX),
            currentPos.dy.clamp(0.0, maxY),
          );

          return Stack(
            children: [
              Obx(() {
                final voice = _voice;
                final isActive = voice?.isActive.value ?? false;
                if (!isActive) return const SizedBox.shrink();
                return Positioned.fill(
                  child: AbsorbPointer(
                    absorbing: false,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: RadialGradient(
                          center: Alignment(
                            (boundedPosition.dx + _diameter / 2) /
                                    constraints.maxWidth *
                                    2 -
                                1,
                            (boundedPosition.dy + _diameter / 2) /
                                    constraints.maxHeight *
                                    2 -
                                1,
                          ),
                          radius: 0.6,
                          colors: [
                            const Color(0xFF00FFB2).withValues(alpha: 0.08),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }),
              if (boundedPosition.dx.isFinite && boundedPosition.dy.isFinite)
                Positioned(
                  left: boundedPosition.dx,
                  top: boundedPosition.dy,
                  child: Obx(() {
                    final voice = _voice;
                    final isActive = voice?.isActive.value ?? false;
                    final isListening =
                        isActive &&
                        voice?.hologramState.value ==
                            RealtimeHologramState.listening;

                    return GestureDetector(
                      onPanStart: (_) =>
                          setState(() => _position = boundedPosition),
                      onPanUpdate: (details) => setState(() {
                        _position = Offset(
                          (boundedPosition.dx + details.delta.dx).clamp(
                            0.0,
                            maxX,
                          ),
                          (boundedPosition.dy + details.delta.dy).clamp(
                            0.0,
                            maxY,
                          ),
                        );
                      }),
                      onTap: _toggleVoice,
                      child: Tooltip(
                        message: isActive
                            ? 'Dừng lắng nghe COSA'
                            : 'Gọi COSA Neural Voice',
                        child: SizedBox(
                          key: const Key('floating_voice_hologram'),
                          width: _diameter,
                          height: _diameter,
                          child: AnimatedBuilder(
                            animation: Listenable.merge([
                              _rotationController,
                              _pulseController,
                              _hueController,
                            ]),
                            builder: (context, _) {
                              final double hue =
                                  (_hueController.value * 360.0) % 360.0;
                              final dynamicPrimary = isListening
                                  ? const Color(0xFF00FFB2)
                                  : HSVColor.fromAHSV(
                                      1.0,
                                      hue,
                                      0.82,
                                      0.98,
                                    ).toColor();
                              final dynamicSecondary = isListening
                                  ? const Color(0xFF14B8A6)
                                  : HSVColor.fromAHSV(
                                      1.0,
                                      (hue + 50.0) % 360.0,
                                      0.78,
                                      0.95,
                                    ).toColor();

                              return CustomPaint(
                                painter: _FloatingNeuralBrainPainter(
                                  rotation: _rotationController.value,
                                  pulse: _pulseController.value,
                                  primaryColor: dynamicPrimary,
                                  secondaryColor: dynamicSecondary,
                                  listening: isListening,
                                  nodes: _nodes,
                                  synapses: _synapses,
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                    );
                  }),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _FloatingNeuralBrainPainter extends CustomPainter {
  final double rotation;
  final double pulse;
  final Color primaryColor;
  final Color secondaryColor;
  final bool listening;
  final List<_MiniBrainNode3D> nodes;
  final List<_MiniSynapse> synapses;

  const _FloatingNeuralBrainPainter({
    required this.rotation,
    required this.pulse,
    required this.primaryColor,
    required this.secondaryColor,
    required this.listening,
    required this.nodes,
    required this.synapses,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = size.center(Offset.zero);
    final double radius = size.width / 2;

    // 1. Ambient Hologram Core Glow
    final Paint glow = Paint()
      ..color = primaryColor.withValues(alpha: listening ? 0.32 : 0.18)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
    canvas.drawCircle(center, radius * 0.8, glow);

    // 2. Translucent Backdrop Disc
    final Paint disc = Paint()
      ..shader = RadialGradient(
        colors: [
          primaryColor.withValues(alpha: 0.22),
          const Color(0xFF040814).withValues(alpha: 0.94),
        ],
      ).createShader(Rect.fromCircle(center: center, radius: radius * 0.88));
    canvas.drawCircle(center, radius * 0.88, disc);

    // 3. Gyroscopic HUD Rings with Tech Ticks
    _drawOuterRings(canvas, center, radius);

    // 4. 3D Mini Neural Brain
    _drawMiniBrain(canvas, center, radius * 0.58);
  }

  void _drawOuterRings(Canvas canvas, Offset center, double radius) {
    final double angle = rotation * 2 * math.pi;

    // Outer Caliper Ring
    final Paint ring = Paint()
      ..color = primaryColor.withValues(alpha: 0.55 + 0.2 * pulse)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    canvas.drawCircle(center, radius * 0.86, ring);

    // Ticks
    final Paint tickPaint = Paint()
      ..color = primaryColor.withValues(alpha: 0.7)
      ..strokeWidth = 1.2;
    const int totalTicks = 16;
    for (int i = 0; i < totalTicks; i++) {
      final double tickAngle = angle + (i * 2 * math.pi / totalTicks);
      final double tickLen = i % 4 == 0 ? 4.5 : 2.5;
      final Offset p1 = Offset(
        center.dx + math.cos(tickAngle) * (radius * 0.86 - tickLen),
        center.dy + math.sin(tickAngle) * (radius * 0.86 - tickLen),
      );
      final Offset p2 = Offset(
        center.dx + math.cos(tickAngle) * (radius * 0.86 + tickLen),
        center.dy + math.sin(tickAngle) * (radius * 0.86 + tickLen),
      );
      canvas.drawLine(p1, p2, tickPaint);
    }

    // Inclined Gimbal Ring
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(-angle * 0.7);
    final Paint gimbal = Paint()
      ..color = secondaryColor.withValues(alpha: 0.4)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: radius * 1.65,
        height: radius * 0.95,
      ),
      gimbal,
    );
    canvas.restore();
  }

  void _drawMiniBrain(Canvas canvas, Offset center, double brainRadius) {
    final double angleY = rotation * 2 * math.pi;
    final double cosY = math.cos(angleY);
    final double sinY = math.sin(angleY);

    final List<Offset> points = [];
    final List<double> depths = [];

    for (final node in nodes) {
      final double scale = 1.0 + 0.06 * math.sin(pulse * math.pi);
      final double x0 = node.x * brainRadius * scale;
      final double y0 = node.y * brainRadius * scale;
      final double z0 = node.z * brainRadius * scale;

      final double x1 = x0 * cosY + z0 * sinY;
      final double z1 = -x0 * sinY + z0 * cosY;

      points.add(Offset(center.dx + x1, center.dy + y0));
      final double depth = ((z1 / brainRadius) + 1.0) / 2.0;
      depths.add(depth.clamp(0.0, 1.0));
    }

    // Synapses
    final Paint synPaint = Paint()..style = PaintingStyle.stroke;
    for (final link in synapses) {
      final double avgDepth = (depths[link.from] + depths[link.to]) / 2.0;
      synPaint.color = secondaryColor.withValues(
        alpha: 0.15 + 0.45 * avgDepth,
      );
      synPaint.strokeWidth = 0.7 + 0.5 * avgDepth;
      canvas.drawLine(points[link.from], points[link.to], synPaint);
    }

    // Nodes
    final Paint nodePaint = Paint()..style = PaintingStyle.fill;
    for (int i = 0; i < nodes.length; i++) {
      final double d = depths[i];
      nodePaint.color = Color.lerp(
        secondaryColor,
        primaryColor,
        d,
      )!.withValues(alpha: 0.35 + 0.65 * d);
      final double size = nodes[i].radius * (0.6 + 0.6 * d);
      canvas.drawCircle(points[i], size, nodePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _FloatingNeuralBrainPainter oldDelegate) {
    return oldDelegate.rotation != rotation ||
        oldDelegate.pulse != pulse ||
        oldDelegate.primaryColor != primaryColor ||
        oldDelegate.secondaryColor != secondaryColor ||
        oldDelegate.listening != listening;
  }
}
