import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../realtime_voice/domain/hologram_state.dart';
import '../../../realtime_voice/presentation/controllers/voice_session_controller.dart';
import '../../controllers/dashboard_controller.dart';

/// A compact, draggable entry point for COSA realtime voice on every dashboard
/// tab. LiveKit remote audio uses the device's default operating-system output.
class FloatingVoiceHologram extends StatefulWidget {
  const FloatingVoiceHologram({super.key});

  @override
  State<FloatingVoiceHologram> createState() => _FloatingVoiceHologramState();
}

class _FloatingVoiceHologramState extends State<FloatingVoiceHologram>
    with SingleTickerProviderStateMixin {
  static const _diameter = 76.0;
  static const _rightPadding = 48.0;
  static const _bottomPadding = 120.0;
  Offset? _position;
  late final AnimationController _rotationController;

  VoiceSessionController get _voice => Get.find<VoiceSessionController>();

  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();
  }

  @override
  void dispose() {
    _rotationController.dispose();
    super.dispose();
  }

  Future<void> _toggleVoice() async {
    if (_voice.isActive.value) {
      await _voice.stopVoiceSession();
      return;
    }
    await _voice.startVoiceSession(
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
      'blocked_work': 25,
      'work_inspector': 26,
      'settings': 13,
      'dashboard': 0,
    };
    final page = pageByTarget[target];
    if (page != null) Get.find<DashboardController>().changePage(page, 0);
  }

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxX = math.max(0.0, constraints.maxWidth - _diameter);
          final maxY = math.max(0.0, constraints.maxHeight - _diameter);
          final defaultPosition = Offset(
            math.max(0.0, constraints.maxWidth - _diameter - _rightPadding),
            math.max(0.0, constraints.maxHeight - _diameter - _bottomPadding),
          );
          final boundedPosition = _position ?? defaultPosition;

          return Stack(
            children: [
              Positioned(
                left: boundedPosition.dx,
                top: boundedPosition.dy,
                child: Obx(() {
                  final isListening =
                      _voice.isActive.value &&
                      _voice.hologramState.value ==
                          RealtimeHologramState.listening;
                  final color = isListening
                      ? const Color(0xFF14B8A6)
                      : const Color(0xFF00D2FF);
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
                      message: _voice.isActive.value
                          ? 'Dừng lắng nghe COSA'
                          : 'Gọi COSA',
                      child: SizedBox(
                        key: const Key('floating_voice_hologram'),
                        width: _diameter,
                        height: _diameter,
                        child: AnimatedBuilder(
                          animation: _rotationController,
                          builder: (context, _) => CustomPaint(
                            painter: _FloatingHologramPainter(
                              rotation: _rotationController.value,
                              color: color,
                              listening: isListening,
                            ),
                            child: Center(
                              child: Icon(
                                isListening
                                    ? Icons.graphic_eq_rounded
                                    : Icons.mic_none_rounded,
                                color: color,
                                size: 26,
                              ),
                            ),
                          ),
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

class _FloatingHologramPainter extends CustomPainter {
  const _FloatingHologramPainter({
    required this.rotation,
    required this.color,
    required this.listening,
  });

  final double rotation;
  final Color color;
  final bool listening;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.width / 2;
    final glow = Paint()
      ..color = color.withValues(alpha: listening ? 0.24 : 0.16)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14);
    canvas.drawCircle(center, radius * .72, glow);

    final core = Paint()
      ..shader = RadialGradient(
        colors: [
          color.withValues(alpha: .25),
          const Color(0xFF071522).withValues(alpha: .92),
        ],
      ).createShader(Rect.fromCircle(center: center, radius: radius * .62));
    canvas.drawCircle(center, radius * .62, core);

    final ring = Paint()
      ..color = color.withValues(alpha: .9)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(rotation * math.pi * 2);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: radius * 1.9,
        height: radius * .72,
      ),
      ring,
    );
    canvas.rotate(math.pi / 2.2);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: radius * 1.75,
        height: radius * .62,
      ),
      ring,
    );
    canvas.restore();
    canvas.drawCircle(center, radius * .62, ring);
  }

  @override
  bool shouldRepaint(covariant _FloatingHologramPainter oldDelegate) =>
      oldDelegate.rotation != rotation ||
      oldDelegate.color != color ||
      oldDelegate.listening != listening;
}
