import 'package:flutter/material.dart';

class ExecutiveReportPanel extends StatelessWidget {
  final Map<String, dynamic>? data;
  final Map<String, dynamic>? cycleTimeline;
  final VoidCallback? onOpenFullTimeline;
  final VoidCallback? onViewBlockers;
  final VoidCallback? onViewApprovals;
  final VoidCallback? onViewActivity;

  const ExecutiveReportPanel({
    super.key,
    this.data,
    this.cycleTimeline,
    this.onOpenFullTimeline,
    this.onViewBlockers,
    this.onViewApprovals,
    this.onViewActivity,
  });

  @override
  Widget build(BuildContext context) {
    final cycle = cycleTimeline?['cycle'] as Map<String, dynamic>? ?? {};
    final cycleTitle = cycle['title'] as String? ?? 'Chu kỳ 13 Tuần (12WY)';
    final durationWeeks = cycle['duration_weeks'] as int? ?? 13;
    final currentWeek = cycle['current_week'] as int? ?? 1;
    final progress = (cycle['overall_progress'] as num?)?.toDouble() ?? 0.0;
    final blockersCount = (cycleTimeline?['blockers'] as List?)?.length ?? 0;
    final pendingApprovals = cycleTimeline?['pending_proposals_count'] as int? ?? 0;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0B132B).withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.analytics_outlined, color: Color(0xFF00F0FF), size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'BÁO CÁO ĐIỀU HÀNH',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.4)),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.circle, color: Color(0xFF10B981), size: 6),
                    SizedBox(width: 4),
                    Text(
                      'Live',
                      style: TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Cycle Overview Card
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF131D38),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF2A3C60)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        cycleTitle,
                        style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(
                      'Tuần $currentWeek/$durationWeeks',
                      style: const TextStyle(color: Color(0xFF00F0FF), fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (progress / 100.0).clamp(0.0, 1.0),
                    backgroundColor: const Color(0xFF1E293B),
                    valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF00F0FF)),
                    minHeight: 6,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Tiến độ mục tiêu: ${progress.toStringAsFixed(1)}%',
                      style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                    ),
                    InkWell(
                      onTap: onOpenFullTimeline,
                      child: const Text(
                        'Chi tiết 12WY →',
                        style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // N-Week Mini Timeline
          const Text(
            'Lộ trình chu kỳ (N-Weeks)',
            style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 38,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: durationWeeks,
              separatorBuilder: (context, index) => const SizedBox(width: 6),
              itemBuilder: (context, idx) {
                final weekNum = idx + 1;
                final isCurrent = weekNum == currentWeek;
                final isPast = weekNum < currentWeek;

                Color bgColor = const Color(0xFF131D38);
                Color borderColor = const Color(0xFF1E293B);
                Color textColor = const Color(0xFF64748B);

                if (isCurrent) {
                  bgColor = const Color(0xFF00F0FF).withValues(alpha: 0.15);
                  borderColor = const Color(0xFF00F0FF);
                  textColor = const Color(0xFF00F0FF);
                } else if (isPast) {
                  bgColor = const Color(0xFF10B981).withValues(alpha: 0.1);
                  borderColor = const Color(0xFF10B981).withValues(alpha: 0.4);
                  textColor = const Color(0xFF10B981);
                }

                return InkWell(
                  onTap: onOpenFullTimeline,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    width: 32,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: bgColor,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: borderColor),
                    ),
                    child: Text(
                      'W$weekNum',
                      style: TextStyle(color: textColor, fontSize: 11, fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 14),

          // Action Highlights (Blockers & Approvals)
          Expanded(
            child: ListView(
              children: [
                _buildActionItem(
                  icon: Icons.shield_outlined,
                  title: 'Phê duyệt cần xử lý',
                  count: pendingApprovals,
                  color: pendingApprovals > 0 ? const Color(0xFFF59E0B) : const Color(0xFF64748B),
                  onTap: onViewApprovals,
                ),
                const SizedBox(height: 8),
                _buildActionItem(
                  icon: Icons.error_outline,
                  title: 'Điểm nghẽn (Blockers)',
                  count: blockersCount,
                  color: blockersCount > 0 ? const Color(0xFFEF4444) : const Color(0xFF64748B),
                  onTap: onViewBlockers,
                ),
                const SizedBox(height: 8),
                _buildActionItem(
                  icon: Icons.history,
                  title: 'Nhật ký vận hành',
                  count: null,
                  color: const Color(0xFF38BDF8),
                  onTap: onViewActivity,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionItem({
    required IconData icon,
    required String title,
    required int? count,
    required Color color,
    required VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF131D38),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500),
              ),
            ),
            if (count != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  count.toString(),
                  style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ),
            const SizedBox(width: 4),
            const Icon(Icons.chevron_right, color: Color(0xFF64748B), size: 16),
          ],
        ),
      ),
    );
  }
}
