import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/skill_registry_controller.dart';

class SkillDetailDialog extends StatelessWidget {
  final Map<String, dynamic> skill;

  const SkillDetailDialog({super.key, required this.skill});

  static void show(BuildContext context, Map<String, dynamic> skill) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (context) => SkillDetailDialog(skill: skill),
    );
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<SkillRegistryController>();
    final name = skill['name']?.toString() ?? 'Kỹ năng';
    final domain = (skill['domain']?.toString() ?? 'general').toUpperCase();
    final status = (skill['status']?.toString() ?? 'candidate').toLowerCase();
    final version = skill['version']?.toString() ?? 'v1.0.0';
    final description = skill['description']?.toString() ?? 'Không có mô tả.';
    final instructions = skill['instructions']?.toString() ?? 'Không có hướng dẫn.';
    final successRate = ((skill['success_rate'] as num?)?.toDouble() ?? 0.0) * 100;
    final usageCount = (skill['usage_count'] as num?)?.toInt() ?? 0;
    final positive = (skill['positive_feedback'] as num?)?.toInt() ?? 0;
    final negative = (skill['negative_feedback'] as num?)?.toInt() ?? 0;
    final createdBy = skill['created_by_agent']?.toString() ?? 'human_admin';
    final approvedBy = skill['approved_by_user_id']?.toString();
    final skillId = skill['id']?.toString() ?? '';
    final tools = (skill['tool_permissions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

    Color statusColor = const Color(0xFF94A3B8);
    if (status == 'candidate') statusColor = const Color(0xFFF59E0B);
    if (status == 'evaluation') statusColor = const Color(0xFF00E5FF);
    if (status == 'active') statusColor = const Color(0xFF10B981);
    if (status == 'deprecated') statusColor = const Color(0xFFEF4444);

    return Dialog(
      backgroundColor: const Color(0xFF090E1B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: statusColor.withValues(alpha: 0.4),
          width: 1.5,
        ),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Container(
        width: 720,
        height: 680,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ──────────────────────────────────────────
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    Icons.psychology_outlined,
                    color: statusColor,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: statusColor.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                            ),
                            child: Text(
                              status.toUpperCase(),
                              style: TextStyle(
                                color: statusColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF1E293B),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              version,
                              style: const TextStyle(
                                color: Color(0xFF38BDF8),
                                fontSize: 10,
                                fontFamily: 'monospace',
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Stages: ${(skill['project_stages'] as List<dynamic>?)?.join(', ') ?? '—'} • Autonomy: ${skill['autonomy_ceiling'] ?? 'L0_OBSERVE'} (${skill['side_effect_class'] ?? 'R'}) • ID: $skillId',
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // ── Performance Metrics Strip ─────────────────────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF131B2E),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
              ),
              child: Row(
                children: [
                  _buildMetric('Tỷ lệ thành công', '${successRate.toInt()}%', const Color(0xFF10B981)),
                  _buildMetric('Số lần gọi', '$usageCount lần', const Color(0xFF00E5FF)),
                  _buildMetric('Đánh giá tốt', '+$positive', const Color(0xFF34D399)),
                  _buildMetric('Phản hồi lỗi', '-$negative', const Color(0xFFF87171)),
                  _buildMetric(
                    'Phê duyệt bởi',
                    approvedBy != null ? 'User #$approvedBy' : 'Chưa duyệt',
                    approvedBy != null ? const Color(0xFFA78BFA) : const Color(0xFFF59E0B),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // ── Description & Allowed Tools ───────────────────────
            Text(
              description,
              style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 10),

            if (tools.isNotEmpty) ...[
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: tools.map((t) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF334155)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.build_outlined, size: 10, color: Color(0xFF38BDF8)),
                        const SizedBox(width: 4),
                        Text(
                          t,
                          style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 11, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
            ],

            // ── SOP / Instructions Viewer ─────────────────────────
            const Text(
              'Quy trình Thao tác Chuẩn (SOP) & Prompt Instructions:',
              style: TextStyle(
                color: Color(0xFF94A3B8),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF060A14),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: SingleChildScrollView(
                  child: SelectableText(
                    instructions,
                    style: const TextStyle(
                      color: Color(0xFFE2E8F0),
                      fontSize: 12,
                      fontFamily: 'monospace',
                      height: 1.5,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // ── Lifecycle Actions (Evaluate, Promote, Deprecate) ───
            Row(
              children: [
                if (status != 'deprecated') ...[
                  // Deprecate button
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFEF4444),
                      side: BorderSide(color: const Color(0xFFEF4444).withValues(alpha: 0.5)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    icon: const Icon(Icons.archive_outlined, size: 16),
                    label: const Text('Ngưng dùng (Deprecate)', style: TextStyle(fontSize: 11)),
                    onPressed: () {
                      controller.deprecateSkill(skillId, reason: 'Manual admin deprecation');
                      Navigator.of(context).pop();
                    },
                  ),
                ],
                const Spacer(),
                // Evaluate Score Button
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF00E5FF),
                    side: BorderSide(color: const Color(0xFF00E5FF).withValues(alpha: 0.5)),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: const Icon(Icons.science_outlined, size: 16),
                  label: const Text('Đánh giá Eval (0.95)', style: TextStyle(fontSize: 11)),
                  onPressed: () {
                    controller.evaluateSkill(skillId, 0.95, details: {'evaluator': 'synthetic_benchmark'});
                    Navigator.of(context).pop();
                  },
                ),
                const SizedBox(width: 10),
                // Promote to Production (Active) button
                if (status != 'active') ...[
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    icon: const Icon(Icons.verified_user_outlined, size: 16),
                    label: const Text(
                      'Phê duyệt lên Production (Active)',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                    ),
                    onPressed: () {
                      controller.promoteSkill(skillId);
                      Navigator.of(context).pop();
                    },
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetric(String label, String value, Color color) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10)),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}
