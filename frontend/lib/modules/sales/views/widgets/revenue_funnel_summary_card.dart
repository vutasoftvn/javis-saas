import 'package:flutter/material.dart';

class RevenueFunnelSummaryCard extends StatelessWidget {
  final int totalLeads;
  final int qualifiedLeads;
  final int activeDeals;
  final double pipelineValue;
  final double weightedValue;

  const RevenueFunnelSummaryCard({
    super.key,
    required this.totalLeads,
    required this.qualifiedLeads,
    required this.activeDeals,
    required this.pipelineValue,
    required this.weightedValue,
  });

  static String formatCurrency(num amount) {
    if (amount >= 1000000000) {
      return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đ';
    } else if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(1)} tr đ';
    } else if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(0)}k đ';
    }
    return '${amount.toInt()} đ';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFF38BDF8).withValues(alpha: 0.2),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0284C7).withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.filter_alt_rounded,
                  color: Color(0xFF38BDF8),
                  size: 18,
                ),
              ),
              const SizedBox(width: 10),
              const Text(
                'TỔNG QUAN PHỄU DOANH THU & PIPELINE',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 650;
              if (isCompact) {
                return Column(
                  children: [
                    Row(
                      children: [
                        Expanded(child: _buildMetric('TỔNG LEADS', '$totalLeads', const Color(0xFF38BDF8))),
                        const SizedBox(width: 10),
                        Expanded(child: _buildMetric('QUALIFIED', '$qualifiedLeads', const Color(0xFF10B981))),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(child: _buildMetric('DEALS ĐANG CHẠY', '$activeDeals', const Color(0xFFF59E0B))),
                        const SizedBox(width: 10),
                        Expanded(child: _buildMetric('DỰ KIẾN', formatCurrency(weightedValue), const Color(0xFF00E5FF))),
                      ],
                    ),
                  ],
                );
              }

              return Row(
                children: [
                  Expanded(child: _buildMetric('TỔNG LEADS', '$totalLeads', const Color(0xFF38BDF8))),
                  _buildDivider(),
                  Expanded(child: _buildMetric('LEAD ĐẠT CHUẨN', '$qualifiedLeads', const Color(0xFF10B981))),
                  _buildDivider(),
                  Expanded(child: _buildMetric('CƠ HỘI BÁN HÀNG', '$activeDeals', const Color(0xFFF59E0B))),
                  _buildDivider(),
                  Expanded(child: _buildMetric('TỔNG PIPELINE', formatCurrency(pipelineValue), const Color(0xFF94A3B8))),
                  _buildDivider(),
                  Expanded(child: _buildMetric('GIÁ TRỊ TRỌNG SỐ', formatCurrency(weightedValue), const Color(0xFF00E5FF))),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildDivider() {
    return Container(
      height: 36,
      width: 1,
      margin: const EdgeInsets.symmetric(horizontal: 10),
      color: const Color(0xFF1E293B),
    );
  }

  Widget _buildMetric(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF64748B),
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: color,
            fontSize: 15,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}
