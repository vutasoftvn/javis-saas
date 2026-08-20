import 'package:flutter/material.dart';

class TerminalOutputCardWidget extends StatelessWidget {
  final Map<String, dynamic> payload;

  const TerminalOutputCardWidget({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Terminal Output';
    final output = payload['output'] ?? '';
    final exitCode = payload['exit_code'] ?? 0;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1117),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0x30FFFFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.terminal, color: Color(0xFF00FF66), size: 16),
              const SizedBox(width: 6),
              Text(title, style: const TextStyle(color: Colors.white, fontSize: 12, fontFamily: 'monospace')),
              const Spacer(),
              Text("Exit: $exitCode", style: TextStyle(color: exitCode == 0 ? const Color(0xFF00FF66) : const Color(0xFFFF3366), fontSize: 11)),
            ],
          ),
          const SizedBox(height: 6),
          Text(output, style: const TextStyle(color: Color(0xFFC9D1D9), fontSize: 11, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
