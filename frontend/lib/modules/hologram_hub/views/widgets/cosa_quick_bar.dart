import 'package:flutter/material.dart';

class CosaQuickBar extends StatefulWidget {
  final Function(String command)? onSubmit;
  final VoidCallback? onVoicePressed;
  final bool isVoiceListening;

  const CosaQuickBar({
    super.key,
    this.onSubmit,
    this.onVoicePressed,
    this.isVoiceListening = false,
  });

  @override
  State<CosaQuickBar> createState() => _CosaQuickBarState();
}

class _CosaQuickBarState extends State<CosaQuickBar> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSubmit() {
    final text = _controller.text.trim();
    if (text.isNotEmpty) {
      widget.onSubmit?.call(text);
      _controller.clear();
      _focusNode.unfocus();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: const Color(0xFF00E5FF).withValues(alpha: 0.3),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00E5FF).withValues(alpha: 0.08),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // Voice Button
          InkWell(
            onTap: widget.onVoicePressed,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: widget.isVoiceListening
                    ? const Color(0xFFEF4444).withValues(alpha: 0.2)
                    : const Color(0xFF00E5FF).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: widget.isVoiceListening
                      ? const Color(0xFFEF4444)
                      : const Color(0xFF00E5FF).withValues(alpha: 0.4),
                ),
              ),
              child: Icon(
                widget.isVoiceListening ? Icons.mic : Icons.mic_none_rounded,
                color: widget.isVoiceListening
                    ? const Color(0xFFEF4444)
                    : const Color(0xFF00E5FF),
                size: 20,
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Input TextField
          Expanded(
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              onSubmitted: (_) => _handleSubmit(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
              ),
              decoration: const InputDecoration(
                hintText: 'Hỏi COSA Companion: "Chúng ta nên làm gì tiếp theo?"...',
                hintStyle: TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 13,
                ),
                border: InputBorder.none,
                isDense: true,
                contentPadding: EdgeInsets.symmetric(vertical: 8),
              ),
            ),
          ),
          const SizedBox(width: 8),
          // Submit Button
          InkWell(
            onTap: _handleSubmit,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF00B4D8), Color(0xFF0077B6)],
                ),
                borderRadius: BorderRadius.circular(10),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF00B4D8).withValues(alpha: 0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: const Icon(
                Icons.arrow_upward_rounded,
                color: Colors.white,
                size: 18,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
