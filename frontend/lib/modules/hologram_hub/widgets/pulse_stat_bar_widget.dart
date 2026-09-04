import 'package:flutter/material.dart';
import '../../../data/models/company_pulse_model.dart';

class PulseStatBarWidget extends StatelessWidget {
  final CompanyPulseModel? pulse;

  const PulseStatBarWidget({super.key, required this.pulse});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isNarrow = constraints.maxWidth < 550;
          final stats = [
            _buildPulseStat(
              icon: Icons.check_circle_outline,
              color: const Color(0xFF10B981),
              value: '${pulse?.goalsOnTrack ?? 0}/${pulse?.totalActiveGoals ?? 0}',
              label: 'Mục tiêu đúng hạn',
            ),
            _buildPulseStat(
              icon: Icons.rocket_launch_outlined,
              color: const Color(0xFF3B82F6),
              value: '${pulse?.activeMissions ?? 0}',
              label: 'Missions đang chạy',
            ),
            _buildPulseStat(
              icon: Icons.gavel_outlined,
              color: const Color(0xFFF59E0B),
              value: '${pulse?.needsDecisionCount ?? 0}',
              label: 'Quyết định cần chốt',
            ),
            _buildPulseStat(
              icon: Icons.warning_amber_outlined,
              color: const Color(0xFFEF4444),
              value: '${pulse?.majorRisksCount ?? 0}',
              label: 'Rủi ro cần lưu ý',
            ),
          ];

          if (isNarrow) {
            return Wrap(
              alignment: WrapAlignment.spaceAround,
              spacing: 20,
              runSpacing: 14,
              children: stats,
            );
          }

          return Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: stats.map((s) => Expanded(child: s)).toList(),
          );
        },
      ),
    );
  }

  Widget _buildPulseStat({
    required IconData icon,
    required Color color,
    required String value,
    required String label,
  }) {
    return Column(
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 18),
            const SizedBox(width: 6),
            Text(
              value,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: Colors.white.withValues(alpha: 0.6),
          ),
        ),
      ],
    );
  }
}
