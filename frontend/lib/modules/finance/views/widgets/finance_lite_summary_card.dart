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

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.25), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF10B981).withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.account_balance_wallet_rounded, color: Color(0xFF10B981), size: 20),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'FOUNDER FINANCE LITE',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: healthColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'SỨC KHỎE: $health',
                      style: TextStyle(color: healthColor, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 18),
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth > 700;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _buildMetricBox(
                    label: 'Tiền mặt & Ngân hàng',
                    value: _formatVND(cash),
                    color: const Color(0xFF10B981),
                    icon: Icons.payments_rounded,
                    width: isWide ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                  ),
                  _buildMetricBox(
                    label: 'Doanh thu kỳ này',
                    value: _formatVND(revenue),
                    color: const Color(0xFF38BDF8),
                    icon: Icons.trending_up_rounded,
                    width: isWide ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                  ),
                  _buildMetricBox(
                    label: 'Lợi nhuận ước tính',
                    value: _formatVND(profit),
                    color: profit >= 0 ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                    icon: Icons.pie_chart_rounded,
                    width: isWide ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                  ),
                  _buildMetricBox(
                    label: 'Runway hoạt động',
                    value: '$runway tháng',
                    color: const Color(0xFFF59E0B),
                    icon: Icons.hourglass_bottom_rounded,
                    subtext: 'Đốt: ${_formatVND(burnRate)}/tháng',
                    width: isWide ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2,
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildMetricBox({
    required String label,
    required String value,
    required Color color,
    required IconData icon,
    String? subtext,
    required double width,
  }) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
              Icon(icon, color: color, size: 16),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          if (subtext != null) ...[
            const SizedBox(height: 4),
            Text(subtext, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10)),
          ],
        ],
      ),
    );
  }
}
