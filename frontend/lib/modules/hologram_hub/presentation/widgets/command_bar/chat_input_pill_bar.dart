import 'package:flutter/material.dart';
import '../miva_hologram_core.dart';
import 'hologram_palette_helper.dart';

class ChatInputPillBar extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final HologramRuntimeState runtimeState;
  final bool isVoiceListening;
  final bool isConversationModeActive;
  final VoidCallback onCloseChat;
  final VoidCallback onVoiceTap;
  final ValueChanged<String> onSubmit;
  final HologramPalette palette;
  final double pulse;

  const ChatInputPillBar({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.runtimeState,
    required this.isVoiceListening,
    required this.isConversationModeActive,
    required this.onCloseChat,
    required this.onVoiceTap,
    required this.onSubmit,
    required this.palette,
    required this.pulse,
  });

  @override
  Widget build(BuildContext context) {
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
        padding: const EdgeInsets.all(1.2),
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
              const SizedBox(width: 6),
              Tooltip(
                message: 'Đóng khung chat',
                child: GestureDetector(
                  onTap: () {
                    focusNode.unfocus();
                    controller.clear();
                    onCloseChat();
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

              Expanded(
                child: TextField(
                  controller: controller,
                  focusNode: focusNode,
                  keyboardType: TextInputType.text,
                  textInputAction: TextInputAction.send,
                  textCapitalization: TextCapitalization.sentences,
                  autocorrect: true,
                  enableSuggestions: true,
                  onSubmitted: onSubmit,
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
                    contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
                    isDense: true,
                  ),
                ),
              ),

              ValueListenableBuilder<TextEditingValue>(
                valueListenable: controller,
                builder: (context, value, child) {
                  final hasText = value.text.trim().isNotEmpty;
                  if (hasText) {
                    return Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: GestureDetector(
                        onTap: () => onSubmit(controller.text),
                        child: Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: [palette.primary, palette.secondary],
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
                  final isVoiceActive = isConversationModeActive ||
                      isVoiceListening ||
                      runtimeState == HologramRuntimeState.listening ||
                      runtimeState == HologramRuntimeState.speaking;

                  return IconButton(
                    icon: ShaderMask(
                      shaderCallback: (bounds) => LinearGradient(
                        colors: isVoiceActive
                            ? [const Color(0xFFEF4444), const Color(0xFFF87171)]
                            : [palette.primary, palette.accent],
                      ).createShader(bounds),
                      child: Icon(
                        isVoiceActive ? Icons.stop_rounded : Icons.mic_rounded,
                        color: Colors.white,
                        size: 22,
                      ),
                    ),
                    tooltip: isVoiceActive
                        ? (isConversationModeActive ? 'Dừng hội thoại realtime' : 'Dừng nghe')
                        : 'Nói với COSA (Voice)',
                    onPressed: onVoiceTap,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                  );
                },
              ),
              const SizedBox(width: 4),
            ],
          ),
        ),
      ),
    );
  }
}
