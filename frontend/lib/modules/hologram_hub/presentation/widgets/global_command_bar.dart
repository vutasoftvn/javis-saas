import 'package:flutter/material.dart';

class GlobalCommandBar extends StatefulWidget {
  final Function(String query) onSubmit;
  final VoidCallback onSettingsTap;
  final VoidCallback onThemeTap;
  final VoidCallback onVoiceTap;

  const GlobalCommandBar({
    super.key,
    required this.onSubmit,
    required this.onSettingsTap,
    required this.onThemeTap,
    required this.onVoiceTap,
  });

  @override
  State<GlobalCommandBar> createState() => _GlobalCommandBarState();
}

class _GlobalCommandBarState extends State<GlobalCommandBar> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
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
    return Row(
      children: [
        // Left Quick Utility Buttons (Settings & Theme)
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A).withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: IconButton(
            icon: const Icon(Icons.settings_outlined, color: Color(0xFF94A3B8), size: 20),
            tooltip: 'Cài đặt',
            onPressed: widget.onSettingsTap,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A).withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: IconButton(
            icon: const Icon(Icons.wb_sunny_outlined, color: Color(0xFF94A3B8), size: 20),
            tooltip: 'Chế độ hiển thị',
            onPressed: widget.onThemeTap,
          ),
        ),
        const SizedBox(width: 14),

        // Center Glowing Command Input Bar
        Expanded(
          child: Container(
            height: 48,
            decoration: BoxDecoration(
              color: const Color(0xFF0D172A).withValues(alpha: 0.9),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: const Color(0xFF00F0FF).withValues(alpha: 0.35),
                width: 1.0,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                  blurRadius: 12,
                  spreadRadius: 0,
                ),
              ],
            ),
            child: Row(
              children: [
                const SizedBox(width: 16),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    focusNode: _focusNode,
                    onSubmitted: _handleSubmitted,
                    style: const TextStyle(color: Colors.white, fontSize: 14.5),
                    decoration: const InputDecoration(
                      hintText: 'Nói với COSA...',
                      hintStyle: TextStyle(color: Color(0xFF64748B), fontSize: 14),
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      contentPadding: EdgeInsets.zero,
                      isDense: true,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.mic_none, color: Color(0xFF00F0FF), size: 20),
                  tooltip: 'Nói với COSA (Voice)',
                  onPressed: widget.onVoiceTap,
                ),
                Container(
                  margin: const EdgeInsets.only(right: 12),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: const Text(
                    '⌘ K',
                    style: TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 18),

        // Right Cloud Connectivity Status
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: const Color(0xFF10B981),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF10B981).withValues(alpha: 0.8),
                    blurRadius: 6,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: const [
                Text(
                  'CONNECTED TO COSA CLOUD',
                  style: TextStyle(
                    color: Color(0xFF10B981),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                  ),
                ),
                Text(
                  '✦ All systems operational',
                  style: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 9.5,
                  ),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}
