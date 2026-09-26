import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../../../core/services/voice_service.dart';
import 'planet_hologram_inspector_dialog.dart';

/// Animated Futuristic Cyber Trống Đồng Centerpiece Background
/// Focuses on the sacred Vietnamese Bronze Drum (Trống Đồng Đông Sơn) in the center:
/// - Clean, deep, calm cosmic background with controlled, reduced halo around the drum.
/// - Concentric holographic rings hugging the drum's sacred geometric bands.
/// - Dynamic Centerpiece Audio Voice Visualizer Core replacing the old Yin-Yang:
///   * 360-degree radial frequency spectrum equalizer bars
///   * Concentric acoustic soundwave ripple rings
///   * Fluid circular oscilloscope waveform ribbon
///   * Central cyber voice orb with dancing vertical equalizer bars
///   * Dynamically reacts to microphone audio level & voice activity from [VoiceService]
///     or custom [audioLevelNotifier] / [isVoiceActive] parameters for future voice extensions.
/// - Counter-rotating holographic HUD arcs and subtle orbiting photon energy nodes.
class CyberCircuitBackground extends StatefulWidget {
  final Widget? child;
  final bool? isVoiceActive;
  final double? audioLevel;
  final List<double>? frequencyBands;
  final ValueListenable<double>? audioLevelNotifier;
  final ValueListenable<bool>? isVoiceActiveNotifier;
  final VoidCallback? onVoiceTap;
  final void Function(PlanetHologramData planet)? onPlanetTap;

  const CyberCircuitBackground({
    super.key,
    this.child,
    this.isVoiceActive,
    this.audioLevel,
    this.frequencyBands,
    this.audioLevelNotifier,
    this.isVoiceActiveNotifier,
    this.onVoiceTap,
    this.onPlanetTap,
  });

  @override
  State<CyberCircuitBackground> createState() => _CyberCircuitBackgroundState();
}

class _CyberCircuitBackgroundState extends State<CyberCircuitBackground>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _rotationController;
  late AnimationController _audioWaveController;

  ValueListenable<double>? _effectiveAudioLevelNotifier;
  ValueListenable<bool>? _effectiveVoiceActiveNotifier;

  double _audioLevel = 0.0;
  bool _isVoiceActive = false;
  Offset? _pointerDownPos;
  int? _pointerDownTime;
  bool _isHoveringPlanet = false;

  void _onPointerDown(PointerDownEvent event) {
    _pointerDownPos = event.localPosition;
    _pointerDownTime = DateTime.now().millisecondsSinceEpoch;
  }

  void _onPointerUp(PointerUpEvent event, double drumRadius, Size size) {
    if (_pointerDownPos == null) return;
    final distance = (event.localPosition - _pointerDownPos!).distance;
    final duration = DateTime.now().millisecondsSinceEpoch - (_pointerDownTime ?? 0);
    _pointerDownPos = null;

    // Phải là một cú chạm dứt khoát (tap), không phải kéo cuộn (scroll drag)
    if (distance > 14.0 || duration > 800) return;

    _checkPlanetHit(event.localPosition, drumRadius, size);
  }

  void _checkPlanetHit(Offset tapPos, double drumRadius, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final rotationProgress = _rotationController.value;

    PlanetHologramData? closestPlanet;
    double minDistance = double.infinity;

    for (final planet in PlanetHologramData.allPlanets) {
      final orbitRadius = drumRadius * planet.orbitRatio;
      final currentAngle = planet.startAngle - (rotationProgress * 2 * math.pi * planet.turns);
      final planetPos = Offset(
        center.dx + math.cos(currentAngle) * orbitRadius,
        center.dy + math.sin(currentAngle) * orbitRadius,
      );

      // Nhận diện chạm thông minh (Generous Hitbox: ~30-36px quanh mỗi hành tinh)
      // Giúp người dùng chạm vào rất dễ dàng và chính xác kể cả trên màn hình cảm ứng điện thoại
      final hitRadius = math.max(planet.radius + 22.0, 36.0);
      final distance = (tapPos - planetPos).distance;
      if (distance <= hitRadius && distance < minDistance) {
        minDistance = distance;
        closestPlanet = planet;
      }
    }

    if (closestPlanet != null) {
      if (widget.onPlanetTap != null) {
        widget.onPlanetTap!(closestPlanet);
      } else {
        PlanetHologramInspectorDialog.show(context, closestPlanet);
      }
    }
  }

  bool _isOverAnyPlanet(Offset hoverPos, double drumRadius, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final rotationProgress = _rotationController.value;

    for (final planet in PlanetHologramData.allPlanets) {
      final orbitRadius = drumRadius * planet.orbitRatio;
      final currentAngle = planet.startAngle - (rotationProgress * 2 * math.pi * planet.turns);
      final planetPos = Offset(
        center.dx + math.cos(currentAngle) * orbitRadius,
        center.dy + math.sin(currentAngle) * orbitRadius,
      );
      final hitRadius = math.max(planet.radius + 22.0, 36.0);
      if ((hoverPos - planetPos).distance <= hitRadius) {
        return true;
      }
    }
    return false;
  }

  @override
  void initState() {
    super.initState();
    // Pulse controller for heartbeat and slow breathing waves (4.0s)
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 4000),
    );

    // Majestic slow rotation for the Trống Đồng drum (120s)
    _rotationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 120),
    );

    // Audio waveform animation controller for high-fidelity fluid acoustic motion (1.5s)
    _audioWaveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    if (!WidgetsBinding.instance.runtimeType.toString().contains('TestWidgetsFlutterBinding')) {
      _pulseController.repeat();
      _rotationController.repeat();
      _audioWaveController.repeat();
    }

    _setupVoiceListeners();
  }

  void _setupVoiceListeners() {
    _effectiveAudioLevelNotifier = widget.audioLevelNotifier ?? VoiceService().audioLevelNotifier;
    _effectiveVoiceActiveNotifier = widget.isVoiceActiveNotifier ?? VoiceService().isRecordingNotifier;

    _effectiveAudioLevelNotifier?.addListener(_onAudioLevelChanged);
    _effectiveVoiceActiveNotifier?.addListener(_onVoiceActiveChanged);

    _audioLevel = widget.audioLevel ?? _effectiveAudioLevelNotifier?.value ?? 0.0;
    _isVoiceActive = widget.isVoiceActive ?? _effectiveVoiceActiveNotifier?.value ?? false;
  }

  void _onAudioLevelChanged() {
    if (!mounted || widget.audioLevel != null) return;
    setState(() {
      _audioLevel = _effectiveAudioLevelNotifier?.value ?? 0.0;
    });
  }

  void _onVoiceActiveChanged() {
    if (!mounted || widget.isVoiceActive != null) return;
    setState(() {
      _isVoiceActive = _effectiveVoiceActiveNotifier?.value ?? false;
    });
  }

  @override
  void didUpdateWidget(covariant CyberCircuitBackground oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.audioLevelNotifier != oldWidget.audioLevelNotifier ||
        widget.isVoiceActiveNotifier != oldWidget.isVoiceActiveNotifier) {
      _effectiveAudioLevelNotifier?.removeListener(_onAudioLevelChanged);
      _effectiveVoiceActiveNotifier?.removeListener(_onVoiceActiveChanged);
      _setupVoiceListeners();
    }
  }

  @override
  void dispose() {
    _effectiveAudioLevelNotifier?.removeListener(_onAudioLevelChanged);
    _effectiveVoiceActiveNotifier?.removeListener(_onVoiceActiveChanged);
    _pulseController.dispose();
    _rotationController.dispose();
    _audioWaveController.dispose();
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
    final activeAudio = widget.audioLevel ?? _audioLevel;
    final activeVoice = widget.isVoiceActive ?? _isVoiceActive;

    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final h = constraints.maxHeight;
        // Drum size fits comfortably inside the center column; responsive on mobile
        final isMobile = w < 768;
        final drumSize = isMobile
            ? (math.min(w * 0.72, h * 0.44).clamp(220.0, 320.0))
            : (math.min(w * 0.46, h * 0.82).clamp(380.0, 780.0));
        final drumRadius = drumSize / 2;

        return MouseRegion(
          cursor: _isHoveringPlanet ? SystemMouseCursors.click : MouseCursor.defer,
          onHover: (event) {
            final isHover = _isOverAnyPlanet(event.localPosition, drumRadius, Size(w, h));
            if (isHover != _isHoveringPlanet) {
              setState(() => _isHoveringPlanet = isHover);
            }
          },
          child: Listener(
            behavior: HitTestBehavior.translucent,
            onPointerDown: _onPointerDown,
            onPointerUp: (event) => _onPointerUp(event, drumRadius, Size(w, h)),
            child: Stack(
              fit: StackFit.expand,
              children: [
            // 1. Ambient Deep Cyber Cosmic Gradient (Dark, sleek, non-intrusive)
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, _) {
                return CustomPaint(
                  painter: _SpaceAmbientPainter(pulseProgress: _pulseController.value),
                );
              },
            ),

            // 2. The Sacred Trống Đồng Holographic Drum Centerpiece
            // Subtle, controlled rim shadow (Giảm sáng xung quanh trống đồng - loại bỏ hào quang xanh loang rộng)
            AnimatedBuilder(
              animation: Listenable.merge([_pulseController, _rotationController]),
              builder: (context, _) {
                final pulse = math.sin(_pulseController.value * 2 * math.pi) * 0.5 + 0.5;
                final opacity = 0.32 + (pulse * 0.08); // Mờ dịu, thanh thoát theo yêu cầu (0.32 -> 0.40)
                final scale = 1.0 + (pulse * 0.010);

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
                              // Subtle, elegant rim illumination without large cyan/green halo
                              BoxShadow(
                                color: const Color(0xFFE5A93C).withValues(alpha: 0.12 + pulse * 0.06),
                                blurRadius: 18,
                                spreadRadius: 0,
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

            // 3. Centerpiece Audio Voice Visualizer (Thay thế hình Âm Dương)
            // Sóng âm thanh 360°, phổ tần số radial, vòng oscilloscope, và quả cầu voice ở tâm trống đồng
            AnimatedBuilder(
              animation: Listenable.merge([_pulseController, _audioWaveController]),
              builder: (context, _) {
                return CustomPaint(
                  painter: _AudioVoiceVisualizerPainter(
                    pulseProgress: _pulseController.value,
                    waveProgress: _audioWaveController.value,
                    drumRadius: drumRadius,
                    audioLevel: activeAudio,
                    isVoiceActive: activeVoice,
                    frequencyBands: widget.frequencyBands,
                  ),
                );
              },
            ),

            // 4. Concentric Drum Hologram Rings & Orbiting Solar System Planets Overlay (Nằm TRÊN hiệu ứng âm thanh)
            // Cho phép Sao Thủy (Mercury) và các hành tinh lướt nổi rõ ràng TRÊN sóng âm và hiệu ứng âm thanh
            AnimatedBuilder(
              animation: Listenable.merge([_pulseController, _rotationController]),
              builder: (context, _) {
                return CustomPaint(
                  painter: _HolographicLedRingsOverlayPainter(
                    pulseProgress: _pulseController.value,
                    rotationProgress: _rotationController.value,
                    drumRadius: drumRadius,
                  ),
                );
              },
            ),

            // 5. Optional interactive tap target for the center voice orb
            if (widget.onVoiceTap != null)
              Center(
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: widget.onVoiceTap,
                    behavior: HitTestBehavior.opaque,
                    child: Container(
                      width: (drumRadius * 0.20).clamp(46.0, 80.0) * 2,
                      height: (drumRadius * 0.20).clamp(46.0, 80.0) * 2,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.transparent,
                      ),
                    ),
                  ),
                ),
              ),

            // 6. Foreground Content (Cards & Chat)
            if (widget.child != null) widget.child!,
          ],
            ),
          ),
        );
      },
    );
  }
}

/// Paints the deep cosmic navy background with controlled, dark cyber ambience
class _SpaceAmbientPainter extends CustomPainter {
  final double pulseProgress;

  _SpaceAmbientPainter({required this.pulseProgress});

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final pulse = math.sin(pulseProgress * 2 * math.pi) * 0.5 + 0.5;

    // Deep, sleek, non-distracting cyber space gradient
    final bgGradient = RadialGradient(
      center: const Alignment(0.0, 0.0),
      radius: 1.05,
      colors: [
        Color.lerp(const Color(0xFF070E1C), const Color(0xFF0C1935), pulse)!,
        const Color(0xFF040814),
        const Color(0xFF020409),
      ],
      stops: const [0.0, 0.48, 1.0],
    );

    final bgPaint = Paint()..shader = bgGradient.createShader(rect);
    canvas.drawRect(rect, bgPaint);
  }

  @override
  bool shouldRepaint(covariant _SpaceAmbientPainter oldDelegate) {
    return oldDelegate.pulseProgress != pulseProgress;
  }
}

/// Dynamic Futuristic Audio Voice Visualizer Centerpiece
/// Replaces the old Yin-Yang with a multi-layered acoustic/voice visualizer:
/// 1. Concentric acoustic soundwave ripples expanding outward through the drum star rays.
/// 2. 360-degree radial frequency equalizer spectrum bars.
/// 3. Continuous circular oscilloscope wave ribbon.
/// 4. Central glass voice orb with dynamic vertical equalizer frequency bars.
class _AudioVoiceVisualizerPainter extends CustomPainter {
  final double pulseProgress;
  final double waveProgress;
  final double drumRadius;
  final double audioLevel;
  final bool isVoiceActive;
  final List<double>? frequencyBands;

  _AudioVoiceVisualizerPainter({
    required this.pulseProgress,
    required this.waveProgress,
    required this.drumRadius,
    required this.audioLevel,
    required this.isVoiceActive,
    this.frequencyBands,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    _drawVoiceVisualizer(canvas, center);
  }

  void _drawVoiceVisualizer(Canvas canvas, Offset center) {
    final pulse = math.sin(pulseProgress * 2 * math.pi) * 0.5 + 0.5;
    final coreRadius = (drumRadius * 0.22).clamp(36.0, 98.0);
    final orbRadius = coreRadius * 0.44;



    // 0. Dark Cyber Elevation Disc — Nằm đè lên lớp trống đồng, tạo độ sâu 3D
    // và bề mặt tương phản cao để toàn bộ cụm LED âm thanh nổi rõ rệt TRÊN mặt trống
    final backdropRadius = coreRadius * 1.04;
    final backdropRect = Rect.fromCircle(center: center, radius: backdropRadius);
    final backdropShader = RadialGradient(
      colors: [
        const Color(0xFF0F2242),
        const Color(0xFF071224),
        const Color(0xF5030713),
      ],
      stops: const [0.0, 0.65, 1.0],
    ).createShader(backdropRect);

    // Bóng đổ phía dưới đĩa để nâng cụm LED nổi bật hẳn trên mặt trống
    canvas.drawCircle(
      center,
      backdropRadius + 2.0,
      Paint()
        ..color = Colors.black.withValues(alpha: 0.65)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10.0),
    );

    // Đĩa nền tối tách biệt
    canvas.drawCircle(center, backdropRadius, Paint()..shader = backdropShader);

    // Viền phát sáng ngoài cùng của đĩa âm thanh
    canvas.drawCircle(
      center,
      backdropRadius,
      Paint()
        ..color = const Color(0xFF00F0FF).withValues(alpha: 0.45)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.2,
    );

    // Effective audio level calculation (smooth fallback to rhythmic breathing if idle)
    final effectiveLevel = isVoiceActive
        ? math.max(audioLevel, 0.28)
        : audioLevel.clamp(0.0, 1.0);

    // 1. Concentric Acoustic Soundwave Ripples (Sóng âm lan tỏa qua các cánh sao mặt trời)
    final rippleCount = isVoiceActive ? 4 : 3;
    for (int i = 0; i < rippleCount; i++) {
      final rippleOffset = (i / rippleCount);
      final rippleProgress = (pulseProgress + rippleOffset) % 1.0;
      final maxRadius = coreRadius + drumRadius * 0.38;
      final currentRadius = coreRadius * 0.8 + rippleProgress * (maxRadius - coreRadius * 0.8);
      final fade = math.sin(rippleProgress * math.pi);
      final rippleAlpha = fade * (0.10 + effectiveLevel * 0.25);

      final isGold = (i % 2 == 0);
      final color = isGold ? const Color(0xFFE5A93C) : const Color(0xFF00F0FF);

      final wavePaint = Paint()
        ..color = color.withValues(alpha: rippleAlpha.clamp(0.0, 0.45))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0 + (isVoiceActive ? 0.8 : 0.0);
      canvas.drawCircle(center, currentRadius, wavePaint);
    }

    // 2. Subtle Acoustic Core Energy Aura (Tập trung ở tâm, không loang ra ngoài)
    final auraRadius = coreRadius * (1.0 + effectiveLevel * 0.18 + pulse * 0.04);
    final auraPaint = Paint()
      ..color = const Color(0xFFE5A93C).withValues(alpha: 0.12 + effectiveLevel * 0.14)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12.0);
    canvas.drawCircle(center, auraRadius, auraPaint);

    final cyanAuraPaint = Paint()
      ..color = const Color(0xFF00F0FF).withValues(alpha: 0.08 + effectiveLevel * 0.12)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18.0);
    canvas.drawCircle(center, auraRadius * 0.85, cyanAuraPaint);

    // 3. Circular Oscilloscope Waveform Ribbon (Vòng sóng âm thanh tròn)
    final oscPath = Path();
    const oscPoints = 64;
    for (int p = 0; p <= oscPoints; p++) {
      final theta = (p / oscPoints) * 2 * math.pi;
      final wave1 = math.sin(theta * 6 + waveProgress * 2 * math.pi * 3);
      final wave2 = math.cos(theta * 10 - waveProgress * 2 * math.pi * 2);
      final waveAmp = (1.5 + effectiveLevel * 5.0) * ((wave1 + wave2) / 2);
      final r = (coreRadius * 0.90) + waveAmp;
      final pos = Offset(center.dx + math.cos(theta) * r, center.dy + math.sin(theta) * r);
      if (p == 0) {
        oscPath.moveTo(pos.dx, pos.dy);
      } else {
        oscPath.lineTo(pos.dx, pos.dy);
      }
    }
    oscPath.close();

    final oscPaint = Paint()
      ..color = const Color(0xFF00F0FF).withValues(alpha: 0.40 + effectiveLevel * 0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    canvas.drawPath(oscPath, oscPaint);

    // 4. Outer Boundary Track Ring & HUD Arcs
    final trackPaint = Paint()
      ..color = const Color(0xFFE5A93C).withValues(alpha: 0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    canvas.drawCircle(center, coreRadius, trackPaint);

    // Fine holographic dial ticks around core perimeter
    const tickCount = 24;
    final tickPaint = Paint()
      ..color = const Color(0xFFE5A93C).withValues(alpha: 0.45)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    for (int t = 0; t < tickCount; t++) {
      final angle = (t / tickCount) * 2 * math.pi;
      final p1 = Offset(center.dx + math.cos(angle) * (coreRadius - 2.0), center.dy + math.sin(angle) * (coreRadius - 2.0));
      final p2 = Offset(center.dx + math.cos(angle) * (coreRadius + 2.0), center.dy + math.sin(angle) * (coreRadius + 2.0));
      canvas.drawLine(p1, p2, tickPaint);
    }

    // 5. 360-Degree Radial Audio Spectrum Equalizer (36 thanh phổ tần số tỏa tròn)
    const barCount = 36;
    final innerR = orbRadius + 3.0;
    final maxBarLength = coreRadius - innerR - 2.0;

    for (int i = 0; i < barCount; i++) {
      final theta = (i / barCount) * 2 * math.pi;
      double barNorm;

      if (isVoiceActive || effectiveLevel > 0.05) {
        // Voice active: React dynamically to frequency bands / audio level
        final freqVal = (frequencyBands != null && i < frequencyBands!.length)
            ? frequencyBands![i]
            : (0.35 + 0.65 * math.sin(i * 1.6 + waveProgress * 12).abs());
        barNorm = (0.22 + 0.78 * freqVal * effectiveLevel).clamp(0.0, 1.0);
      } else {
        // Idle state: Harmonic breathing wave simulating voice standby
        final w1 = math.sin(theta * 3 + waveProgress * 2 * math.pi * 2);
        final w2 = math.cos(theta * 5 - waveProgress * 2 * math.pi * 3);
        final harmonic = ((w1 + w2) / 2).abs();
        barNorm = (0.20 + 0.42 * harmonic);
      }

      final barLength = 4.0 + (maxBarLength - 4.0) * barNorm;
      final startPos = Offset(center.dx + math.cos(theta) * innerR, center.dy + math.sin(theta) * innerR);
      final endPos = Offset(center.dx + math.cos(theta) * (innerR + barLength), center.dy + math.sin(theta) * (innerR + barLength));

      // Gradient color: Sacred Gold at base, Electric Cyan towards tip
      final barColor = Color.lerp(
        const Color(0xFFE5A93C),
        const Color(0xFF00F0FF),
        barNorm,
      )!;

      // Glowing aura pass for LED effect
      final glowPaint = Paint()
        ..color = barColor.withValues(alpha: (0.35 + barNorm * 0.40))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.8
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);
      canvas.drawLine(startPos, endPos, glowPaint);

      // Sharp core LED bar pass
      final barPaint = Paint()
        ..color = barColor.withValues(alpha: 0.85 + barNorm * 0.15)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.4
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(startPos, endPos, barPaint);

      // Bright white accent tip on active/peak bars
      if (barNorm > 0.55 || isVoiceActive) {
        final tipPaint = Paint()
          ..color = Colors.white.withValues(alpha: (barNorm * 0.9).clamp(0.0, 0.95))
          ..style = PaintingStyle.fill;
        canvas.drawCircle(endPos, 1.2, tipPaint);
      }
    }

    // 6. Central Voice Orb (Quả cầu âm thanh tâm điểm)
    // Deep cosmic glass disc
    final orbRect = Rect.fromCircle(center: center, radius: orbRadius);
    final orbGradient = RadialGradient(
      colors: [
        const Color(0xFF14294D),
        const Color(0xFF071124),
        const Color(0xFF030712),
      ],
      stops: const [0.0, 0.72, 1.0],
    );
    canvas.drawCircle(center, orbRadius, Paint()..shader = orbGradient.createShader(orbRect));

    // Golden boundary ring for the voice orb
    canvas.drawCircle(
      center,
      orbRadius,
      Paint()
        ..color = const Color(0xFFE5A93C).withValues(alpha: 0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.3,
    );

    // Inner subtle cyan holographic track
    canvas.drawCircle(
      center,
      orbRadius - 1.5,
      Paint()
        ..color = const Color(0xFF00F0FF).withValues(alpha: 0.35)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.8,
    );

    // 7. Internal Equalizer Waveform inside the Voice Orb (5 thanh đứng nhảy theo giọng nói)
    const eqBarCount = 5;
    const barW = 2.4;
    const barSpacing = 4.2;
    final totalW = (eqBarCount * barW) + ((eqBarCount - 1) * barSpacing);
    final startX = center.dx - (totalW / 2) + (barW / 2);
    final maxEqHeight = orbRadius * 1.05;

    for (int k = 0; k < eqBarCount; k++) {
      final x = startX + (k * (barW + barSpacing));
      final distFromCenter = (k - 2).abs() / 2.0; // 0.0 at center, 1.0 at edges
      final envelope = 1.0 - (distFromCenter * 0.40); // Natural curved equalizer envelope

      double heightFactor;
      if (isVoiceActive || effectiveLevel > 0.05) {
        final randWave = math.sin(k * 2.3 + waveProgress * 16).abs();
        heightFactor = (0.30 + 0.70 * randWave * effectiveLevel) * envelope;
      } else {
        final idleWave = math.sin(k * 1.5 + waveProgress * 2 * math.pi * 2).abs();
        final pulseWave = math.sin(pulseProgress * 2 * math.pi) * 0.5 + 0.5;
        heightFactor = (0.25 + 0.35 * idleWave + 0.15 * pulseWave) * envelope;
      }

      final barH = (4.0 + (maxEqHeight - 4.0) * heightFactor.clamp(0.10, 1.0));
      final barRect = RRect.fromRectAndRadius(
        Rect.fromCenter(center: Offset(x, center.dy), width: barW, height: barH),
        const Radius.circular(1.5),
      );

      final isCenterBar = (k == 2);
      final eqPaint = Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFFFFFFFF),
            Color(0xFF00F0FF),
            Color(0xFFE5A93C),
          ],
          stops: [0.0, 0.45, 1.0],
        ).createShader(barRect.outerRect);
      canvas.drawRRect(barRect, eqPaint);

      if (isCenterBar) {
        // Bright glowing center node
        canvas.drawCircle(
          Offset(x, center.dy),
          1.6,
          Paint()..color = Colors.white.withValues(alpha: 0.95),
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant _AudioVoiceVisualizerPainter oldDelegate) {
    return oldDelegate.pulseProgress != pulseProgress ||
        oldDelegate.waveProgress != waveProgress ||
        oldDelegate.drumRadius != drumRadius ||
        oldDelegate.audioLevel != audioLevel ||
        oldDelegate.isVoiceActive != isVoiceActive ||
        oldDelegate.frequencyBands != frequencyBands;
  }
}

typedef _PlanetSpec = PlanetHologramData;

/// Paints the Concentric Orbits and 8 Solar System Planets revolving around
/// the Sacred Trống Đồng Sun Axis (Mô phỏng 8 hành tinh Hệ Mặt Trời quay quanh tâm Trống Đồng)
class _HolographicLedRingsOverlayPainter extends CustomPainter {
  final double pulseProgress;
  final double rotationProgress;
  final double drumRadius;

  _HolographicLedRingsOverlayPainter({
    required this.pulseProgress,
    required this.rotationProgress,
    required this.drumRadius,
  });

  // 8 hành tinh Hệ Mặt Trời lồng ghép tương ứng theo các tầng hoa văn đồng tâm của Trống Đồng:
  // Tâm Trống Đồng (Mặt Trời) -> Sao Thủy -> Sao Kim -> Trái Đất -> Sao Hỏa -> Sao Mộc -> Sao Thổ -> Thiên Vương -> Hải Vương
  // Trục góc hội tụ hoàng đạo: -pi/3.8 (~ -47 độ, hướng Tây Bắc - Đông Nam của Trống Đồng)
  static const double _alignmentAxis = -math.pi / 3.8;

  // 8 hành tinh Hệ Mặt Trời (Thất Tinh cổ điển + Thiên Vương, Hải Vương hiện đại):
  static List<PlanetHologramData> get _solarPlanets => PlanetHologramData.allPlanets;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    _drawPlanetaryOrbitsAndCelestialBodies(canvas, center);
  }

  void _drawPlanetaryOrbitsAndCelestialBodies(Canvas canvas, Offset center) {
    // ── TÍNH TOÁN THỜI ĐIỂM THẤT TINH HỘI TỤ (Chu kỳ 60 giây) ──
    // Trong 120s của rotationController, hiện tượng xảy ra 2 lần:
    // - Tại 60s (progress = 0.5): Thẳng hàng đối xứng qua tâm Mặt Trời (Syzygy)
    // - Tại 120s (progress = 1.0 / 0.0): Toàn bộ 8 thiên thể xếp thẳng một tia duy nhất từ tâm Mặt Trời!
    final cycleProgress = (rotationProgress * 2.0) % 1.0;
    final distFromAlignment = math.min(cycleProgress, 1.0 - cycleProgress);
    final secondsToAlignment = ((1.0 - cycleProgress) * 60.0).clamp(0.0, 60.0);
    const alignmentWindow = 4.5 / 60.0; // Khoảng hội tụ rực rỡ kéo dài ~4.5 giây

    double alignmentIntensity = 0.0;
    if (distFromAlignment < alignmentWindow) {
      final norm = distFromAlignment / alignmentWindow;
      alignmentIntensity = (math.cos(norm * math.pi) * 0.5 + 0.5);
    }

    // 1. Vẽ các đường ray quỹ đạo đồng tâm (Concentric Orbital Tracks)
    for (int i = 0; i < _solarPlanets.length; i++) {
      final planet = _solarPlanets[i];
      final orbitRadius = drumRadius * planet.orbitRatio;

      final isCyanTrack = (i == 2 || i == 6);
      final trackColor = isCyanTrack ? const Color(0xFF00F0FF) : const Color(0xFFE5A93C);

      final trackPaint = Paint()
        ..color = trackColor.withValues(alpha: (i == 7) ? 0.13 : 0.09)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.9;
      canvas.drawCircle(center, orbitRadius, trackPaint);

      if (i % 2 == 0) {
        final counterAngle = -rotationProgress * 2 * math.pi * (1.0 + i * 0.25);
        final arcPaint = Paint()
          ..color = trackColor.withValues(alpha: 0.22)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2
          ..strokeCap = StrokeCap.round;

        const segments = 4;
        final sweepAngle = (math.pi / 7);
        for (int s = 0; s < segments; s++) {
          final startAngle = counterAngle + (s * (2 * math.pi / segments));
          canvas.drawArc(
            Rect.fromCircle(center: center, radius: orbitRadius),
            startAngle,
            sweepAngle,
            false,
            arcPaint,
          );
        }
      }
    }

    // Tính toán tọa độ chính xác của 8 hành tinh
    final planetPositions = <Offset>[];
    final planetAngles = <double>[];
    for (int i = 0; i < _solarPlanets.length; i++) {
      final planet = _solarPlanets[i];
      final orbitRadius = drumRadius * planet.orbitRatio;
      final currentAngle = planet.startAngle - (rotationProgress * 2 * math.pi * planet.turns);
      final pos = Offset(
        center.dx + math.cos(currentAngle) * orbitRadius,
        center.dy + math.sin(currentAngle) * orbitRadius,
      );
      planetPositions.add(pos);
      planetAngles.add(currentAngle);
    }

    // 2. MẠNG DÂY NĂNG LƯỢNG KẾT NỐI THẤT TINH (Constellation Quantum Web)
    // Nối từ Tâm Mặt Trời -> Thủy -> Kim -> Trái Đất -> Hỏa -> Mộc -> Thổ -> Thiên Vương -> Hải Vương
    _drawConstellationWeb(canvas, center, planetPositions, alignmentIntensity);

    // 3. KHI THẤT TINH HỘI TỤ (Alignment Resonance Laser Beam)
    if (alignmentIntensity > 0.02) {
      _drawAlignmentResonanceBeam(canvas, center, alignmentIntensity);
    }

    // 4. Vẽ 8 Hành tinh lướt trên quỹ đạo nhận ánh sáng từ Tâm Trống Đồng
    for (int i = 0; i < _solarPlanets.length; i++) {
      final planet = _solarPlanets[i];
      final orbitRadius = drumRadius * planet.orbitRatio;
      final currentAngle = planetAngles[i];
      final pos = planetPositions[i];

      // A. Vết đuôi quỹ đạo chuyển động lướt
      _drawOrbitalTrail(canvas, center, orbitRadius, currentAngle, planet.glowColor);

      // B. Hào quang khí quyển mềm (khi hội tụ hào quang bừng sáng)
      final auraRadius = planet.radius + 4.0 + (alignmentIntensity * 6.0);
      canvas.drawCircle(
        pos,
        auraRadius,
        Paint()
          ..color = planet.glowColor.withValues(alpha: 0.34 + (alignmentIntensity * 0.40))
          ..maskFilter = MaskFilter.blur(BlurStyle.normal, 4.5 + (alignmentIntensity * 4.0)),
      );

      // Khi hội tụ: Vòng sóng xung kích mở rộng tại mỗi hành tinh
      if (alignmentIntensity > 0.10) {
        canvas.drawCircle(
          pos,
          planet.radius * (1.3 + (1.0 - alignmentIntensity) * 1.8),
          Paint()
            ..color = planet.glowColor.withValues(alpha: alignmentIntensity * 0.55)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.4,
        );
      }

      // C. Quả cầu hành tinh 3D
      _drawPlanetSphere(canvas, center, pos, planet);

      // D. Các đặc điểm thiên văn đặc trưng
      if (planet.hasMoon) {
        _drawEarthMoon(canvas, pos, planet.radius);
      } else if (planet.hasStripes) {
        _drawJupiterStripes(canvas, pos, planet.radius);
      } else if (planet.hasRings) {
        _drawSaturnRings(canvas, pos, planet.radius);
      } else if (planet.hasPolarCap) {
        _drawMarsPolarCap(canvas, pos, planet.radius);
      } else if (planet.hasVerticalRing) {
        _drawUranusRing(canvas, pos, planet.radius);
      }

      // E. Nhãn tên Cyber HUD
      _drawPlanetLabel(canvas, pos, planet);
    }

    // 5. HUD ĐẾM NGƯỢC & CHỈ SỐ THẤT TINH HỘI TỤ
    _drawConvergenceHud(canvas, center, alignmentIntensity, secondsToAlignment);
  }

  /// Mạng dây năng lượng kết nối các hành tinh với Tâm Mặt Trời
  void _drawConstellationWeb(Canvas canvas, Offset center, List<Offset> positions, double alignmentIntensity) {
    final webColor = Color.lerp(
      const Color(0xFF00F0FF),
      const Color(0xFFE5A93C),
      alignmentIntensity,
    )!;

    final path = Path()..moveTo(center.dx, center.dy);
    for (final p in positions) {
      path.lineTo(p.dx, p.dy);
    }

    // Dây liên kết mềm mờ (hơi phát sáng khi tiến gần hội tụ)
    canvas.drawPath(
      path,
      Paint()
        ..color = webColor.withValues(alpha: 0.12 + (alignmentIntensity * 0.35))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0 + (alignmentIntensity * 1.5)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, 1.5 + (alignmentIntensity * 2.5)),
    );

    // Hạt photon lượng tử lướt theo các đoạn nối từ tâm Mặt Trời ra các hành tinh
    for (int k = 0; k < positions.length; k++) {
      final p1 = (k == 0) ? center : positions[k - 1];
      final p2 = positions[k];
      final photonT = (pulseProgress + k * 0.13) % 1.0;
      final photonPos = Offset.lerp(p1, p2, photonT)!;

      canvas.drawCircle(
        photonPos,
        1.6 + (alignmentIntensity * 1.2),
        Paint()..color = Colors.white.withValues(alpha: 0.85),
      );
      canvas.drawCircle(
        photonPos,
        3.2 + (alignmentIntensity * 2.0),
        Paint()
          ..color = webColor.withValues(alpha: 0.45)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.8),
      );
    }
  }

  /// Trục chùm tia năng lượng laser thần thánh xuyên tâm Trống Đồng khi Thất Tinh Hội Tụ
  void _drawAlignmentResonanceBeam(Canvas canvas, Offset center, double intensity) {
    final dir = Offset(math.cos(_alignmentAxis), math.sin(_alignmentAxis));
    final beamLength = drumRadius * 1.35;
    final p1 = center - (dir * beamLength);
    final p2 = center + (dir * beamLength);

    // Lớp 1: Hào quang vàng hổ phách rộng
    canvas.drawLine(
      p1,
      p2,
      Paint()
        ..color = const Color(0xFFE5A93C).withValues(alpha: intensity * 0.45)
        ..strokeWidth = 16.0 * intensity
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10.0),
    );

    // Lớp 2: Luồng plasma lượng tử Quantum Cyan
    canvas.drawLine(
      p1,
      p2,
      Paint()
        ..color = const Color(0xFF00F0FF).withValues(alpha: intensity * 0.75)
        ..strokeWidth = 4.5 * intensity
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3.5),
    );

    // Lớp 3: Lõi laser trắng thuần khiết
    canvas.drawLine(
      p1,
      p2,
      Paint()
        ..color = Colors.white.withValues(alpha: intensity * 0.95)
        ..strokeWidth = 1.8 * intensity,
    );

    // Đợt sóng xung kích Mặt Trời (Solar Flare Shockwave) mở rộng từ tâm
    final shockRadius = (drumRadius * 0.22) + ((1.0 - intensity) * drumRadius * 0.85);
    canvas.drawCircle(
      center,
      shockRadius,
      Paint()
        ..color = const Color(0xFFF59E0B).withValues(alpha: intensity * 0.40)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0 * intensity,
    );
  }

  /// HUD hiển thị đếm ngược chu kỳ hoặc thông báo Thất Tinh Hội Tụ
  void _drawConvergenceHud(Canvas canvas, Offset center, double alignmentIntensity, double secondsLeft) {
    final isConverged = alignmentIntensity > 0.18;
    final hudText = isConverged
        ? '⚡ THẤT DIỆU HỘI TỤ • CỘNG HƯỞNG THIÊN HÀ'
        : '⏳ Thất Tinh Hội Tụ: ${secondsLeft.toInt().toString().padLeft(2, '0')}s';

    final textSpan = TextSpan(
      text: hudText,
      style: TextStyle(
        color: isConverged
            ? const Color(0xFFFEF08A)
            : const Color(0xFF00F0FF).withValues(alpha: 0.70),
        fontSize: isConverged ? 10.5 : 9.0,
        fontWeight: isConverged ? FontWeight.bold : FontWeight.w500,
        letterSpacing: 0.8,
        shadows: isConverged
            ? [
                const Shadow(color: Colors.black, blurRadius: 4.0),
                const Shadow(color: Color(0xFFE5A93C), blurRadius: 8.0),
              ]
            : [
                const Shadow(color: Colors.black, blurRadius: 3.0),
              ],
      ),
    );

    final tp = TextPainter(text: textSpan, textDirection: TextDirection.ltr);
    tp.layout();

    // Vị trí đặt ở phía trên đỉnh của Trống Đồng
    final hudY = center.dy - (drumRadius * 1.18);
    final hudRect = Rect.fromCenter(
      center: Offset(center.dx, hudY),
      width: tp.width + 18,
      height: tp.height + 8,
    );

    if (isConverged) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(hudRect, const Radius.circular(8)),
        Paint()..color = const Color(0xFF0F172A).withValues(alpha: 0.75),
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(hudRect, const Radius.circular(8)),
        Paint()
          ..color = const Color(0xFFE5A93C).withValues(alpha: alignmentIntensity * 0.85)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.0,
      );
    }

    tp.paint(canvas, Offset(center.dx - (tp.width / 2), hudY - (tp.height / 2)));
  }

  /// Vẽ vết đuôi mờ lướt nhẹ theo sau hành tinh
  void _drawOrbitalTrail(Canvas canvas, Offset center, double orbitRadius, double currentAngle, Color color) {
    const trailSweep = math.pi / 11; // ~16 độ
    final trailPaint = Paint()
      ..color = color.withValues(alpha: 0.26)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: orbitRadius),
      currentAngle,
      trailSweep,
      false,
      trailPaint,
    );
  }

  /// Vẽ quả cầu 3D với hướng chiếu sáng tự nhiên xuất phát từ Tâm Trống Đồng (Mặt Trời)
  void _drawPlanetSphere(Canvas canvas, Offset center, Offset pos, _PlanetSpec planet) {
    final sunAngle = math.atan2(pos.dy - center.dy, pos.dx - center.dx);
    final planetRect = Rect.fromCircle(center: pos, radius: planet.radius);

    final sphereGradient = RadialGradient(
      center: Alignment(
        -math.cos(sunAngle) * 0.48,
        -math.sin(sunAngle) * 0.48,
      ),
      radius: 0.95,
      colors: [
        Colors.white.withValues(alpha: 0.95),
        planet.primaryColor,
        planet.darkColor,
      ],
      stops: const [0.0, 0.42, 1.0],
    );

    canvas.drawCircle(
      pos,
      planet.radius,
      Paint()..shader = sphereGradient.createShader(planetRect),
    );
  }

  /// Trái Đất: Vệt mây xoáy và Mặt Trăng tí hon quay quanh
  void _drawEarthMoon(Canvas canvas, Offset pos, double earthRadius) {
    // Vệt mây xoáy nhẹ trên bề mặt
    canvas.drawCircle(
      Offset(pos.dx - 1.6, pos.dy - 0.8),
      2.2,
      Paint()..color = Colors.white.withValues(alpha: 0.55),
    );

    // Mặt Trăng quay quanh Trái Đất
    final moonDist = earthRadius * 2.2;
    final moonAngle = -(rotationProgress * 2 * math.pi * 32);
    final moonPos = Offset(
      pos.dx + math.cos(moonAngle) * moonDist,
      pos.dy + math.sin(moonAngle) * moonDist,
    );

    // Quỹ đạo Mặt Trăng
    canvas.drawCircle(
      pos,
      moonDist,
      Paint()
        ..color = Colors.white.withValues(alpha: 0.12)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.8,
    );

    // Quả cầu Mặt Trăng
    canvas.drawCircle(
      moonPos,
      2.2,
      Paint()..color = const Color(0xFFF1F5F9),
    );
    canvas.drawCircle(
      moonPos,
      3.2,
      Paint()
        ..color = Colors.white.withValues(alpha: 0.45)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.8),
    );
  }

  /// Sao Mộc: Dải mây khí quyển caramel & Đốm Đỏ Lớn (Great Red Spot)
  void _drawJupiterStripes(Canvas canvas, Offset pos, double jupiterRadius) {
    final planetRect = Rect.fromCircle(center: pos, radius: jupiterRadius);
    canvas.save();
    canvas.clipPath(Path()..addOval(planetRect));

    // Dải mây xích đạo
    canvas.drawRect(
      Rect.fromCenter(center: Offset(pos.dx, pos.dy - 2.6), width: jupiterRadius * 2.4, height: 2.8),
      Paint()..color = const Color(0xFF92400E).withValues(alpha: 0.72),
    );
    canvas.drawRect(
      Rect.fromCenter(center: Offset(pos.dx, pos.dy + 2.6), width: jupiterRadius * 2.4, height: 2.4),
      Paint()..color = const Color(0xFFB45309).withValues(alpha: 0.62),
    );

    // Đốm Đỏ Lớn
    canvas.drawCircle(
      Offset(pos.dx + 3.6, pos.dy + 2.6),
      2.4,
      Paint()..color = const Color(0xFFDC2626).withValues(alpha: 0.92),
    );

    canvas.restore();
  }

  /// Sao Thổ: Vành đai Thổ tinh (Saturn's Ring Belt) nghiêng 25°
  void _drawSaturnRings(Canvas canvas, Offset pos, double saturnRadius) {
    canvas.save();
    canvas.translate(pos.dx, pos.dy);
    canvas.rotate(math.pi / 7.2); // Góc nghiêng thanh nhã ~25°

    // Vành đai ngoài (Vành A)
    canvas.drawOval(
      Rect.fromCenter(center: Offset.zero, width: saturnRadius * 4.2, height: saturnRadius * 1.5),
      Paint()
        ..color = const Color(0xFFFDE68A).withValues(alpha: 0.76)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.8,
    );

    // Vành đai trong (Vành B)
    canvas.drawOval(
      Rect.fromCenter(center: Offset.zero, width: saturnRadius * 2.9, height: saturnRadius * 1.0),
      Paint()
        ..color = const Color(0xFFCA8A04).withValues(alpha: 0.55)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.8,
    );

    canvas.restore();
  }

  /// Sao Hỏa: Chỏm băng trắng ở cực Bắc
  void _drawMarsPolarCap(Canvas canvas, Offset pos, double marsRadius) {
    canvas.drawCircle(
      Offset(pos.dx, pos.dy - marsRadius * 0.65),
      1.6,
      Paint()..color = Colors.white.withValues(alpha: 0.92),
    );
  }

  /// Sao Thiên Vương: Vành đai băng giá đứng nghiêng
  void _drawUranusRing(Canvas canvas, Offset pos, double uranusRadius) {
    canvas.save();
    canvas.translate(pos.dx, pos.dy);
    canvas.rotate(math.pi / 2.3);

    canvas.drawOval(
      Rect.fromCenter(center: Offset.zero, width: uranusRadius * 3.0, height: uranusRadius * 0.9),
      Paint()
        ..color = const Color(0xFFA5F3FC).withValues(alpha: 0.45)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4,
    );

    canvas.restore();
  }

  /// Nhãn tên Cyber HUD rõ ràng, sắc nét và nổi bật bên cạnh hành tinh
  void _drawPlanetLabel(Canvas canvas, Offset pos, _PlanetSpec planet) {
    final textSpan = TextSpan(
      text: planet.nameVi,
      style: TextStyle(
        color: Colors.white.withValues(alpha: 0.92),
        fontSize: 11.5,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.4,
        shadows: [
          const Shadow(
            color: Colors.black,
            blurRadius: 4.0,
            offset: Offset(0, 1),
          ),
          Shadow(
            color: planet.glowColor.withValues(alpha: 0.75),
            blurRadius: 6.0,
          ),
        ],
      ),
    );

    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();

    final labelOffset = Offset(
      pos.dx + planet.radius + 6.0,
      pos.dy - (textPainter.height / 2),
    );

    textPainter.paint(canvas, labelOffset);
  }

  @override
  bool shouldRepaint(covariant _HolographicLedRingsOverlayPainter oldDelegate) {
    return oldDelegate.pulseProgress != pulseProgress ||
        oldDelegate.rotationProgress != rotationProgress ||
        oldDelegate.drumRadius != drumRadius;
  }
}
