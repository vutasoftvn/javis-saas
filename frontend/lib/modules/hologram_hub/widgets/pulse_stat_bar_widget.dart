import '../../../core/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/app_translations.dart';
import '../../../data/models/company_pulse_model.dart';

class PulseStatBarWidget extends StatelessWidget {
  final CompanyPulseModel? pulse;

  const PulseStatBarWidget({super.key, required this.pulse});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
      ),
      child: Column(
        children: [
          _buildPulseStat(
            icon: Icons.check_circle_outline,
            color: const Color(0xFF10B981),
            value: '${pulse?.goalsOnTrack ?? 0}/${pulse?.totalActiveGoals ?? 0}',
            label: L10nKey.hubPulseGoalsOnTrack.tr,
          ),
          const Divider(color: Color(0xFF334155), height: 24),
          _buildPulseStat(
            icon: Icons.rocket_launch_outlined,
            color: const Color(0xFF3B82F6),
            value: '${pulse?.activeMissions ?? 0}',
            label: L10nKey.hubPulseActiveMissions.tr,
          ),
          const Divider(color: Color(0xFF334155), height: 24),
          _buildPulseStat(
            icon: Icons.gavel_outlined,
            color: const Color(0xFFF59E0B),
            value: '${pulse?.needsDecisionCount ?? 0}',
            label: L10nKey.hubPulseNeedsDecision.tr,
          ),
          const Divider(color: Color(0xFF334155), height: 24),
          _buildPulseStat(
            icon: Icons.warning_amber_outlined,
            color: const Color(0xFFEF4444),
            value: '${pulse?.majorRisksCount ?? 0}',
            label: L10nKey.hubPulseMajorRisks.tr,
          ),
        ],
      ),
    );
  }

  Widget _buildPulseStat({
    required IconData icon,
    required Color color,
    required String value,
    required String label,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: color, size: 20),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11.5,
                  color: Colors.white.withValues(alpha: 0.6),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
