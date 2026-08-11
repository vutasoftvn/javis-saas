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
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;

        return Row(
          children: [
            // Left Quick Utility Buttons (Settings & Theme on wide screens only)
            if (!isMobile) ...[
              Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF0D172A).withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: IconButton(
                  icon: const Icon(Icons.settings_outlined, color: Color(0xFF94A3B8), size: 19),
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
                  icon: const Icon(Icons.wb_sunny_outlined, color: Color(0xFF94A3B8), size: 19),
                  tooltip: 'Chế độ hiển thị',
                  onPressed: widget.onThemeTap,
                ),
              ),
              const SizedBox(width: 14),
            ],

            // Center Glowing Command Input Bar (Pill shape radius 100 with shadow)
            Expanded(
              child: Container(
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
                    const SizedBox(width: 16),
                    // Active Green Bot Icon
                    const Icon(
                      Icons.psychology,
                      color: Color(0xFF10B981),
                      size: 20,
                    ),
                    const SizedBox(width: 10),
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
                    IconButton(
                      icon: const Icon(Icons.mic_none, color: Color(0xFF00F0FF), size: 20),
                      tooltip: 'Nói với COSA (Voice)',
                      onPressed: widget.onVoiceTap,
                    ),
                    if (!isMobile)
                      Container(
                        margin: const EdgeInsets.only(right: 14),
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
                      )
                    else
                      const SizedBox(width: 6),
                  ],
                ),
              ),
            ),

            // Right Cloud Connectivity Status (Desktop / Wide screen only)
            if (!isMobile) ...[
              const SizedBox(width: 18),
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
                        'COSA CLOUD',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.0,
                        ),
                      ),
                      Text(
                        'CONNECTED',
                        style: TextStyle(
                          color: Color(0xFF10B981),
                          fontSize: 9.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ],
        );
      },
    );
  }
}
