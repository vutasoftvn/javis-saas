import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class AiTeamKpiRow extends StatelessWidget {
  final Map<String, dynamic> workforce;
  final Map<String, dynamic> health;
  final Map<String, dynamic> financials;
  final Map<String, dynamic> governance;

  const AiTeamKpiRow({
    super.key,
    required this.workforce,
    required this.health,
    required this.financials,
    required this.governance,
  });

  @override
  Widget build(BuildContext context) {
    final totalAgents = workforce['total_agents'] ?? 12;
    final healthyAgents = health['HEALTHY'] ?? totalAgents;
    final totalUsd = (financials['total_cost_usd'] ?? 0.0).toStringAsFixed(4);
    final totalVnd = (financials['total_cost_vnd'] ?? 0.0);
    final budgetLimit = financials['total_budget_limit_usd'] ?? 100.0;
    final budgetSpent = financials['total_budget_spent_usd'] ?? 0.0;
    final budgetPct = (financials['budget_consumption_pct'] ??
            (budgetLimit > 0 ? (budgetSpent / budgetLimit * 100) : 0.0))
        .toStringAsFixed(1);
    final pendingCount = governance['pending_approvals_total'] ?? 0;
    final criticalCount = governance['critical_risk_count'] ?? 0;

    final card1 = _buildStatCard(
      valueLeft: '$totalAgents Nhân sự AI',
      valueRight: '🟢 $healthyAgents Sẵn sàng',
      titleLeft: 'Lực lượng AI (Workforce)',
      titleRight: '${health['STALLED'] ?? 0} Bị nghẽn',
      icon: Icons.badge_rounded,
      accentColor: AppTheme.primary,
    );

    final card2 = _buildStatCard(
      valueLeft: '\$$totalUsd',
      valueRight: '≈ ${(totalVnd as num).toStringAsFixed(0)} ₫',
      titleLeft: 'Chi phí Token (Cost Ledger)',
      titleRight: 'Tỷ giá: 25,400 ₫',
      icon: Icons.payments_rounded,
      accentColor: const Color(0xFF38BDF8),
    );

    final card3 = _buildStatCard(
      valueLeft: '$budgetPct%',
      valueRight: '\$$budgetSpent / \$$budgetLimit',
      titleLeft: 'Hạn mức Ngân sách 12-Tuần',
      titleRight: (budgetSpent / (budgetLimit > 0 ? budgetLimit : 1.0) > 0.8)
          ? 'Cảnh báo'
          : 'An toàn',
      icon: Icons.account_balance_wallet_rounded,
      accentColor: (budgetSpent / (budgetLimit > 0 ? budgetLimit : 1.0) > 0.8)
          ? AppTheme.warning
          : AppTheme.success,
    );

    final card4 = _buildStatCard(
      valueLeft: '$pendingCount Cần duyệt',
      valueRight: criticalCount > 0 ? '🔴 $criticalCount Rủi ro cao' : 'Kiểm soát an toàn',
      titleLeft: 'Phiếu Phê duyệt (Approval)',
      titleRight: 'Workforce Inbox',
      icon: Icons.fact_check_rounded,
      accentColor: criticalCount > 0
          ? AppTheme.error
          : (pendingCount > 0 ? AppTheme.warning : AppTheme.success),
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > 1000) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: card1),
              const SizedBox(width: 10),
              Expanded(child: card2),
              const SizedBox(width: 10),
              Expanded(child: card3),
              const SizedBox(width: 10),
              Expanded(child: card4),
            ],
          );
        } else if (constraints.maxWidth > 600) {
          return Column(
            children: [
              Row(
                children: [
                  Expanded(child: card1),
                  const SizedBox(width: 10),
                  Expanded(child: card2),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: card3),
                  const SizedBox(width: 10),
                  Expanded(child: card4),
                ],
              ),
            ],
          );
        } else {
          return Column(
            children: [
              card1,
              const SizedBox(height: 10),
              card2,
              const SizedBox(height: 10),
              card3,
              const SizedBox(height: 10),
              card4,
            ],
          );
        }
      },
    );
  }

  Widget _buildStatCard({
    required String valueLeft,
    required String valueRight,
    required String titleLeft,
    required String titleRight,
    required IconData icon,
    required Color accentColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withValues(alpha: 0.18), width: 1),
        boxShadow: [
          BoxShadow(
            color: accentColor.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: accentColor.withValues(alpha: 0.25), width: 1),
            ),
            child: Center(
              child: Icon(icon, color: accentColor, size: 20),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      valueLeft,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textDark,
                        letterSpacing: -0.3,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      valueRight,
                      style: TextStyle(
                        fontSize: 12,
                        color: accentColor,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      titleLeft,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.textMutedDark,
                        fontWeight: FontWeight.w500,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      titleRight,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.textDimDark,
                        fontWeight: FontWeight.w500,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
