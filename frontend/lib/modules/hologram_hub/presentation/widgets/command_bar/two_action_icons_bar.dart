import 'package:flutter/material.dart';
import '../miva_hologram_core.dart';
import 'command_waveform_banner.dart';
import 'hologram_palette_helper.dart';

class TwoActionIconsBar extends StatelessWidget {
  final HologramRuntimeState runtimeState;
  final bool isVoiceListening;
  final bool isConversationModeActive;
  final VoidCallback onOpenChat;
  final VoidCallback onVoiceTap;
  final VoidCallback? onVoiceLongPress;
  final HologramPalette palette;
  final double pulse;
  final AnimationController waveAnimController;

  const TwoActionIconsBar({
    super.key,
    required this.runtimeState,
    required this.isVoiceListening,
    required this.isConversationModeActive,
    required this.onOpenChat,
    required this.onVoiceTap,
    this.onVoiceLongPress,
    required this.palette,
    required this.pulse,
    required this.waveAnimController,
  });

  @override
  Widget build(BuildContext context) {
    final isVoiceActive = isConversationModeActive ||
        isVoiceListening ||
        runtimeState == HologramRuntimeState.listening ||
        runtimeState == HologramRuntimeState.speaking ||
        runtimeState == HologramRuntimeState.thinking ||
        runtimeState == HologramRuntimeState.acting ||
        runtimeState == HologramRuntimeState.retrieving;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
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
                ? CommandWaveformBanner(
                    key: const ValueKey('audio_waveform_banner'),
                    runtimeState: runtimeState,
                    isVoiceListening: isVoiceListening,
                    isConversationModeActive: isConversationModeActive,
                    palette: palette,
                    pulse: pulse,
                    waveAnimController: waveAnimController,
                  )
                : const SizedBox.shrink(),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Keyboard button
              Tooltip(
                message: 'Mở khung chat (Bàn phím)',
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: onOpenChat,
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
                            color: palette.primary.withValues(alpha: 0.20 + 0.10 * pulse),
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
                      child: Icon(Icons.keyboard_alt_outlined, color: palette.primary, size: 26),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 36),

              // Voice mic / stop button
              Tooltip(
                message: isVoiceActive
                    ? (isConversationModeActive ? 'Dừng hội thoại realtime' : 'Dừng lắng nghe')
                    : 'Chạm: Voice nhanh · Giữ: Chế độ hội thoại',
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: onVoiceTap,
                    onLongPress: onVoiceLongPress,
                    borderRadius: BorderRadius.circular(100),
                    splashColor: (isVoiceActive ? palette.accent : palette.secondary).withValues(alpha: 0.35),
                    highlightColor: (isVoiceActive ? palette.accent : palette.secondary).withValues(alpha: 0.15),
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
                                colors: [palette.primary, palette.accent],
                              )
                            : null,
                        color: isVoiceActive ? null : const Color(0xFF0D172A).withValues(alpha: 0.88),
                        border: Border.all(
                          color: isVoiceActive ? palette.accent : palette.secondary.withValues(alpha: 0.55),
                          width: isVoiceActive ? 1.8 : 1.2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: (isVoiceActive ? palette.accent : palette.secondary)
                                .withValues(alpha: isVoiceActive ? (0.45 + 0.25 * pulse) : (0.20 + 0.10 * pulse)),
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
                        color: isVoiceActive ? const Color(0xFF04070E) : palette.secondary,
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
  }
}
