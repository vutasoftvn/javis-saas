import 'package:flutter/material.dart';

/// Dedicated Mobile Command Bar component for COSA Hologram Hub.
/// Renders a floating pill input bar with:
///   - Left icon: toggle history visibility (chat_bubble / chat_bubble_outline)
///   - Left icon in textfield: clear history (only when messages exist)
///   - Right icon: voice mic
///
/// When [showHistory] is true and [messages] is non-empty, the chat history
/// list is rendered ABOVE this bar (below the hologram orb), newest at bottom,
/// oldest at top, scrollable upward.
class MobileCommandBar extends StatefulWidget {
  final Function(String query) onSubmit;
  final VoidCallback onVoiceTap;
  final List<Map<String, String>> messages;
  final bool showHistory;
  final VoidCallback onToggleHistory;
  final VoidCallback onClearHistory;

  const MobileCommandBar({
    super.key,
    required this.onSubmit,
    required this.onVoiceTap,
    this.messages = const [],
    this.showHistory = true,
    required this.onToggleHistory,
    required this.onClearHistory,
  });

  @override
  State<MobileCommandBar> createState() => _MobileCommandBarState();
}

class _MobileCommandBarState extends State<MobileCommandBar> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(MobileCommandBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Auto-scroll to bottom when new messages arrive
    if (widget.messages.length != oldWidget.messages.length &&
        widget.showHistory &&
        widget.messages.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  void _handleSubmitted(String text) {
    if (text.trim().isNotEmpty) {
      widget.onSubmit(text.trim());
      _controller.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasMessages = widget.messages.isNotEmpty;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Chat History Panel ───────────────────────────────────────────
        if (hasMessages && widget.showHistory)
          _buildHistoryPanel(),

        // ── Input Bar ────────────────────────────────────────────────────
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          color: Colors.transparent,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Left: Toggle history icon button
              _buildToggleButton(hasMessages),
              const SizedBox(width: 8),

              // Center: Pill input
              Expanded(child: _buildInputPill(hasMessages)),
            ],
          ),
        ),
      ],
    );
  }

  /// Toggle history button (left of input pill)
  Widget _buildToggleButton(bool hasMessages) {
    return GestureDetector(
      onTap: hasMessages ? widget.onToggleHistory : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: hasMessages
              ? (widget.showHistory
                  ? const Color(0xFF00F0FF).withValues(alpha: 0.18)
                  : const Color(0xFF1E293B).withValues(alpha: 0.7))
              : Colors.transparent,
          border: hasMessages
              ? Border.all(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.35),
                  width: 1,
                )
              : null,
        ),
        child: Icon(
          hasMessages
              ? (widget.showHistory
                  ? Icons.chat_bubble
                  : Icons.chat_bubble_outline)
              : Icons.chat_bubble_outline,
          color: hasMessages
              ? const Color(0xFF00F0FF)
              : const Color(0xFF374151),
          size: 17,
        ),
      ),
    );
  }

  /// Input pill with optional clear icon on the left (when has messages)
  Widget _buildInputPill(bool hasMessages) {
    return Container(
      height: 48,
      decoration: BoxDecoration(
        color: const Color(0xFF0D172A).withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(
          color: const Color(0xFF00F0FF).withValues(alpha: 0.4),
          width: 1.0,
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
          // Clear history icon (inside pill, left side) — visible only when messages exist
          if (hasMessages) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: widget.onClearHistory,
              child: Tooltip(
                message: 'Xoá lịch sử chat',
                child: Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                  ),
                  child: const Icon(
                    Icons.delete_sweep_outlined,
                    color: Color(0xFFEF4444),
                    size: 15,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
          ] else
            const SizedBox(width: 20),

          // Text field
          Expanded(
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              onSubmitted: _handleSubmitted,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: const InputDecoration(
                hintText: 'Nói với COSA...',
                hintStyle: TextStyle(color: Color(0xFF64748B), fontSize: 13.5),
                filled: false,
                fillColor: Colors.transparent,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                contentPadding: EdgeInsets.zero,
                isDense: true,
              ),
            ),
          ),

          // Right: Voice icon
          IconButton(
            icon: const Icon(Icons.mic_none, color: Color(0xFF00F0FF), size: 20),
            tooltip: 'Nói với COSA (Voice)',
            onPressed: widget.onVoiceTap,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
          ),
          const SizedBox(width: 4),
        ],
      ),
    );
  }

  /// Chat history panel — messages displayed bottom-up, latest at bottom
  Widget _buildHistoryPanel() {
    return Container(
      constraints: const BoxConstraints(maxHeight: 260),
      margin: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF070C18).withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFF1E293B).withValues(alpha: 0.8),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00F0FF).withValues(alpha: 0.06),
            blurRadius: 20,
            spreadRadius: 2,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: ListView.builder(
          controller: _scrollController,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          itemCount: widget.messages.length,
          itemBuilder: (context, index) {
            final msg = widget.messages[index];
            final isUser = msg['role'] == 'user';
            return _buildMessageBubble(
              text: msg['text'] ?? '',
              isUser: isUser,
            );
          },
        ),
      ),
    );
  }

  Widget _buildMessageBubble({required String text, required bool isUser}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            // COSA avatar
            Container(
              width: 24,
              height: 24,
              margin: const EdgeInsets.only(right: 6, bottom: 2),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const LinearGradient(
                  colors: [Color(0xFF00D2FF), Color(0xFF0072FF)],
                ),
              ),
              child: const Icon(Icons.psychology, size: 13, color: Colors.white),
            ),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                gradient: isUser
                    ? const LinearGradient(
                        colors: [Color(0xFF0072FF), Color(0xFF00D2FF)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isUser
                    ? null
                    : const Color(0xFF0D172A),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(12),
                  topRight: const Radius.circular(12),
                  bottomLeft: Radius.circular(isUser ? 12 : 2),
                  bottomRight: Radius.circular(isUser ? 2 : 12),
                ),
                border: isUser
                    ? null
                    : Border.all(
                        color: const Color(0xFF1E293B),
                        width: 1,
                      ),
                boxShadow: [
                  BoxShadow(
                    color: isUser
                        ? const Color(0xFF00D2FF).withValues(alpha: 0.2)
                        : Colors.black.withValues(alpha: 0.3),
                    blurRadius: 8,
                  ),
                ],
              ),
              child: Text(
                text,
                style: TextStyle(
                  color: isUser
                      ? const Color(0xFF04070E)
                      : const Color(0xFFCBD5E1),
                  fontSize: 13,
                  height: 1.45,
                  fontWeight: isUser ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 6),
            Container(
              width: 24,
              height: 24,
              margin: const EdgeInsets.only(left: 0, bottom: 2),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF1E293B),
                border: Border.all(color: const Color(0xFF334155), width: 1),
              ),
              child: const Icon(Icons.person, size: 13, color: Color(0xFF38BDF8)),
            ),
          ],
        ],
      ),
    );
  }
}
