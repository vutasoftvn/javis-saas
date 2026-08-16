import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';

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
    final sales = pulseData?['sales'] as Map<String, dynamic>? ?? {
      'status': 'Tăng trưởng tốt',
      'indicator': '+15% tuần này',
      'color': 'green',
      'trend': 'up',
    };
    final cash = pulseData?['cash'] as Map<String, dynamic>? ?? {
      'status': 'Ổn định',
      'indicator': 'Runway: 8.5 tháng',
      'color': 'cyan',
      'trend': 'neutral',
    };
    final marketing = pulseData?['marketing'] as Map<String, dynamic>? ?? {
      'status': 'Chiến dịch Q3',
      'indicator': '120 leads',
      'color': 'green',
      'trend': 'up',
    };
    final operations = pulseData?['operations'] as Map<String, dynamic>? ?? {
      'status': 'Bình thường',
      'indicator': '0 lỗi hệ thống',
      'color': 'green',
      'trend': 'check',
    };
    final legal = pulseData?['legal'] as Map<String, dynamic>? ?? {
      'status': 'Tuân thủ đầy đủ',
      'indicator': 'Hạn thuế: 20 ngày',
      'color': 'green',
      'trend': 'check',
    };

    final items = [
      {
        'label': 'SALES',
        'icon': Icons.trending_up,
        'indicator': sales['indicator'] ?? '',
        'color': sales['color'] ?? 'green',
      },
      {
        'label': 'CASH',
        'icon': Icons.account_balance_wallet_outlined,
        'indicator': cash['indicator'] ?? '',
        'color': cash['color'] ?? 'cyan',
      },
      {
        'label': 'MARKETING',
        'icon': Icons.campaign_outlined,
        'indicator': marketing['indicator'] ?? '',
        'color': marketing['color'] ?? 'green',
      },
      {
        'label': 'OPERATIONS',
        'icon': Icons.miscellaneous_services_outlined,
        'indicator': operations['indicator'] ?? '',
        'color': operations['color'] ?? 'green',
      },
      {
        'label': 'LEGAL',
        'icon': Icons.gavel_outlined,
        'indicator': legal['indicator'] ?? '',
        'color': legal['color'] ?? 'green',
      },
    ];

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
                  color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.monitor_heart_outlined,
                  size: 14,
                  color: Color(0xFF00F0FF),
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
          const Spacer(),
          Text(
            indicator,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
