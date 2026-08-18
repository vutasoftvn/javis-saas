import 'package:flutter/material.dart';

/// Strategy Navigation Panel - Collapsible Sidebar
/// Groups 5 strategic action buttons under "Strategy" section
class StrategyNavigationPanel extends StatelessWidget {
  final bool isExpanded;
  final VoidCallback onToggleExpand;
  final VoidCallback onOpenStrategyLenses;
  final VoidCallback onOpenEvidenceBackbone;
  final VoidCallback onOpenDecisionLog;
  final VoidCallback onOpenStageGateAudit;
  final VoidCallback onOpenTwelveWyLoop;
  final int? unreadHypothesis;
  final int? unreadDecisions;
  final int? activeRisks;
  final int? nextActions;

  const StrategyNavigationPanel({
    super.key,
    required this.isExpanded,
    required this.onToggleExpand,
    required this.onOpenStrategyLenses,
    required this.onOpenEvidenceBackbone,
    required this.onOpenDecisionLog,
    required this.onOpenStageGateAudit,
    required this.onOpenTwelveWyLoop,
    this.unreadHypothesis,
    this.unreadDecisions,
    this.activeRisks,
    this.nextActions,
  });

  Widget _buildNavItem({
    required IconData icon,
    required String label,
    required String color,
    required Color colorValue,
    required VoidCallback onTap,
    int? badgeCount,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            color: colorValue.withValues(alpha: 0.08),
            border: Border.all(
              color: colorValue.withValues(alpha: 0.2),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(icon, size: 16, color: colorValue),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (badgeCount != null && badgeCount > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: colorValue,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    badgeCount.toString(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      width: isExpanded ? 260 : 60,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.1),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header: Toggle button
          Tooltip(
            message: isExpanded ? 'Collapse Strategy Menu' : 'Expand Strategy Menu',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: onToggleExpand,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.psychology_outlined,
                        size: 20,
                        color: const Color(0xFFA855F7),
                      ),
                      if (isExpanded) ...[
                        const SizedBox(width: 8),
                        Text(
                          'Strategy',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const Spacer(),
                        Icon(
                          Icons.chevron_left,
                          size: 18,
                          color: Colors.white70,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),

          const SizedBox(height: 12),

          // Divider
          Divider(
            color: Colors.white.withValues(alpha: 0.1),
            height: 1,
          ),

          const SizedBox(height: 12),

          // 5 Strategy Action Buttons
          if (isExpanded)
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildNavItem(
                      icon: Icons.lens_blur_outlined,
                      label: 'Lăng Kính',
                      color: 'purple',
                      colorValue: const Color(0xFFA855F7),
                      onTap: onOpenStrategyLenses,
                    ),
                    const SizedBox(height: 8),
                    _buildNavItem(
                      icon: Icons.hub_outlined,
                      label: 'Giả Định',
                      color: 'cyan',
                      colorValue: const Color(0xFF38BDF8),
                      onTap: onOpenEvidenceBackbone,
                      badgeCount: unreadHypothesis,
                    ),
                    const SizedBox(height: 8),
                    _buildNavItem(
                      icon: Icons.history_edu_outlined,
                      label: 'Bộ Nhớ',
                      color: 'green',
                      colorValue: const Color(0xFF10B981),
                      onTap: onOpenDecisionLog,
                      badgeCount: unreadDecisions,
                    ),
                    const SizedBox(height: 8),
                    _buildNavItem(
                      icon: Icons.verified_user_outlined,
                      label: 'Thẩm Định',
                      color: 'amber',
                      colorValue: const Color(0xFFF59E0B),
                      onTap: onOpenStageGateAudit,
                      badgeCount: activeRisks,
                    ),
                    const SizedBox(height: 8),
                    _buildNavItem(
                      icon: Icons.loop_outlined,
                      label: 'WY Loop',
                      color: 'pink',
                      colorValue: const Color(0xFFE879F9),
                      onTap: onOpenTwelveWyLoop,
                      badgeCount: nextActions,
                    ),
                  ],
                ),
              ),
            )
          else
            // Compact icon-only mode
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    _buildCompactIcon(
                      icon: Icons.lens_blur_outlined,
                      colorValue: const Color(0xFFA855F7),
                      tooltip: 'Lăng Kính (Lenses)',
                      onTap: onOpenStrategyLenses,
                    ),
                    const SizedBox(height: 8),
                    _buildCompactIcon(
                      icon: Icons.hub_outlined,
                      colorValue: const Color(0xFF38BDF8),
                      tooltip: 'Giả Định (Hypothesis)',
                      onTap: onOpenEvidenceBackbone,
                      badgeCount: unreadHypothesis,
                    ),
                    const SizedBox(height: 8),
                    _buildCompactIcon(
                      icon: Icons.history_edu_outlined,
                      colorValue: const Color(0xFF10B981),
                      tooltip: 'Bộ Nhớ (Memory)',
                      onTap: onOpenDecisionLog,
                      badgeCount: unreadDecisions,
                    ),
                    const SizedBox(height: 8),
                    _buildCompactIcon(
                      icon: Icons.verified_user_outlined,
                      colorValue: const Color(0xFFF59E0B),
                      tooltip: 'Thẩm Định (Audit)',
                      onTap: onOpenStageGateAudit,
                      badgeCount: activeRisks,
                    ),
                    const SizedBox(height: 8),
                    _buildCompactIcon(
                      icon: Icons.loop_outlined,
                      colorValue: const Color(0xFFE879F9),
                      tooltip: 'WY Loop',
                      onTap: onOpenTwelveWyLoop,
                      badgeCount: nextActions,
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildCompactIcon({
    required IconData icon,
    required Color colorValue,
    required String tooltip,
    required VoidCallback onTap,
    int? badgeCount,
  }) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: colorValue.withValues(alpha: 0.1),
                  border: Border.all(
                    color: colorValue.withValues(alpha: 0.3),
                  ),
                ),
                child: Icon(icon, size: 20, color: colorValue),
              ),
              if (badgeCount != null && badgeCount > 0)
                Positioned(
                  top: -4,
                  right: -4,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: colorValue,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF0F172A), width: 1),
                    ),
                    child: Text(
                      badgeCount.toString(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
