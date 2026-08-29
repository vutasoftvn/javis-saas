import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import '../audio_waveform_painter.dart';

class HubChatInputBar extends StatelessWidget {
  final HologramHubController controller;
  final TextEditingController textController;
  final FocusNode focusNode;
  final AnimationController waveController;
  final bool isComposing;
  final ValueChanged<String> onSubmit;

  const HubChatInputBar({
    super.key,
    required this.controller,
    required this.textController,
    required this.focusNode,
    required this.waveController,
    required this.isComposing,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Voice listening indicator banner
        Obx(() {
          final isListening = controller.isVoiceListening.value ||
              controller.runtimeState.value == HologramRuntimeState.listening;
          if (!isListening) return const SizedBox.shrink();

          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            color: const Color(0xFF14B8A6).withValues(alpha: 0.1),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: const Color(0xFF14B8A6),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF14B8A6).withValues(alpha: 0.8),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Đang lắng nghe giọng nói... Bấm lại nút Mic để kết thúc.',
                    style: TextStyle(
                      color: Color(0xFF14B8A6),
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                AnimatedBuilder(
                  animation: waveController,
                  builder: (context, child) {
                    return SizedBox(
                      width: 60,
                      height: 16,
                      child: CustomPaint(
                        painter: AudioWaveformPainter(
                          animationValue: waveController.value,
                          barCount: 10,
                          primaryColor: const Color(0xFF14B8A6),
                          secondaryColor: const Color(0xFF3B82F6),
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          );
        }),

        // Bottom Input Row
        Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
          decoration: BoxDecoration(
            color: const Color(0xFF070C18).withValues(alpha: 0.40),
            borderRadius: const BorderRadius.vertical(bottom: Radius.circular(15)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Speech-to-text / Mic button
              Obx(() {
                final isListening = controller.isVoiceListening.value ||
                    controller.runtimeState.value == HologramRuntimeState.listening;

                return Tooltip(
                  message: isListening
                      ? 'Dừng ghi âm & xử lý'
                      : 'Nói để chuyển thành văn bản (Speech to Text)',
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(100),
                      onTap: controller.onTalkPressed,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: isListening
                              ? const Color(0xFFEF4444).withValues(alpha: 0.15)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(100),
                          border: Border.all(
                            color: isListening
                                ? const Color(0xFFEF4444)
                                : const Color(0xFF334155).withValues(alpha: 0.8),
                            width: 1,
                          ),
                          boxShadow: isListening
                              ? [
                                  BoxShadow(
                                    color: const Color(0xFFEF4444).withValues(alpha: 0.4),
                                    blurRadius: 10,
                                  ),
                                ]
                              : null,
                        ),
                        child: Icon(
                          isListening ? Icons.mic : Icons.mic_none_rounded,
                          size: 20,
                          color: isListening ? const Color(0xFFEF4444) : const Color(0xFF94A3B8),
                        ),
                      ),
                    ),
                  ),
                );
              }),

              const SizedBox(width: 8),

              // Text Field
              Expanded(
                child: Container(
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(100),
                    border: Border.all(
                      color: focusNode.hasFocus
                          ? const Color(0xFF14B8A6).withValues(alpha: 0.5)
                          : const Color(0xFF334155).withValues(alpha: 0.8),
                      width: 1,
                    ),
                  ),
                  child: CallbackShortcuts(
                    bindings: {
                      const SingleActivator(LogicalKeyboardKey.enter): () {
                        onSubmit(textController.text);
                      },
                    },
                    child: TextField(
                      controller: textController,
                      focusNode: focusNode,
                      maxLines: 1,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 14.5,
                      ),
                      decoration: const InputDecoration(
                        hintText: 'Nhập tin nhắn hoặc lệnh...',
                        hintStyle: TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 14,
                        ),
                        filled: false,
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        disabledBorder: InputBorder.none,
                        errorBorder: InputBorder.none,
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 11),
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(width: 8),

              // Send Button
              Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(100),
                  onTap: isComposing ? () => onSubmit(textController.text) : null,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.transparent,
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(
                        color: isComposing
                            ? const Color(0xFF14B8A6).withValues(alpha: 0.7)
                            : const Color(0xFF334155).withValues(alpha: 0.8),
                        width: 1,
                      ),
                      boxShadow: isComposing
                          ? [
                              BoxShadow(
                                color: const Color(0xFF14B8A6).withValues(alpha: 0.25),
                                blurRadius: 8,
                              ),
                            ]
                          : null,
                    ),
                    child: Icon(
                      Icons.send_rounded,
                      size: 18,
                      color: isComposing ? const Color(0xFF14B8A6) : const Color(0xFF64748B),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
