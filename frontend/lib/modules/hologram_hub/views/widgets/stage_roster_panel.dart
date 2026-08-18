import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// StageRosterModal — Phase 6
/// Hiển thị Agent Roster được xếp hạng theo COSA Stage Policy hiện tại.
/// Phân loại: HIGH Priority (★), READY (○), LOCKED (🔒)
class StageRosterModal extends StatelessWidget {
  final RxList<Map<String, dynamic>> roster;
  final Map<String, dynamic>? stageMeta;
  final Map<String, dynamic>? summary;
  final RxBool isLoading;
  final void Function(String agentKey) onActivateAgent;

  const StageRosterModal({
    super.key,
    required this.roster,
    required this.stageMeta,
    required this.summary,
    required this.isLoading,
    required this.onActivateAgent,
  });

  static void show(
    BuildContext context, {
    required RxList<Map<String, dynamic>> roster,
    required Map<String, dynamic>? stageMeta,
    required Map<String, dynamic>? summary,
    required RxBool isLoading,
    required void Function(String agentKey) onActivateAgent,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => StageRosterModal(
        roster: roster,
        stageMeta: stageMeta,
        summary: summary,
        isLoading: isLoading,
        onActivateAgent: onActivateAgent,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final stageCode = stageMeta?['stage_code'] ?? '?';
    final stageNameVi = stageMeta?['stage_name_vi'] ?? 'Giai đoạn hiện tại';

    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: BoxDecoration(
        color: const Color(0xFF0F1117),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.08),
        ),
      ),
      child: Column(
        children: [
          // ── Handle bar
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // ── Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF6C63FF), Color(0xFF9C5FFF)],
                        ),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        stageCode,
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Đội ngũ Agent — $stageNameVi',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 15,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Obx(() {
                  if (isLoading.value) {
                    return const _SummaryChipRow(total: 0, high: 0, medium: 0, locked: 0);
                  }
                  final s = summary;
                  return _SummaryChipRow(
                    total: (s?['total'] as int?) ?? 0,
                    high: (s?['high_priority'] as int?) ?? 0,
                    medium: (s?['medium'] as int?) ?? 0,
                    locked: (s?['locked'] as int?) ?? 0,
                  );
                }),
                const SizedBox(height: 12),
                Divider(color: Colors.white.withValues(alpha: 0.08)),
              ],
            ),
          ),

          // ── Agent List
          Expanded(
            child: Obx(() {
              if (isLoading.value) {
                return const Center(
                  child: CircularProgressIndicator(
                    color: Color(0xFF6C63FF),
                    strokeWidth: 2,
                  ),
                );
              }
              if (roster.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.group_off_outlined, color: Colors.white38, size: 48),
                      const SizedBox(height: 12),
                      Text(
                        'Chưa có agent nào trong roster.',
                        style: TextStyle(color: Colors.white38, fontSize: 14),
                      ),
                    ],
                  ),
                );
              }

              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                itemCount: roster.length,
                separatorBuilder: (_, _) => const SizedBox(height: 6),
                itemBuilder: (context, i) {
                  final agent = roster[i];
                  return _AgentRosterCard(
                    agent: agent,
                    onActivate: () => onActivateAgent(agent['key'] ?? ''),
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }
}

/// Tóm tắt số lượng agents theo nhóm
class _SummaryChipRow extends StatelessWidget {
  final int total, high, medium, locked;
  const _SummaryChipRow({required this.total, required this.high, required this.medium, required this.locked});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 6,
      children: [
        _chip('$total Agent', Colors.white24, Colors.white60),
        _chip('★ $high Ưu tiên', const Color(0xFF22C55E).withValues(alpha: 0.2), const Color(0xFF22C55E)),
        _chip('○ $medium Sẵn sàng', Colors.white10, Colors.white54),
        _chip('🔒 $locked Bị khoá', const Color(0xFFEF4444).withValues(alpha: 0.2), const Color(0xFFEF4444)),
      ],
    );
  }

  Widget _chip(String label, Color bg, Color fg) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(color: fg, fontSize: 12, fontWeight: FontWeight.w500),
      ),
    );
  }
}

/// Card đại diện mỗi agent trong roster
class _AgentRosterCard extends StatelessWidget {
  final Map<String, dynamic> agent;
  final VoidCallback onActivate;

  const _AgentRosterCard({required this.agent, required this.onActivate});

  @override
  Widget build(BuildContext context) {
    final priority = agent['priority'] as String? ?? 'MEDIUM';
    final fitScore = (agent['fit_score'] as int?) ?? 50;
    final isLocked = agent['is_locked'] == true;
    final name = agent['name'] as String? ?? 'Agent';
    final roleTitle = agent['role_title'] as String? ?? '';
    final recommendation = agent['stage_recommendation'] as String? ?? '';
    final department = agent['department'] as String? ?? '';

    final Color priorityColor;
    final String priorityIcon;
    final Color cardBorder;

    switch (priority) {
      case 'HIGH':
        priorityColor = const Color(0xFF22C55E);
        priorityIcon = '★';
        cardBorder = const Color(0xFF22C55E).withValues(alpha: 0.3);
      case 'LOW' when isLocked:
        priorityColor = const Color(0xFFEF4444);
        priorityIcon = '🔒';
        cardBorder = const Color(0xFFEF4444).withValues(alpha: 0.3);
      default:
        priorityColor = Colors.white38;
        priorityIcon = '○';
        cardBorder = Colors.white.withValues(alpha: 0.06);
    }

    return Container(
      decoration: BoxDecoration(
        color: isLocked
            ? const Color(0xFF1A0F0F)
            : (priority == 'HIGH'
                ? const Color(0xFF0E1A14)
                : const Color(0xFF111318)),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cardBorder, width: isLocked ? 1.5 : 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Row 1: Priority badge + name + dept
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: priorityColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    priorityIcon,
                    style: TextStyle(color: priorityColor, fontSize: 14),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: TextStyle(
                          color: isLocked ? Colors.white38 : Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                      if (roleTitle.isNotEmpty || department.isNotEmpty)
                        Text(
                          roleTitle.isNotEmpty ? roleTitle : department,
                          style: TextStyle(
                            color: Colors.white38,
                            fontSize: 11,
                          ),
                        ),
                    ],
                  ),
                ),
                // Priority badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: priorityColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    priority == 'HIGH' ? 'PRIORITY' : (isLocked ? 'LOCKED' : 'READY'),
                    style: TextStyle(
                      color: priorityColor,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // Row 2: Fit Score meter
            Row(
              children: [
                Text(
                  'Fit',
                  style: TextStyle(color: Colors.white38, fontSize: 11),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: fitScore / 100,
                      minHeight: 6,
                      backgroundColor: Colors.white10,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        fitScore >= 80
                            ? const Color(0xFF22C55E)
                            : (fitScore >= 40
                                ? const Color(0xFFEAB308)
                                : const Color(0xFFEF4444)),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  '$fitScore%',
                  style: TextStyle(
                    color: priorityColor,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),

            // Row 3: Stage recommendation text
            if (recommendation.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                recommendation,
                style: TextStyle(
                  color: Colors.white38,
                  fontSize: 11,
                  fontStyle: isLocked ? FontStyle.italic : FontStyle.normal,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],

            const SizedBox(height: 10),

            // Row 4: Action button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: onActivate,
                style: ElevatedButton.styleFrom(
                  backgroundColor: isLocked
                      ? const Color(0xFFEF4444).withValues(alpha: 0.12)
                      : (priority == 'HIGH'
                          ? const Color(0xFF6C63FF).withValues(alpha: 0.2)
                          : Colors.white.withValues(alpha: 0.06)),
                  foregroundColor: isLocked ? const Color(0xFFEF4444) : (priority == 'HIGH' ? const Color(0xFF9C8FFF) : Colors.white60),
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                    side: BorderSide(
                      color: isLocked
                          ? const Color(0xFFEF4444).withValues(alpha: 0.3)
                          : Colors.transparent,
                    ),
                  ),
                ),
                child: Text(
                  isLocked ? '⚠ Kích hoạt (cảnh báo)' : '▶ Kích hoạt',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
