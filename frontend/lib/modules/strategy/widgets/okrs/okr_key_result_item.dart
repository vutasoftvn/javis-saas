import 'package:flutter/material.dart';
import '../../controllers/strategy_controller.dart';

class OkrKeyResultItem extends StatelessWidget {
  final dynamic kr;
  final StrategyController controller;
  final VoidCallback onCheckIn;

  const OkrKeyResultItem({
    super.key,
    required this.kr,
    required this.controller,
    required this.onCheckIn,
  });

  @override
  Widget build(BuildContext context) {
    final krId = kr['id']?.toString() ?? '';
    final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
    final target = (kr['target_value'] as num?)?.toDouble() ?? 100.0;
    final unit = kr['unit'] ?? '%';
    final ratio = target > 0 ? (current / target).clamp(0.0, 1.0) : 0.0;

    String fmtNum(double val) {
      if (val == val.roundToDouble()) {
        return val.toInt().toString();
      }
      return val.toStringAsFixed(1);
    }

    final krTitle = kr['title'] ?? 'Đạt ${fmtNum(target)} $unit';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.4)),
            ),
            child: const Text(
              'KR',
              style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  krTitle,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: ratio,
                          backgroundColor: Colors.white10,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            ratio >= 1.0
                                ? const Color(0xFF10B981)
                                : (ratio >= 0.7 ? const Color(0xFF38BDF8) : const Color(0xFFF59E0B)),
                          ),
                          minHeight: 4,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      '${fmtNum(current)} / ${fmtNum(target)} $unit',
                      style: const TextStyle(color: Colors.white70, fontSize: 11),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          IconButton(
            onPressed: onCheckIn,
            icon: const Icon(Icons.edit_calendar_rounded, size: 16, color: Color(0xFF38BDF8)),
            splashRadius: 16,
            tooltip: 'Check-in tiến độ',
          ),
          IconButton(
            onPressed: () => controller.deleteKeyResult(krId),
            icon: const Icon(Icons.delete_outline_rounded, size: 16, color: Colors.white30),
            splashRadius: 16,
            tooltip: 'Xóa KR',
          ),
        ],
      ),
    );
  }
}
