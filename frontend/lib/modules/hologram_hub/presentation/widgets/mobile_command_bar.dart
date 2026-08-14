import 'package:flutter/material.dart';

/// Dedicated Mobile Command Bar component for COSA Hologram Hub.
///
/// Modes:
/// 1. Default Mode (isChatInputActive == false):
///    - Renders 2 standard circular action buttons:
///      - Left: Keyboard Icon Button (opens chat input, animates orb to top 32px @ 0.5 scale)
///      - Right: Voice Mic Hero Button (starts active listening mode)
///
/// 2. Chat Input Mode (isChatInputActive == true):
///    - Renders pill chat input bar with:
///      - Left: "Icon xoá" / Close button (dismisses chat bar, animates orb back to center)
///      - Center: Text input field for COSA
///      - Right: Send / Mic button
class MobileCommandBar extends StatefulWidget {
  final bool isChatInputActive;
  final bool isVoiceListening;
  final VoidCallback onOpenChat;
  final VoidCallback onCloseChat;
  final VoidCallback onVoiceTap;
  final VoidCallback? onVoiceLongPress;
  final Function(String query) onSubmit;

  const MobileCommandBar({
    super.key,
    required this.isChatInputActive,
    this.isVoiceListening = false,
    required this.onOpenChat,
    required this.onCloseChat,
    required this.onVoiceTap,
    this.onVoiceLongPress,
    required this.onSubmit,
  });

  @override
  State<MobileCommandBar> createState() => _MobileCommandBarState();
}

class _MobileCommandBarState extends State<MobileCommandBar> with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  late AnimationController _pulseAnimController;

  @override
  void initState() {
    super.initState();
    _pulseAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
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
    super.dispose();
  }

  void _handleSubmitted(String text) {
    if (text.trim().isNotEmpty) {
      widget.onSubmit(text.trim());
      _controller.clear();
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
    return Container(
      key: key,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // 1. Keyboard Icon Button (opens chat input)
          Tooltip(
            message: 'Mở khung chat (Bàn phím)',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: widget.onOpenChat,
                borderRadius: BorderRadius.circular(100),
                splashColor: const Color(0xFF00F0FF).withValues(alpha: 0.25),
                child: Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF0D172A).withValues(alpha: 0.92),
                    border: Border.all(
                      color: const Color(0xFF00F0FF).withValues(alpha: 0.4),
                      width: 1.2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF00F0FF).withValues(alpha: 0.2),
                        blurRadius: 16,
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
                  child: const Center(
                    child: Icon(
                      Icons.keyboard_alt_outlined,
                      color: Color(0xFF00F0FF),
                      size: 26,
                    ),
                  ),
                ),
              ),
            ),
          ),

          const SizedBox(width: 36),

          // 2. Voice Mic Button (Active state when listening, standard state when idle)
          // Tap = push-to-talk (record -> transcribe -> send); long-press =
          // LiveKit Conversation Mode (continuous realtime voice, §15.2).
          Tooltip(
            message: widget.isVoiceListening
                ? 'Đang lắng nghe chủ động (Chạm để gửi)'
                : 'Chạm: Voice nhanh · Giữ: Chế độ hội thoại',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: widget.onVoiceTap,
                onLongPress: widget.onVoiceLongPress,
                borderRadius: BorderRadius.circular(100),
                splashColor: const Color(0xFF00F0FF).withValues(alpha: 0.35),
                child: AnimatedBuilder(
                  animation: _pulseAnimController,
                  builder: (context, child) {
                    final pulse = _pulseAnimController.value;
                    final isListening = widget.isVoiceListening;

                    return AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: isListening ? 62 : 56,
                      height: isListening ? 62 : 56,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: isListening
                            ? const LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [Color(0xFF00F0FF), Color(0xFF10B981)],
                              )
                            : null,
                        color: isListening
                            ? null
                            : const Color(0xFF0D172A).withValues(alpha: 0.92),
                        border: Border.all(
                          color: isListening
                              ? const Color(0xFF00FFB2)
                              : const Color(0xFF00F0FF).withValues(alpha: 0.4),
                          width: isListening ? 1.8 : 1.2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: (isListening
                                    ? const Color(0xFF00FFB2)
                                    : const Color(0xFF00F0FF))
                                .withValues(
                                    alpha: isListening
                                        ? (0.45 + 0.25 * pulse)
                                        : 0.2),
                            blurRadius: isListening ? (20 + 8 * pulse) : 16,
                            spreadRadius: isListening ? (2 + 2 * pulse) : 1,
                            offset: const Offset(0, 2),
                          ),
                          if (!isListening)
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.5),
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                            ),
                        ],
                      ),
                      child: Center(
                        child: Icon(
                          isListening ? Icons.graphic_eq : Icons.mic,
                          color: isListening
                              ? const Color(0xFF04070E)
                              : const Color(0xFF00F0FF),
                          size: isListening ? 30 : 26,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// ── Mode 2: Chat Input Bar with Delete/Close Icon ───────────────────────
  Widget _buildChatInputBar({required Key key}) {
    return Container(
      key: key,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Container(
        height: 50,
        decoration: BoxDecoration(
          color: const Color(0xFF0D172A).withValues(alpha: 0.95),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.45),
            width: 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF00F0FF).withValues(alpha: 0.25),
              blurRadius: 18,
              spreadRadius: 1,
              offset: const Offset(0, 3),
            ),
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.4),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            // Left: "Icon xoá" / Close chat bar (returns to 2 icons & full orb)
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
                      color: const Color(0xFFEF4444).withValues(alpha: 0.35),
                      width: 1,
                    ),
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.close_rounded,
                      color: Color(0xFFEF4444),
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
                decoration: const InputDecoration(
                  hintText: 'Nói với COSA...',
                  hintStyle: TextStyle(color: Color(0xFF64748B), fontSize: 14),
                  filled: false,
                  fillColor: Colors.transparent,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(horizontal: 4, vertical: 10),
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
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(
                            colors: [Color(0xFF00D2FF), Color(0xFF0072FF)],
                          ),
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
                return IconButton(
                  icon: const Icon(Icons.mic_none, color: Color(0xFF00F0FF), size: 22),
                  tooltip: 'Nói với COSA (Voice)',
                  onPressed: widget.onVoiceTap,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                );
              },
            ),
            const SizedBox(width: 4),
          ],
        ),
      ),
    );
  }
}
