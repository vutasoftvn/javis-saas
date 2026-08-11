import 'package:flutter/material.dart';

class KpiStrip extends StatelessWidget {
  final Map<String, dynamic>? kpiData;
  final Function(int targetIndex)? onCardTap;

  const KpiStrip({
    super.key,
    this.kpiData,
    this.onCardTap,
  });

  static const Color _previewColor = Color(0xFF64748B);

  Widget _buildKpiCard({
    required IconData icon,
    required String title,
    required String count,
    required String statusLabel,
    required String badgeText,
    required Color accentColor,
    VoidCallback? onTap,
    bool isDevPreview = false,
    bool useExpanded = true,
  }) {
    // A dev-preview tile has no backing feature yet - render it visibly
    // muted/disabled instead of showing a fabricated live number.
    final effectiveAccent = isDevPreview ? _previewColor : accentColor;

    final cardWidget = Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A).withValues(alpha: isDevPreview ? 0.55 : 0.85),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: const Color(0xFF1E293B),
              width: 1.0,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.25),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Icon & Title Header
              Row(
                children: [
                  Icon(icon, size: 16, color: effectiveAccent),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Big Count Number - "—" for not-yet-real dev-preview tiles.
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

              // Status Label
              Text(
                statusLabel,
                style: const TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 6),

              // Badge / Footer Text
              if (isDevPreview)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: _previewColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: _previewColor.withValues(alpha: 0.4), width: 0.8),
                  ),
                  child: Text(
                    badgeText.isEmpty ? 'SẮP RA MẮT' : badgeText,
                    style: const TextStyle(
                      color: _previewColor,
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                )
              else
                Text(
                  badgeText,
                  style: TextStyle(
                    color: effectiveAccent,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
            ],
          ),
        ),
      ),
    );

    if (useExpanded) {
      return Expanded(child: cardWidget);
    } else {
      return SizedBox(width: 145, child: cardWidget);
    }
  }

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
        final useExpanded = constraints.maxWidth >= 900;

        final cards = [
          // 1. PROJECTS -> Tab 1 (Tasks / Projects)
          _buildKpiCard(
            icon: Icons.layers_outlined,
            title: 'PROJECTS',
            count: '${projects?['count'] ?? 0}',
            statusLabel: projects?['label'] ?? 'ĐANG TRIỂN KHAI',
            badgeText: projects?['badge'] ?? '',
            accentColor: const Color(0xFF00F0FF),
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(1) : null,
          ),
          const SizedBox(width: 10),

          // 2. TASKS -> Tab 1 (Tasks)
          _buildKpiCard(
            icon: Icons.check_box_outlined,
            title: 'TASKS',
            count: '${tasks?['count'] ?? 0}',
            statusLabel: tasks?['label'] ?? 'PENDING',
            badgeText: tasks?['badge'] ?? '',
            accentColor: const Color(0xFF38BDF8),
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(1) : null,
          ),
          const SizedBox(width: 10),

          // 3. OKRs -> Tab 3 (Strategy & OKRs)
          _buildKpiCard(
            icon: Icons.track_changes,
            title: 'OKRs',
            count: '${okrs?['count'] ?? 0}',
            statusLabel: okrs?['label'] ?? 'ĐANG THEO DÕI',
            badgeText: okrs?['badge'] ?? '',
            accentColor: const Color(0xFF38BDF8),
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(3) : null,
          ),
          const SizedBox(width: 10),

          // 4. WORKFLOWS -> Tab 5 (Workflows)
          _buildKpiCard(
            icon: Icons.account_tree_outlined,
            title: 'WORKFLOWS',
            count: '${workflows?['count'] ?? 0}',
            statusLabel: workflows?['label'] ?? 'ĐANG CHẠY',
            badgeText: workflows?['badge'] ?? '',
            accentColor: const Color(0xFFF59E0B),
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(5) : null,
          ),
          const SizedBox(width: 10),

          // 5. KNOWLEDGE -> Tab 2 (Vault)
          _buildKpiCard(
            icon: Icons.auto_stories_outlined,
            title: 'KNOWLEDGE',
            count: '${knowledge?['count'] ?? 0}',
            statusLabel: knowledge?['label'] ?? 'TÀI LIỆU',
            badgeText: knowledge?['badge'] ?? '',
            accentColor: const Color(0xFF00F0FF),
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(2) : null,
          ),
          const SizedBox(width: 10),

          // 6. AUTOMATIONS -> Tab 9 (Plugins / Automations)
          _buildKpiCard(
            icon: Icons.bolt_outlined,
            title: 'AUTOMATIONS',
            count: '${automations?['count'] ?? 0}',
            statusLabel: automations?['label'] ?? 'ACTIVE',
            badgeText: automations?['badge'] ?? '',
            accentColor: const Color(0xFF00FFB2),
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(9) : null,
          ),
          const SizedBox(width: 10),

          // 7. DEV JOBS -> Tab 5 (Workflows / Dev)
          _buildKpiCard(
            icon: Icons.code,
            title: 'DEV JOBS',
            count: '${devJobs?['count'] ?? 0}',
            statusLabel: devJobs?['label'] ?? 'SẮP RA MẮT',
            badgeText: devJobs?['badge'] ?? '',
            accentColor: const Color(0xFF38BDF8),
            isDevPreview: (devJobs?['is_dev_preview'] as bool?) ?? true,
            useExpanded: useExpanded,
            onTap: onCardTap != null ? () => onCardTap!(5) : null,
          ),
        ];

        if (useExpanded) {
          return Row(children: cards);
        } else {
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: cards),
          );
        }
      },
    );
  }
}
