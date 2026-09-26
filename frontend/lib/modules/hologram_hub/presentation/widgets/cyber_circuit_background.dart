import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../../../core/services/voice_service.dart';

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

  const CyberCircuitBackground({
    super.key,
    this.child,
    this.isVoiceActive,
    this.audioLevel,
    this.frequencyBands,
    this.audioLevelNotifier,
    this.isVoiceActiveNotifier,
    this.onVoiceTap,
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
        // Drum size fits comfortably inside the 6/12 center column
        final drumSize = math.min(w * 0.46, h * 0.82).clamp(380.0, 780.0);
        final drumRadius = drumSize / 2;

        return Stack(
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

            // 3. Concentric Drum Hologram Rings & Orbiting Photons Overlay (On top of Trống Đồng)
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

            // 4. Centerpiece Audio Voice Visualizer (Thay thế hình Âm Dương)
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
    final coreRadius = (drumRadius * 0.23).clamp(58.0, 98.0);
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
      drumRadius * 0.99, // Outer drum rim boundary (inside drum edge to prevent halo bleed)
    ];

    final ringColors = [
      const Color(0xFFE5A93C), // Sacred Bronze Gold
      const Color(0xFF00F0FF), // Quantum Cyan
      const Color(0xFFF59E0B), // Solar Amber
      const Color(0xFFE5A93C), // Sacred Bronze Gold rim (softened from emerald green)
    ];

    for (int i = 0; i < ringRadii.length; i++) {
      final r = ringRadii[i];
      final color = ringColors[i];

      // Base Track Ring
      final ringPaint = Paint()
        ..color = color.withValues(alpha: (i == 3) ? 0.15 : 0.12)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.1;
      canvas.drawCircle(center, r, ringPaint);

      // Counter-rotating Segmented Hologram HUD Arcs
      final counterAngle = -rotationProgress * 2 * math.pi * (1.1 + i * 0.3);
      final arcPaint = Paint()
        ..color = color.withValues(alpha: 0.28)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4
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
        2.2,
        Paint()..color = Colors.white.withValues(alpha: 0.90),
      );

      // Subtle Glowing Halo (tight blur 2.0 to avoid outer glare)
      canvas.drawCircle(
        pos,
        4.0,
        Paint()
          ..color = color.withValues(alpha: 0.35)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.0),
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
