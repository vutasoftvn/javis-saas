import 'package:flutter/material.dart';
import 'hud_card.dart';

/// CEO Next Best Actions Brief (mCOSA V12 Sprint 9/10, Spec §37 & §50) —
/// surfaces the Top 3 ranked actions from GET /api/v1/strategy/ceo/next-actions
/// directly on the Hologram Hub, so the founder sees them without opening the
/// Strategy module first.
class NextActionsPanel extends StatelessWidget {
  final List<dynamic> actions;
  final VoidCallback? onViewAll;

  const NextActionsPanel({
    super.key,
    required this.actions,
    this.onViewAll,
  });

  @override
  Widget build(BuildContext context) {
    return hudCard(
      onTap: onViewAll,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          hudCardHeader(
            title: 'HÀNH ĐỘNG ƯU TIÊN CEO',
            badgeText: actions.isEmpty ? 'ĐANG RẢNH' : 'TOP ${actions.length}',
            badgeColor: actions.isEmpty ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
          ),
          const SizedBox(height: 10),
          if (actions.isEmpty)
            const Text(
              'Không có hành động ưu tiên nào đang chờ. Hệ thống sẽ tự động đề xuất khi phát hiện tắc nghẽn công việc, điểm Gate HOLD hoặc mục cần phê duyệt.',
              style: TextStyle(color: Color(0xFF64748B), fontSize: 14, height: 1.4),
            )
          else
            ...actions.take(3).map((a) => _buildActionRow(a)),
        ],
      ),
    );
  }

  Widget _buildActionRow(dynamic action) {
    final title = action['title'] as String? ?? 'Hành động';
    final category = action['category'] as String? ?? '';
    final score = (action['r0_score'] as num?)?.toDouble() ?? 0.0;
    final urgent = score >= 0.8;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 3),
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: (urgent ? const Color(0xFFEF4444) : const Color(0xFFF59E0B)).withValues(alpha: 0.15),
            ),
            child: Icon(
              urgent ? Icons.priority_high_rounded : Icons.bolt_rounded,
              size: 12,
              color: urgent ? const Color(0xFFEF4444) : const Color(0xFFF59E0B),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 14, fontWeight: FontWeight.w600),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (category.isNotEmpty)
                  Text(
                    category,
                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 14),
                  ),
              ],
            ),
          ),
          Text(
            score.toStringAsFixed(2),
            style: TextStyle(
              color: urgent ? const Color(0xFFEF4444) : const Color(0xFFF59E0B),
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
