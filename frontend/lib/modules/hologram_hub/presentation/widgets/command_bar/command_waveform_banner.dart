import 'package:flutter/material.dart';
import '../audio_waveform_painter.dart';
import '../miva_hologram_core.dart';
import 'hologram_palette_helper.dart';

class CommandWaveformBanner extends StatelessWidget {
  final HologramRuntimeState runtimeState;
  final bool isVoiceListening;
  final bool isConversationModeActive;
  final HologramPalette palette;
  final double pulse;
  final AnimationController waveAnimController;

  const CommandWaveformBanner({
    super.key,
    required this.runtimeState,
    required this.isVoiceListening,
    required this.isConversationModeActive,
    required this.palette,
    required this.pulse,
    required this.waveAnimController,
  });

  @override
  Widget build(BuildContext context) {
    final String statusText;
    final Color stateColor;
    final IconData statusIcon;

    if (runtimeState == HologramRuntimeState.speaking) {
      statusText = 'COSA đang nói...';
      stateColor = palette.accent;
      statusIcon = Icons.volume_up_rounded;
    } else if (runtimeState == HologramRuntimeState.thinking ||
        runtimeState == HologramRuntimeState.acting ||
        runtimeState == HologramRuntimeState.retrieving) {
      statusText = 'Đang suy nghĩ...';
      stateColor = palette.secondary;
      statusIcon = Icons.psychology_outlined;
    } else {
      statusText = 'Đang lắng nghe...';
      stateColor = palette.primary;
      statusIcon = Icons.mic_rounded;
    }

    return Center(
      child: Container(
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
            Icon(statusIcon, color: stateColor, size: 15),
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
            SizedBox(
              width: 72,
              height: 18,
              child: CustomPaint(
                painter: AudioWaveformPainter(
                  animationValue: waveAnimController.value,
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
}
