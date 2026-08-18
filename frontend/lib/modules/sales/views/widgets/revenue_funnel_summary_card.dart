import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

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
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: AppTheme.borderDark,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.filter_alt_rounded,
                  color: AppTheme.primaryLight,
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
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 650;
              if (isCompact) {
                return Column(
                  children: [
                    Row(
                      children: [
                        Expanded(child: _buildMetric('TỔNG LEADS', '$totalLeads', Colors.blueAccent)),
                        const SizedBox(width: 10),
                        Expanded(child: _buildMetric('LEAD ĐẠT CHUẨN', '$qualifiedLeads', AppTheme.success)),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(child: _buildMetric('CƠ HỘI BÁN HÀNG', '$activeDeals', Colors.amberAccent)),
                        const SizedBox(width: 10),
                        Expanded(child: _buildMetric('GIÁ TRỊ TRỌNG SỐ', formatCurrency(weightedValue), AppTheme.primaryLight)),
                      ],
                    ),
                  ],
                );
              }

              return Row(
                children: [
                  Expanded(child: _buildMetric('TỔNG LEADS', '$totalLeads', Colors.blueAccent)),
                  _buildDivider(),
                  Expanded(child: _buildMetric('LEAD ĐẠT CHUẨN', '$qualifiedLeads', AppTheme.success)),
                  _buildDivider(),
                  Expanded(child: _buildMetric('CƠ HỘI BÁN HÀNG', '$activeDeals', Colors.amberAccent)),
                  _buildDivider(),
                  Expanded(child: _buildMetric('TỔNG PIPELINE', formatCurrency(pipelineValue), Colors.white70)),
                  _buildDivider(),
                  Expanded(child: _buildMetric('GIÁ TRỊ TRỌNG SỐ', formatCurrency(weightedValue), AppTheme.primaryLight)),
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
      height: 32,
      width: 1,
      margin: const EdgeInsets.symmetric(horizontal: 10),
      color: Colors.white.withValues(alpha: 0.08),
    );
  }

  Widget _buildMetric(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AppTheme.textMutedDark,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
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
            fontSize: 16,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}
