import 'package:flutter/material.dart';
import 'hud_card.dart';

/// Needs You Brief Panel — Surfaces founder exception queue on the Hologram Hub right rail.
class NeedsYouPanel extends StatelessWidget {
  final List<dynamic> items;
  final VoidCallback? onViewAll;

  const NeedsYouPanel({
    super.key,
    required this.items,
    this.onViewAll,
  });

  @override
  Widget build(BuildContext context) {
    final count = items.length;
    return hudCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          hudCardHeader(
            title: 'NEEDS YOU — EXCEPTIONS',
            badgeText: count == 0 ? 'TẤT CẢ XONG' : '$count YÊU CẦU',
            badgeColor: count == 0 ? const Color(0xFF10B981) : const Color(0xFFEF4444),
          ),
          const SizedBox(height: 10),
          if (items.isEmpty)
            const Text(
              'Không có ngoại lệ hay phê duyệt nào cần founder giải quyết lúc này.',
              style: TextStyle(color: Color(0xFF64748B), fontSize: 10.5, height: 1.4),
            )
          else
            ...items.take(3).map((item) => _buildItemRow(item)),
          if (onViewAll != null) ...[
            const SizedBox(height: 4),
            InkWell(
              onTap: onViewAll,
              child: const Padding(
                padding: EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      'XEM TOÀN BỘ NEEDS YOU',
                      style: TextStyle(
                        color: Color(0xFFEF4444),
                        fontSize: 11.5,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.0,
                      ),
                    ),
                    SizedBox(width: 4),
                    Icon(Icons.arrow_forward_ios, size: 10, color: Color(0xFFEF4444)),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildItemRow(dynamic item) {
    final reason = (item['reason'] as String?) ?? 'Yêu cầu xử lý';
    final priority = (item['priority'] as String?) ?? 'P1';
    final isP0 = priority == 'P0';

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
              color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFFF59E0B)).withValues(alpha: 0.15),
            ),
            child: Icon(
              isP0 ? Icons.error_outline : Icons.pending_actions,
              size: 12,
              color: isP0 ? const Color(0xFFEF4444) : const Color(0xFFF59E0B),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              reason,
              style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12, fontWeight: FontWeight.w600),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
