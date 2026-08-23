import 'package:flutter/material.dart';
import '../../../data/models/company_pulse_model.dart';

class CoFounderCardWidget extends StatelessWidget {
  final CompanyPulseModel? pulse;
  final VoidCallback onAskCosa;

  const CoFounderCardWidget({
    super.key,
    required this.pulse,
    required this.onAskCosa,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1E1B4B), Color(0xFF312E81), Color(0xFF0F172A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF6366F1).withValues(alpha: 0.3), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6366F1).withValues(alpha: 0.15),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 620;
              if (isCompact) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFF8B5CF6), Color(0xFF6366F1)],
                            ),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF8B5CF6).withValues(alpha: 0.4),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: const Icon(Icons.psychology, color: Colors.white, size: 24),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Wrap(
                                crossAxisAlignment: WrapCrossAlignment.center,
                                spacing: 8,
                                runSpacing: 4,
                                children: [
                                  const Text(
                                    'COSA Co-Founder',
                                    style: TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.white,
                                      letterSpacing: 0.3,
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF10B981).withValues(alpha: 0.2),
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(color: const Color(0xFF10B981), width: 0.8),
                                    ),
                                    child: const Text(
                                      'ONLINE • AI PARTNER',
                                      style: TextStyle(fontSize: 10, color: Color(0xFF34D399), fontWeight: FontWeight.w600),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                pulse?.suggestedFocus ?? 'Đang theo dõi nhịp tim doanh nghiệp và điều phối 5 Core Domains...',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.white.withValues(alpha: 0.85),
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: ElevatedButton.icon(
                        onPressed: onAskCosa,
                        icon: const Icon(Icons.chat_bubble_outline, size: 16, color: Colors.white),
                        label: const Text('Trao đổi', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF6366F1),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          elevation: 4,
                        ),
                      ),
                    ),
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF8B5CF6), Color(0xFF6366F1)],
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF8B5CF6).withValues(alpha: 0.4),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.psychology, color: Colors.white, size: 30),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Text(
                              'COSA Co-Founder',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                                letterSpacing: 0.3,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: const Color(0xFF10B981).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFF10B981), width: 0.8),
                              ),
                              child: const Text(
                                'ONLINE • AI PARTNER',
                                style: TextStyle(fontSize: 10, color: Color(0xFF34D399), fontWeight: FontWeight.w600),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          pulse?.suggestedFocus ?? 'Đang theo dõi nhịp tim doanh nghiệp và điều phối 5 Core Domains...',
                          style: TextStyle(
                            fontSize: 13.5,
                            color: Colors.white.withValues(alpha: 0.85),
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: onAskCosa,
                    icon: const Icon(Icons.chat_bubble_outline, size: 16, color: Colors.white),
                    label: const Text('Trao đổi', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF6366F1),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      elevation: 4,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          const Divider(color: Color(0x336366F1), height: 1),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final isNarrow = constraints.maxWidth < 550;
              if (isNarrow) {
                return Wrap(
                  alignment: WrapAlignment.spaceAround,
                  spacing: 20,
                  runSpacing: 14,
                  children: [
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
                  ],
                );
              }

              return Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Expanded(
                    child: _buildPulseStat(
                      icon: Icons.check_circle_outline,
                      color: const Color(0xFF10B981),
                      value: '${pulse?.goalsOnTrack ?? 0}/${pulse?.totalActiveGoals ?? 0}',
                      label: 'Mục tiêu đúng hạn',
                    ),
                  ),
                  Expanded(
                    child: _buildPulseStat(
                      icon: Icons.rocket_launch_outlined,
                      color: const Color(0xFF3B82F6),
                      value: '${pulse?.activeMissions ?? 0}',
                      label: 'Missions đang chạy',
                    ),
                  ),
                  Expanded(
                    child: _buildPulseStat(
                      icon: Icons.gavel_outlined,
                      color: const Color(0xFFF59E0B),
                      value: '${pulse?.needsDecisionCount ?? 0}',
                      label: 'Quyết định cần chốt',
                    ),
                  ),
                  Expanded(
                    child: _buildPulseStat(
                      icon: Icons.warning_amber_outlined,
                      color: const Color(0xFFEF4444),
                      value: '${pulse?.majorRisksCount ?? 0}',
                      label: 'Rủi ro cần lưu ý',
                    ),
                  ),
                ],
              );
            },
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
