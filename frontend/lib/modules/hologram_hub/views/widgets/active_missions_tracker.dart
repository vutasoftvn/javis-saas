import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';

class ActiveMissionsTracker extends StatelessWidget {
  final List<dynamic> missions;
  final Function(String missionId)? onTapMission;

  const ActiveMissionsTracker({
    super.key,
    required this.missions,
    this.onTapMission,
  });

  @override
  Widget build(BuildContext context) {
    if (missions.isEmpty) {
      return const SizedBox.shrink();
    }

    return GlassCard(
      padding: const EdgeInsets.all(16),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.rocket_launch_rounded,
                  color: Color(0xFF34D399),
                  size: 18,
                ),
              ),
              const SizedBox(width: 10),
              const Text(
                'NHIỆM VỤ ĐA AGENT ĐANG CHẠY',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: const Color(0xFF10B981).withValues(alpha: 0.3),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Color(0xFF10B981),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      '${missions.length} active',
                      style: const TextStyle(
                        color: Color(0xFF34D399),
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: missions.length,
            separatorBuilder: (context, index) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = missions[index] as Map<String, dynamic>;
              return _buildMissionCard(context, item);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildMissionCard(BuildContext context, Map<String, dynamic> item) {
    final missionId = item['mission_id']?.toString() ?? '';
    final title = item['title']?.toString() ?? 'Nhiệm vụ';
    final agent = item['agent']?.toString() ?? 'AI Specialist';
    final progress = (item['progress_percent'] as num?)?.toInt() ?? 50;
    final currentStep = item['current_step']?.toString() ?? 'Đang xử lý';
    final nextStep = item['next_step']?.toString() ?? 'Bước tiếp theo';

    return InkWell(
      onTap: () => onTapMission?.call(missionId),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF131D35),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: const Color(0xFF1E293B),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.smart_toy_outlined,
                        size: 11,
                        color: Color(0xFF00E5FF),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        agent,
                        style: const TextStyle(
                          color: Color(0xFF00E5FF),
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Progress Bar
            Row(
              children: [
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress / 100.0,
                      minHeight: 6,
                      backgroundColor: const Color(0xFF1E293B),
                      valueColor: const AlwaysStoppedAnimation<Color>(
                        Color(0xFF10B981),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  '$progress%',
                  style: const TextStyle(
                    color: Color(0xFF34D399),
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // Steps info
            Row(
              children: [
                const Icon(
                  Icons.play_arrow_rounded,
                  size: 13,
                  color: Color(0xFF38BDF8),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    currentStep,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
            if (nextStep.isNotEmpty) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  const Icon(
                    Icons.skip_next_rounded,
                    size: 13,
                    color: Color(0xFF64748B),
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      'Tiếp: $nextStep',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
            ],
            // Verification and Budget chips
            if (item['verification_status'] != null || item['budget'] != null) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  if (item['verification_status'] != null && item['verification_status'] != 'UNKNOWN') ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: (item['verification_status'] == 'VERIFIED')
                            ? const Color(0xFF10B981).withValues(alpha: 0.15)
                            : const Color(0xFFF59E0B).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.verified_outlined,
                            size: 10,
                            color: (item['verification_status'] == 'VERIFIED')
                                ? const Color(0xFF34D399)
                                : const Color(0xFFFBBF24),
                          ),
                          const SizedBox(width: 3),
                          Text(
                            item['verification_status'].toString(),
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              color: (item['verification_status'] == 'VERIFIED')
                                  ? const Color(0xFF34D399)
                                  : const Color(0xFFFBBF24),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                  ],
                  if (item['budget'] != null && item['budget'] is Map) ...[
                    Text(
                      'Budget: \$${((item['budget'] as Map)['current_cost_usd'] as num?)?.toStringAsFixed(2) ?? '0.00'}',
                      style: const TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 10,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                  const Spacer(),
                  const Text(
                    'Xem chi tiết ›',
                    style: TextStyle(
                      color: Color(0xFF00E5FF),
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
