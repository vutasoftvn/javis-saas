import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';
import '../../widgets/token_savings_badge.dart';

/// Unified Company Pulse Card in the Top-Left Corner
class CompanyPulseBar extends StatelessWidget {
  final Map<String, dynamic>? pulseData;
  final VoidCallback? onRefresh;

  const CompanyPulseBar({
    super.key,
    this.pulseData,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (pulseData == null || pulseData!.isEmpty) {
      return const SizedBox.shrink();
    }

    final sales = pulseData?['sales'] as Map<String, dynamic>?;
    final cash = pulseData?['cash'] as Map<String, dynamic>?;
    final marketing = pulseData?['marketing'] as Map<String, dynamic>?;
    final operations = pulseData?['operations'] as Map<String, dynamic>?;
    final legal = pulseData?['legal'] as Map<String, dynamic>?;

    final items = <Map<String, dynamic>>[];
    if (sales != null && (sales['indicator']?.toString().isNotEmpty ?? false)) {
      items.add({
        'label': 'SALES',
        'icon': Icons.trending_up,
        'indicator': sales['indicator'] ?? '',
        'color': sales['color'] ?? 'green',
      });
    }
    if (cash != null && (cash['indicator']?.toString().isNotEmpty ?? false)) {
      items.add({
        'label': 'CASH',
        'icon': Icons.account_balance_wallet_outlined,
        'indicator': cash['indicator'] ?? '',
        'color': cash['color'] ?? 'cyan',
      });
    }
    if (marketing != null && (marketing['indicator']?.toString().isNotEmpty ?? false)) {
      items.add({
        'label': 'MARKETING',
        'icon': Icons.campaign_outlined,
        'indicator': marketing['indicator'] ?? '',
        'color': marketing['color'] ?? 'green',
      });
    }
    if (operations != null && (operations['indicator']?.toString().isNotEmpty ?? false)) {
      items.add({
        'label': 'OPERATIONS',
        'icon': Icons.miscellaneous_services_outlined,
        'indicator': operations['indicator'] ?? '',
        'color': operations['color'] ?? 'green',
      });
    }
    if (legal != null && (legal['indicator']?.toString().isNotEmpty ?? false)) {
      items.add({
        'label': 'LEGAL',
        'icon': Icons.gavel_outlined,
        'indicator': legal['indicator'] ?? '',
        'color': legal['color'] ?? 'green',
      });
    }

    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return GlassCard(
      padding: const EdgeInsets.all(14),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header: Pulse Title + Live indicator
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: const Color(0xFF14B8A6).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.monitor_heart_outlined,
                  size: 14,
                  color: Color(0xFF14B8A6),
                ),
              ),
              const SizedBox(width: 8),
              const Text(
                'NHỊP ĐẬP DOANH NGHIỆP',
                style: TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(
                    color: const Color(0xFF10B981).withValues(alpha: 0.3),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 5,
                      height: 5,
                      decoration: const BoxDecoration(
                        color: Color(0xFF10B981),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text(
                      'LIVE',
                      style: TextStyle(
                        color: Color(0xFF10B981),
                        fontSize: 9,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Structured Pulse Items — Each Metric on 1 Full Line
          Column(
            children: items.map((item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: _buildPulseRow(
                  label: item['label'] as String,
                  icon: item['icon'] as IconData,
                  indicator: item['indicator'] as String,
                  colorCode: item['color'] as String,
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 8),
          const Divider(color: Colors.white10, height: 1),
          const SizedBox(height: 8),
          const Center(child: TokenSavingsBadge()),
        ],
      ),
    );
  }

  Widget _buildPulseRow({
    required String label,
    required IconData icon,
    required String indicator,
    required String colorCode,
  }) {
    Color statusColor;
    switch (colorCode.toLowerCase()) {
      case 'green':
        statusColor = const Color(0xFF10B981);
        break;
      case 'cyan':
        statusColor = const Color(0xFF00E5FF);
        break;
      case 'amber':
      case 'yellow':
        statusColor = const Color(0xFFF59E0B);
        break;
      case 'red':
        statusColor = const Color(0xFFEF4444);
        break;
      default:
        statusColor = const Color(0xFF38BDF8);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: statusColor.withValues(alpha: 0.20),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(
              icon,
              size: 13,
              color: statusColor,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF94A3B8),
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(width: 5),
          Container(
            width: 5,
            height: 5,
            decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: statusColor.withValues(alpha: 0.8),
                  blurRadius: 4,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          const Spacer(),
          Flexible(
            child: Text(
              indicator,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
