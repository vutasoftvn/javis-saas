import 'package:flutter/material.dart';
import 'audio_waveform_painter.dart';
import 'miva_hologram_core.dart';

/// Dedicated Mobile Command Bar component for COSA Hologram Hub.
///
/// Fully color-synchronized with the central Hologram Brain:
/// - Dynamic spectrum cycling & state-aware primary/secondary/accent colors
/// - Rotating holographic gradient border rings
/// - Multi-layer cosmic aura & breathing glow shadows
/// - Dual-tone shader icons (Keyboard & Mic / Stop)
/// - Top Audio Waveform Banner when realtime voice or voice listening is active
///
/// Modes:
/// 1. Default Mode (isChatInputActive == false):
///    - Left: Keyboard Icon Button (opens chat input, animates orb to top 32px @ 0.5 scale)
///    - Right: Voice Mic / Stop Hero Button (starts listening or stops realtime voice)
///    - Above: Active Audio Waveform Banner indicating Listening/Speaking/Thinking state
///
/// 2. Chat Input Mode (isChatInputActive == true):
///    - Left: Close button (dismisses chat bar, animates orb back to center)
///    - Center: Text input field for COSA
///    - Right: Send / Mic / Stop button
class MobileCommandBar extends StatefulWidget {
  final HologramRuntimeState runtimeState;
  final bool isChatInputActive;
  final bool isVoiceListening;
  final bool isConversationModeActive;
  final VoidCallback onOpenChat;
  final VoidCallback onCloseChat;
  final VoidCallback onVoiceTap;
  final VoidCallback? onVoiceLongPress;
  final Function(String query) onSubmit;

  const MobileCommandBar({
    super.key,
    this.runtimeState = HologramRuntimeState.idle,
    required this.isChatInputActive,
    this.isVoiceListening = false,
    this.isConversationModeActive = false,
    required this.onOpenChat,
    required this.onCloseChat,
    required this.onVoiceTap,
    this.onVoiceLongPress,
    required this.onSubmit,
  });

  @override
  State<MobileCommandBar> createState() => _MobileCommandBarState();
}

class _MobileCommandBarState extends State<MobileCommandBar>
    with TickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  late AnimationController _pulseAnimController;
  late AnimationController _hueController;
  late AnimationController _orbitController;
  late AnimationController _waveAnimController;

  @override
  void initState() {
    super.initState();
    // Heartbeat / breathing pulse synchronized with brain (2200ms)
    _pulseAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);

    // Spectrum hue cycle synchronized with brain (16s)
    _hueController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 16),
    )..repeat();

    // Subtle orbital rotation for gradient borders (12s)
    _orbitController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..repeat();

    // Fluid audio waveform frequency animation (1200ms)
    _waveAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void didUpdateWidget(MobileCommandBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isChatInputActive && !oldWidget.isChatInputActive) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _focusNode.requestFocus();
      });
    } else if (!widget.isChatInputActive && oldWidget.isChatInputActive) {
      _focusNode.unfocus();
      _controller.clear();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _pulseAnimController.dispose();
    _hueController.dispose();
    _orbitController.dispose();
    _waveAnimController.dispose();
    super.dispose();
  }

  void _handleSubmitted(String text) {
    if (text.trim().isNotEmpty) {
      widget.onSubmit(text.trim());
      _controller.clear();
    }
  }

  /// Computes dynamic primary, secondary, and accent colors matching MivaHologramCore
  ({Color primary, Color secondary, Color accent}) _resolveDynamicPalette() {
    final double hueProgress = _hueController.value;
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

    switch (widget.runtimeState) {
      case HologramRuntimeState.listening:
        return (
          primary: const Color(0xFF14B8A6),
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
          secondary: const Color(0xFF14B8A6),
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
        return (
          primary: dynamicRainbowColor,
          secondary: secondaryDynamicColor,
          accent: accentDynamicColor,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (child, animation) {
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.15),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        );
      },
      child: widget.isChatInputActive
          ? _buildChatInputBar(key: const ValueKey('chat_input_bar'))
          : _buildTwoIconsBar(key: const ValueKey('two_icons_bar')),
    );
  }

  /// ── Mode 1: Two Standard Action Icons (Keyboard & Voice) ───────────────
  Widget _buildTwoIconsBar({required Key key}) {
    return AnimatedBuilder(
      key: key,
      animation: Listenable.merge([
        _pulseAnimController,
        _hueController,
        _waveAnimController,
      ]),
      builder: (context, child) {
        final palette = _resolveDynamicPalette();
        final pulse = _pulseAnimController.value;
        final isVoiceActive = widget.isConversationModeActive ||
            widget.isVoiceListening ||
            widget.runtimeState == HologramRuntimeState.listening ||
            widget.runtimeState == HologramRuntimeState.speaking ||
            widget.runtimeState == HologramRuntimeState.thinking ||
            widget.runtimeState == HologramRuntimeState.acting ||
            widget.runtimeState == HologramRuntimeState.retrieving;

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // 0. Audio Waveform Banner above 2 icons when realtime voice or voice listening is active
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  return FadeTransition(
                    opacity: animation,
                    child: SizeTransition(
                      sizeFactor: animation,
                      child: Center(child: child),
                    ),
                  );
                },
                child: isVoiceActive
                    ? _buildAudioWaveformBanner(palette, pulse)
                    : const SizedBox.shrink(),
              ),

              // 1. Two Icon Buttons Row (Keyboard & Voice Stop/Mic)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Left Icon Button: Keyboard (Cyan / palette.primary)
                  Tooltip(
                    message: 'Mở khung chat (Bàn phím)',
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: widget.onOpenChat,
                        borderRadius: BorderRadius.circular(100),
                        splashColor: palette.primary.withValues(alpha: 0.3),
                        highlightColor: palette.primary.withValues(alpha: 0.15),
                        child: Container(
                          width: 56,
                          height: 56,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: const Color(0xFF0D172A).withValues(alpha: 0.88),
                            border: Border.all(
                              color: palette.primary.withValues(alpha: 0.55),
                              width: 1.2,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: palette.primary.withValues(
                                  alpha: 0.20 + 0.10 * pulse,
                                ),
                                blurRadius: 16 + 4 * pulse,
                                spreadRadius: 1,
                                offset: const Offset(0, 2),
                              ),
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.5),
                                blurRadius: 10,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Icon(
                            Icons.keyboard_alt_outlined,
                            color: palette.primary,
                            size: 26,
                          ),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(width: 36),

                  // Right Icon Button: Voice Mic / Stop Hero Button
                  Tooltip(
                    message: isVoiceActive
                        ? (widget.isConversationModeActive
                            ? 'Dừng hội thoại realtime (Chạm để dừng)'
                            : 'Dừng lắng nghe (Chạm để gửi)')
                        : 'Chạm: Voice nhanh · Giữ: Chế độ hội thoại',
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: widget.onVoiceTap,
                        onLongPress: widget.onVoiceLongPress,
                        borderRadius: BorderRadius.circular(100),
                        splashColor: (isVoiceActive ? palette.accent : palette.secondary)
                            .withValues(alpha: 0.35),
                        highlightColor: (isVoiceActive ? palette.accent : palette.secondary)
                            .withValues(alpha: 0.15),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 250),
                          width: isVoiceActive ? 62 : 56,
                          height: isVoiceActive ? 62 : 56,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: isVoiceActive
                                ? LinearGradient(
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                    colors: [
                                      palette.primary,
                                      palette.accent,
                                    ],
                                  )
                                : null,
                            color: isVoiceActive
                                ? null
                                : const Color(0xFF0D172A).withValues(alpha: 0.88),
                            border: Border.all(
                              color: isVoiceActive
                                  ? palette.accent
                                  : palette.secondary.withValues(alpha: 0.55),
                              width: isVoiceActive ? 1.8 : 1.2,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: (isVoiceActive
                                        ? palette.accent
                                        : palette.secondary)
                                    .withValues(
                                        alpha: isVoiceActive
                                            ? (0.45 + 0.25 * pulse)
                                            : (0.20 + 0.10 * pulse)),
                                blurRadius: isVoiceActive ? (20 + 8 * pulse) : (16 + 4 * pulse),
                                spreadRadius: isVoiceActive ? (2 + 2 * pulse) : 1,
                                offset: const Offset(0, 2),
                              ),
                              if (!isVoiceActive)
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.5),
                                  blurRadius: 10,
                                  offset: const Offset(0, 4),
                                ),
                            ],
                          ),
                          child: Icon(
                            isVoiceActive ? Icons.stop_rounded : Icons.mic_rounded,
                            color: isVoiceActive
                                ? const Color(0xFF04070E)
                                : palette.secondary,
                            size: isVoiceActive ? 32 : 26,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  /// ── Audio Waveform Visualizer Banner above the 2 Action Icons ───────────
  Widget _buildAudioWaveformBanner(
    ({Color primary, Color secondary, Color accent}) palette,
    double pulse,
  ) {
    final String statusText;
    final Color stateColor;
    final IconData statusIcon;

    if (widget.runtimeState == HologramRuntimeState.speaking) {
      statusText = 'COSA đang nói...';
      stateColor = palette.accent;
      statusIcon = Icons.volume_up_rounded;
    } else if (widget.runtimeState == HologramRuntimeState.thinking ||
        widget.runtimeState == HologramRuntimeState.acting ||
        widget.runtimeState == HologramRuntimeState.retrieving) {
      statusText = 'Đang suy nghĩ...';
      stateColor = palette.secondary;
      statusIcon = Icons.psychology_outlined;
    } else if (widget.runtimeState == HologramRuntimeState.listening ||
        widget.isVoiceListening) {
      statusText = 'Đang lắng nghe...';
      stateColor = palette.primary;
      statusIcon = Icons.mic_rounded;
    } else if (widget.isConversationModeActive) {
      statusText = 'Đang lắng nghe...';
      stateColor = palette.primary;
      statusIcon = Icons.mic_rounded;
    } else {
      statusText = 'Đang lắng nghe...';
      stateColor = palette.primary;
      statusIcon = Icons.mic_rounded;
    }

    return Center(
      child: Container(
        key: const ValueKey('audio_waveform_banner'),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0xFF070D1E).withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(
          color: stateColor.withValues(alpha: 0.55),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: stateColor.withValues(alpha: 0.25 + 0.15 * pulse),
            blurRadius: 16 + 6 * pulse,
            spreadRadius: 1,
            offset: const Offset(0, 2),
          ),
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.6),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            statusIcon,
            color: stateColor,
            size: 15,
          ),
          const SizedBox(width: 6),
          Text(
            statusText,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.3,
            ),
          ),
          const SizedBox(width: 10),
          // Dynamic Waveform Visualizer
          SizedBox(
            width: 72,
            height: 18,
            child: CustomPaint(
              painter: AudioWaveformPainter(
                animationValue: _waveAnimController.value,
                primaryColor: stateColor,
                secondaryColor: palette.secondary,
                barCount: 14,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

  /// ── Mode 2: Chat Input Bar with Delete/Close Icon ───────────────────────
  Widget _buildChatInputBar({required Key key}) {
    return AnimatedBuilder(
      key: key,
      animation: Listenable.merge([
        _pulseAnimController,
        _hueController,
        _orbitController,
      ]),
      builder: (context, child) {
        final palette = _resolveDynamicPalette();
        final pulse = _pulseAnimController.value;

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Container(
            height: 52,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  palette.primary.withValues(alpha: 0.65),
                  palette.secondary.withValues(alpha: 0.45),
                  palette.accent.withValues(alpha: 0.65),
                ],
              ),
              borderRadius: BorderRadius.circular(100),
              boxShadow: [
                BoxShadow(
                  color: palette.primary.withValues(alpha: 0.20 + 0.10 * pulse),
                  blurRadius: 18 + 4 * pulse,
                  spreadRadius: 1,
                  offset: const Offset(0, 3),
                ),
                BoxShadow(
                  color: palette.secondary.withValues(alpha: 0.15),
                  blurRadius: 12,
                  offset: const Offset(0, 2),
                ),
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.5),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            padding: const EdgeInsets.all(1.2), // Gradient border
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(100),
                gradient: const RadialGradient(
                  center: Alignment(0.0, -0.2),
                  radius: 1.5,
                  colors: [
                    Color(0xFF0F1E38),
                    Color(0xFF0A1224),
                    Color(0xFF050914),
                  ],
                ),
              ),
              child: Row(
                children: [
                  // Left: "Icon xoá" / Close chat bar
                  const SizedBox(width: 6),
                  Tooltip(
                    message: 'Đóng khung chat',
                    child: GestureDetector(
                      onTap: () {
                        _focusNode.unfocus();
                        _controller.clear();
                        widget.onCloseChat();
                      },
                      child: Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                          border: Border.all(
                            color: const Color(0xFFEF4444).withValues(alpha: 0.45),
                            width: 1,
                          ),
                        ),
                        child: const Center(
                          child: Icon(
                            Icons.close_rounded,
                            color: Color(0xFFF87171),
                            size: 19,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Center: Text field
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      focusNode: _focusNode,
                      keyboardType: TextInputType.text,
                      textInputAction: TextInputAction.send,
                      textCapitalization: TextCapitalization.sentences,
                      autocorrect: true,
                      enableSuggestions: true,
                      onSubmitted: _handleSubmitted,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                      decoration: InputDecoration(
                        hintText: 'Nói với COSA...',
                        hintStyle: TextStyle(
                          color: const Color(0xFF94A3B8).withValues(alpha: 0.8),
                          fontSize: 14,
                        ),
                        filled: false,
                        fillColor: Colors.transparent,
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 4,
                          vertical: 10,
                        ),
                        isDense: true,
                      ),
                    ),
                  ),

                  // Right: Send action or Mic
                  ValueListenableBuilder<TextEditingValue>(
                    valueListenable: _controller,
                    builder: (context, value, child) {
                      final hasText = value.text.trim().isNotEmpty;
                      if (hasText) {
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: GestureDetector(
                            onTap: () => _handleSubmitted(_controller.text),
                            child: Container(
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: LinearGradient(
                                  colors: [
                                    palette.primary,
                                    palette.secondary,
                                  ],
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: palette.primary.withValues(alpha: 0.4),
                                    blurRadius: 8,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                              child: const Center(
                                child: Icon(
                                  Icons.arrow_upward_rounded,
                                  color: Color(0xFF04070E),
                                  size: 20,
                                ),
                              ),
                            ),
                          ),
                        );
                      }
                      final isVoiceActive = widget.isConversationModeActive ||
                          widget.isVoiceListening ||
                          widget.runtimeState == HologramRuntimeState.listening ||
                          widget.runtimeState == HologramRuntimeState.speaking;

                      return IconButton(
                        icon: ShaderMask(
                          shaderCallback: (bounds) => LinearGradient(
                            colors: isVoiceActive
                                ? [const Color(0xFFEF4444), const Color(0xFFF87171)]
                                : [palette.primary, palette.accent],
                          ).createShader(bounds),
                          child: Icon(
                            isVoiceActive
                                ? Icons.stop_rounded
                                : Icons.mic_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                        tooltip: isVoiceActive
                            ? (widget.isConversationModeActive
                                ? 'Dừng hội thoại realtime'
                                : 'Dừng nghe')
                            : 'Nói với COSA (Voice)',
                        onPressed: widget.onVoiceTap,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 40,
                          minHeight: 40,
                        ),
                      );
                    },
                  ),
                  const SizedBox(width: 4),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

