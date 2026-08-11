import 'package:flutter/material.dart';

class QuickCommandsBar extends StatelessWidget {
  final Function(String command) onCommandTap;

  const QuickCommandsBar({
    super.key,
    required this.onCommandTap,
  });

  static const List<String> _commands = [
    'Tổng quan hôm nay',
    'Kiểm tra công việc',
    'Mở Knowledge Studio',
    'Báo cáo tài chính',
  ];

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'QUICK COMMANDS',
            style: TextStyle(
              color: Color(0xFF64748B),
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(width: 14),
          ..._commands.map((cmd) {
            return Padding(
              padding: const EdgeInsets.only(right: 10.0),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => onCommandTap(cmd),
                  borderRadius: BorderRadius.circular(20),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D172A).withValues(alpha: 0.8),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: const Color(0xFF1E293B),
                        width: 1.0,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.add, size: 13, color: Color(0xFF38BDF8)),
                        const SizedBox(width: 6),
                        Text(
                          cmd,
                          style: const TextStyle(
                            color: Color(0xFFCBD5E1),
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
