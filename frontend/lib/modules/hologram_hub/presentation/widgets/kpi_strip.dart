import 'package:flutter/material.dart';
import 'glass_card.dart';

class KpiStrip extends StatelessWidget {
  final Map<String, dynamic>? kpiData;
  final Function(int targetIndex)? onCardTap;

  const KpiStrip({super.key, this.kpiData, this.onCardTap});

  static const Color _previewColor = Color(0xFF64748B);

  @override
  Widget build(BuildContext context) {
    final kpi = kpiData ?? {};

    final projects = kpi['projects'] as Map<String, dynamic>?;
    final tasks = kpi['tasks'] as Map<String, dynamic>?;
    final okrs = kpi['okrs'] as Map<String, dynamic>?;
    final workflows = kpi['workflows'] as Map<String, dynamic>?;
    final knowledge = kpi['knowledge'] as Map<String, dynamic>?;
    final automations = kpi['automations'] as Map<String, dynamic>?;
    final devJobs = kpi['dev_jobs'] as Map<String, dynamic>?;

    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        // 3 breakpoints:
        //   desktop  : w >= 1100 → 7 Expanded cards in one Row
        //   tablet   : 700 <= w < 1100 → Wrap (2 rows of ~4 cards each)
        //   compact  : w < 700  → horizontal scroll, fixed-width compact cards
        final isDesktop = w >= 1100;
        final isTablet = w >= 700;

        // Build card data list for convenience
        final cardDefs = [
          (
            Icons.layers_outlined,
            'DỰ ÁN',
            '${projects?['count'] ?? 0}',
            _translateKpiStatus(projects?['label'] ?? 'ĐANG TRIỂN KHAI'),
            projects?['badge'] ?? '',
            const Color(0xFF14B8A6),
            false,
            1,
          ),
          (
            Icons.check_box_outlined,
            'CÔNG VIỆC',
            '${tasks?['count'] ?? 0}',
            _translateKpiStatus(tasks?['label'] ?? 'ĐANG CHỜ'),
            tasks?['badge'] ?? '',
            const Color(0xFF38BDF8),
            false,
            1,
          ),
          (
            Icons.track_changes,
            'MỤC TIÊU OKR',
            '${okrs?['count'] ?? 0}',
            _translateKpiStatus(okrs?['label'] ?? 'ĐANG THEO DÕI'),
            okrs?['badge'] ?? '',
            const Color(0xFF38BDF8),
            false,
            3,
          ),
          (
            Icons.account_tree_outlined,
            'QUY TRÌNH',
            '${workflows?['count'] ?? 0}',
            _translateKpiStatus(workflows?['label'] ?? 'ĐANG CHẠY'),
            workflows?['badge'] ?? '',
            const Color(0xFFF59E0B),
            false,
            5,
          ),
          (
            Icons.auto_stories_outlined,
            'TRI THỨC',
            '${knowledge?['count'] ?? 0}',
            _translateKpiStatus(knowledge?['label'] ?? 'TÀI LIỆU'),
            knowledge?['badge'] ?? '',
            const Color(0xFF14B8A6),
            false,
            2,
          ),
          (
            Icons.bolt_outlined,
            'TỰ ĐỘNG HÓA',
            '${automations?['count'] ?? 0}',
            _translateKpiStatus(automations?['label'] ?? 'HOẠT ĐỘNG'),
            automations?['badge'] ?? '',
            const Color(0xFF00FFB2),
            false,
            9,
          ),
          (
            Icons.code,
            'TÁC VỤ DEV',
            '${devJobs?['count'] ?? 0}',
            _translateKpiStatus(devJobs?['label'] ?? 'SẮP RA MẮT'),
            devJobs?['badge'] ?? '',
            const Color(0xFF38BDF8),
            (devJobs?['is_dev_preview'] as bool?) ?? true,
            5,
          ),
        ];

        if (isDesktop) {
          // ── Desktop: single row, all Expanded ──────────────────────────────
          return Row(
            children: [
              for (var i = 0; i < cardDefs.length; i++) ...[
                if (i > 0) const SizedBox(width: 10),
                Expanded(
                  child: _buildKpiCardInner(
                    icon: cardDefs[i].$1,
                    title: cardDefs[i].$2,
                    count: cardDefs[i].$3,
                    statusLabel: cardDefs[i].$4,
                    badgeText: cardDefs[i].$5,
                    accentColor: cardDefs[i].$6,
                    isDevPreview: cardDefs[i].$7,
                    onTap: onCardTap != null
                        ? () => onCardTap!(cardDefs[i].$8)
                        : null,
                  ),
                ),
              ],
            ],
          );
        }

        if (isTablet) {
          // ── Tablet: Wrap, 4 per row ─────────────────────────────────────────
          final cardW = (w - 10 * 3) / 4;
          return Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final d in cardDefs)
                SizedBox(
                  width: cardW,
                  child: _buildKpiCardInner(
                    icon: d.$1,
                    title: d.$2,
                    count: d.$3,
                    statusLabel: d.$4,
                    badgeText: d.$5,
                    accentColor: d.$6,
                    isDevPreview: d.$7,
                    onTap: onCardTap != null ? () => onCardTap!(d.$8) : null,
                  ),
                ),
            ],
          );
        }

        // ── Compact / Mobile: horizontal scroll, fixed 130px cards ───────────
        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              for (var i = 0; i < cardDefs.length; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                SizedBox(
                  width: 130,
                  child: _buildKpiCardInner(
                    icon: cardDefs[i].$1,
                    title: cardDefs[i].$2,
                    count: cardDefs[i].$3,
                    statusLabel: cardDefs[i].$4,
                    badgeText: cardDefs[i].$5,
                    accentColor: cardDefs[i].$6,
                    isDevPreview: cardDefs[i].$7,
                    onTap: onCardTap != null
                        ? () => onCardTap!(cardDefs[i].$8)
                        : null,
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  /// Card inner widget (không wrap Expanded/SizedBox — caller decides sizing).
  Widget _buildKpiCardInner({
    required IconData icon,
    required String title,
    required String count,
    required String statusLabel,
    required String badgeText,
    required Color accentColor,
    bool isDevPreview = false,
    VoidCallback? onTap,
  }) {
    final effectiveAccent = isDevPreview ? _previewColor : accentColor;
    return GlassCard(
      height: 120,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      borderRadius: 14,
      onTap: onTap,
      child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            mainAxisSize: MainAxisSize.max,
            children: [
              const Spacer(),
              Text(
                isDevPreview ? '—' : count,
                style: TextStyle(
                  color: isDevPreview ? _previewColor : Colors.white,
                  fontSize: 26,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 2),
              if (isDevPreview)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: _previewColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: _previewColor.withValues(alpha: 0.4),
                      width: 0.8,
                    ),
                  ),
                  child: Text(
                    badgeText.isEmpty ? 'SẮP RA MẮT' : badgeText,
                    style: const TextStyle(
                      color: _previewColor,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                )
              else
                Text(
                  statusLabel,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              const Spacer(),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 16, color: effectiveAccent),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      title,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
    );
  }

  String _translateKpiStatus(String label) {
    switch (label.toUpperCase()) {
      case 'PENDING':
        return 'ĐANG CHỜ';
      case 'ACTIVE':
        return 'HOẠT ĐỘNG';
      default:
        return label;
    }
  }
}
