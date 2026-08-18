import 'package:flutter/material.dart';

class FinanceLiteSummaryCard extends StatelessWidget {
  final Map<String, dynamic>? metrics;
  final VoidCallback? onAddTransaction;

  const FinanceLiteSummaryCard({
    super.key,
    this.metrics,
    this.onAddTransaction,
  });

  String _formatVND(num amount) {
    if (amount >= 1000000000) {
      return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đ';
    } else if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(1)} tr đ';
    } else if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(0)} k đ';
    }
    return '${amount.toInt()} đ';
  }

  @override
  Widget build(BuildContext context) {
    final cash = (metrics?['cash_and_bank_balance'] as num?) ?? 0;
    final revenue = (metrics?['total_revenue_period'] as num?) ?? 0;
    final expense = (metrics?['total_expense_period'] as num?) ?? 0;
    final profit = (metrics?['estimated_net_profit'] as num?) ?? (revenue - expense);
    final runway = (metrics?['runway_months'] as num?) ?? 0;
    final burnRate = (metrics?['monthly_burn_rate'] as num?) ?? 0;
    final health = (metrics?['health_status']?.toString() ?? 'CHƯA PHÁT SINH').toUpperCase();

    Color healthColor = const Color(0xFF10B981);
    if (health == 'WARNING') healthColor = const Color(0xFFF59E0B);
    if (health == 'CRITICAL') healthColor = const Color(0xFFEF4444);
    if (health == 'CHƯA PHÁT SINH') healthColor = const Color(0xFF64748B);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Header row: title + health badge ──────────────────────────────
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.account_balance_wallet_rounded,
                      color: Color(0xFF10B981),
                      size: 16,
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'FOUNDER FINANCE LITE',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: healthColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'SỨC KHỎE: $health',
                  style: TextStyle(
                    color: healthColor,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        ),

        // ── Cards row: đồng bộ chiều cao ────────────────────────────────
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth > 700;
            if (isWide) {
              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: _buildMetricBox(
                        label: 'Tiền mặt & Ngân hàng',
                        value: _formatVND(cash),
                        color: const Color(0xFF10B981),
                        icon: Icons.payments_rounded,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _buildMetricBox(
                        label: 'Doanh thu kỳ này',
                        value: _formatVND(revenue),
                        color: const Color(0xFF38BDF8),
                        icon: Icons.trending_up_rounded,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _buildMetricBox(
                        label: 'Lợi nhuận ước tính',
                        value: _formatVND(profit),
                        color: profit >= 0 ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                        icon: Icons.pie_chart_rounded,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _buildMetricBox(
                        label: 'Runway hoạt động',
                        value: '$runway tháng',
                        color: const Color(0xFFF59E0B),
                        icon: Icons.hourglass_bottom_rounded,
                        subtext: 'Đốt: ${_formatVND(burnRate)}/tháng',
                      ),
                    ),
                  ],
                ),
              );
            }
            // Narrow: 2×2 grid
            return Column(
              children: [
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: _buildMetricBox(
                          label: 'Tiền mặt & Ngân hàng',
                          value: _formatVND(cash),
                          color: const Color(0xFF10B981),
                          icon: Icons.payments_rounded,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildMetricBox(
                          label: 'Doanh thu kỳ này',
                          value: _formatVND(revenue),
                          color: const Color(0xFF38BDF8),
                          icon: Icons.trending_up_rounded,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: _buildMetricBox(
                          label: 'Lợi nhuận ước tính',
                          value: _formatVND(profit),
                          color: profit >= 0 ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                          icon: Icons.pie_chart_rounded,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildMetricBox(
                          label: 'Runway hoạt động',
                          value: '$runway tháng',
                          color: const Color(0xFFF59E0B),
                          icon: Icons.hourglass_bottom_rounded,
                          subtext: 'Đốt: ${_formatVND(burnRate)}/tháng',
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildMetricBox({
    required String label,
    required String value,
    required Color color,
    required IconData icon,
    String? subtext,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Label + icon
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 4),
              Icon(icon, color: color, size: 15),
            ],
          ),
          const SizedBox(height: 6),
          // Value + subtext cùng dòng
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Expanded(
                child: Text(
                  value,
                  style: TextStyle(
                    color: color,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (subtext != null)
                Text(
                  subtext,
                  style: const TextStyle(
                      color: Color(0xFF64748B), fontSize: 10),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
