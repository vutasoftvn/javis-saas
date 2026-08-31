import 'package:flutter/material.dart';
import '../../../../../core/theme/app_theme.dart';
import '../../../controllers/strategy_controller.dart';
import '../dialogs/okr_dialogs.dart';

class KeyResultItemTile extends StatelessWidget {
  final StrategyController controller;
  final dynamic kr;

  const KeyResultItemTile({
    super.key,
    required this.controller,
    required this.kr,
  });

  String _fmtNum(double val) {
    if (val == val.roundToDouble()) {
      return val.toInt().toString();
    }
    return val.toStringAsFixed(1);
  }

  @override
  Widget build(BuildContext context) {
    final krId = kr['id']?.toString() ?? '';
    final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
    final target = (kr['target_value'] as num?)?.toDouble() ?? 100.0;
    final unit = kr['unit'] ?? '%';
    final ratio = target > 0 ? (current / target).clamp(0.0, 1.0) : 0.0;
    final krTitle = kr['title'] ?? 'Đạt ${_fmtNum(target)} $unit';

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
                  style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(
                  'Tiến độ: ${_fmtNum(current)} / ${_fmtNum(target)} ${unit.isNotEmpty ? unit : '%'}',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),

          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${(ratio * 100).toInt()}%',
                style: const TextStyle(color: AppTheme.secondaryLight, fontWeight: FontWeight.bold, fontSize: 12),
              ),
              const SizedBox(height: 4),
              SizedBox(
                width: 64,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: ratio,
                    backgroundColor: Colors.white10,
                    valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.secondaryLight),
                    minHeight: 5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(width: 10),

          TextButton(
            onPressed: () => OkrDialogs.showCheckinKeyResultDialog(context, controller, kr),
            style: TextButton.styleFrom(
              foregroundColor: AppTheme.primaryLight,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            ),
            child: const Text('Check-in', style: TextStyle(fontSize: 12)),
          ),
          IconButton(
            onPressed: () => controller.deleteKeyResult(krId),
            icon: const Icon(Icons.delete_outline_rounded, size: 16, color: Colors.white38),
            splashRadius: 16,
            tooltip: 'Xóa KR',
          ),
        ],
      ),
    );
  }
}
