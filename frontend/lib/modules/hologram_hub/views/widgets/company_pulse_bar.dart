import 'package:flutter/material.dart';

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

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFF00E5FF).withValues(alpha: 0.2),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF00E5FF).withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 650;

          if (isCompact) {
            return SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildPulseItem(
                    label: 'SALES',
                    icon: Icons.trending_up,
                    status: sales['status'] ?? '',
                    indicator: sales['indicator'] ?? '',
                    colorCode: sales['color'] ?? 'green',
                  ),
                  _buildDivider(),
                  _buildPulseItem(
                    label: 'CASH',
                    icon: Icons.account_balance_wallet_outlined,
                    status: cash['status'] ?? '',
                    indicator: cash['indicator'] ?? '',
                    colorCode: cash['color'] ?? 'cyan',
                  ),
                  _buildDivider(),
                  _buildPulseItem(
                    label: 'MKT',
                    icon: Icons.campaign_outlined,
                    status: marketing['status'] ?? '',
                    indicator: marketing['indicator'] ?? '',
                    colorCode: marketing['color'] ?? 'green',
                  ),
                  _buildDivider(),
                  _buildPulseItem(
                    label: 'OPS',
                    icon: Icons.miscellaneous_services_outlined,
                    status: operations['status'] ?? '',
                    indicator: operations['indicator'] ?? '',
                    colorCode: operations['color'] ?? 'green',
                  ),
                  _buildDivider(),
                  _buildPulseItem(
                    label: 'LEGAL',
                    icon: Icons.gavel_outlined,
                    status: legal['status'] ?? '',
                    indicator: legal['indicator'] ?? '',
                    colorCode: legal['color'] ?? 'green',
                  ),
                ],
              ),
            );
          }

          return Row(
            children: [
              Expanded(
                child: _buildPulseItem(
                  label: 'SALES',
                  icon: Icons.trending_up,
                  status: sales['status'] ?? '',
                  indicator: sales['indicator'] ?? '',
                  colorCode: sales['color'] ?? 'green',
                ),
              ),
              _buildDivider(),
              Expanded(
                child: _buildPulseItem(
                  label: 'CASH',
                  icon: Icons.account_balance_wallet_outlined,
                  status: cash['status'] ?? '',
                  indicator: cash['indicator'] ?? '',
                  colorCode: cash['color'] ?? 'cyan',
                ),
              ),
              _buildDivider(),
              Expanded(
                child: _buildPulseItem(
                  label: 'MARKETING',
                  icon: Icons.campaign_outlined,
                  status: marketing['status'] ?? '',
                  indicator: marketing['indicator'] ?? '',
                  colorCode: marketing['color'] ?? 'green',
                ),
              ),
              _buildDivider(),
              Expanded(
                child: _buildPulseItem(
                  label: 'OPERATIONS',
                  icon: Icons.miscellaneous_services_outlined,
                  status: operations['status'] ?? '',
                  indicator: operations['indicator'] ?? '',
                  colorCode: operations['color'] ?? 'green',
                ),
              ),
              _buildDivider(),
              Expanded(
                child: _buildPulseItem(
                  label: 'LEGAL',
                  icon: Icons.gavel_outlined,
                  status: legal['status'] ?? '',
                  indicator: legal['indicator'] ?? '',
                  colorCode: legal['color'] ?? 'green',
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildDivider() {
    return Container(
      height: 32,
      width: 1,
      margin: const EdgeInsets.symmetric(horizontal: 10),
      color: const Color(0xFF1E293B),
    );
  }

  Widget _buildPulseItem({
    required String label,
    required IconData icon,
    required String status,
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

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.12),
            shape: BoxShape.circle,
            border: Border.all(color: statusColor.withValues(alpha: 0.3)),
          ),
          child: Icon(
            icon,
            size: 14,
            color: statusColor,
          ),
        ),
        const SizedBox(width: 8),
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(width: 4),
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
                ],
              ),
              const SizedBox(height: 2),
              Text(
                indicator,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
