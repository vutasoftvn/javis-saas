import 'package:flutter/material.dart';

/// Strategy Floating Action Bar
/// Horizontal bar with 5 quick-access buttons below hologram
/// Responsive: stacks vertical on mobile, horizontal on desktop
class StrategyFloatingActionBar extends StatelessWidget {
  final VoidCallback onOpenStrategyLenses;
  final VoidCallback onOpenEvidenceBackbone;
  final VoidCallback onOpenDecisionLog;
  final VoidCallback onOpenStageGateAudit;
  final VoidCallback onOpenTwelveWyLoop;
  final int? unreadHypothesis;
  final int? unreadDecisions;
  final int? activeRisks;
  final int? nextActions;
  final bool isCompact;

  const StrategyFloatingActionBar({
    super.key,
    required this.onOpenStrategyLenses,
    required this.onOpenEvidenceBackbone,
    required this.onOpenDecisionLog,
    required this.onOpenStageGateAudit,
    required this.onOpenTwelveWyLoop,
    this.unreadHypothesis,
    this.unreadDecisions,
    this.activeRisks,
    this.nextActions,
    this.isCompact = false,
  });

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
    int? badgeCount,
    bool showLabel = true,
  }) {
    return Tooltip(
      message: label,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                padding: showLabel
                    ? const EdgeInsets.symmetric(horizontal: 12, vertical: 8)
                    : const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: color.withValues(alpha: 0.1),
                  border: Border.all(
                    color: color.withValues(alpha: 0.3),
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(icon, size: 16, color: color),
                    if (showLabel) ...[
                      const SizedBox(width: 6),
                      Text(
                        label,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              if (badgeCount != null && badgeCount > 0)
                Positioned(
                  top: -6,
                  right: -6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: const Color(0xFF0F172A),
                        width: 1,
                      ),
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

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 1100;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.1),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: isWide && !isCompact
          ? // Desktop: Horizontal layout
          SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildActionButton(
                    icon: Icons.lens_blur_outlined,
                    label: 'Lăng Kính',
                    color: const Color(0xFFA855F7),
                    onTap: onOpenStrategyLenses,
                    showLabel: true,
                  ),
                  const SizedBox(width: 10),
                  _buildActionButton(
                    icon: Icons.hub_outlined,
                    label: 'Giả Định',
                    color: const Color(0xFF38BDF8),
                    onTap: onOpenEvidenceBackbone,
                    badgeCount: unreadHypothesis,
                    showLabel: true,
                  ),
                  const SizedBox(width: 10),
                  _buildActionButton(
                    icon: Icons.history_edu_outlined,
                    label: 'Bộ Nhớ',
                    color: const Color(0xFF10B981),
                    onTap: onOpenDecisionLog,
                    badgeCount: unreadDecisions,
                    showLabel: true,
                  ),
                  const SizedBox(width: 10),
                  _buildActionButton(
                    icon: Icons.verified_user_outlined,
                    label: 'Thẩm Định',
                    color: const Color(0xFFF59E0B),
                    onTap: onOpenStageGateAudit,
                    badgeCount: activeRisks,
                    showLabel: true,
                  ),
                  const SizedBox(width: 10),
                  _buildActionButton(
                    icon: Icons.loop_outlined,
                    label: 'WY Loop',
                    color: const Color(0xFFE879F9),
                    onTap: onOpenTwelveWyLoop,
                    badgeCount: nextActions,
                    showLabel: true,
                  ),
                  const SizedBox(width: 8),
                  // Divider
                  Container(
                    width: 1,
                    height: 30,
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                  const SizedBox(width: 8),
                  // Info chip
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(6),
                      color: Colors.white.withValues(alpha: 0.05),
                    ),
                    child: Text(
                      '5 chức năng chiến lược',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.7),
                        fontSize: 10,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ],
              ),
            )
          : // Mobile/Compact: Grid/Vertical layout
          Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _buildActionButton(
                  icon: Icons.lens_blur_outlined,
                  label: 'Lăng Kính',
                  color: const Color(0xFFA855F7),
                  onTap: onOpenStrategyLenses,
                  showLabel: false,
                ),
                _buildActionButton(
                  icon: Icons.hub_outlined,
                  label: 'Giả Định',
                  color: const Color(0xFF38BDF8),
                  onTap: onOpenEvidenceBackbone,
                  badgeCount: unreadHypothesis,
                  showLabel: false,
                ),
                _buildActionButton(
                  icon: Icons.history_edu_outlined,
                  label: 'Bộ Nhớ',
                  color: const Color(0xFF10B981),
                  onTap: onOpenDecisionLog,
                  badgeCount: unreadDecisions,
                  showLabel: false,
                ),
                _buildActionButton(
                  icon: Icons.verified_user_outlined,
                  label: 'Thẩm Định',
                  color: const Color(0xFFF59E0B),
                  onTap: onOpenStageGateAudit,
                  badgeCount: activeRisks,
                  showLabel: false,
                ),
                _buildActionButton(
                  icon: Icons.loop_outlined,
                  label: 'WY Loop',
                  color: const Color(0xFFE879F9),
                  onTap: onOpenTwelveWyLoop,
                  badgeCount: nextActions,
                  showLabel: false,
                ),
              ],
            ),
    );
  }
}
