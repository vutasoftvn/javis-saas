import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// ExceptionEscalationInbox — Phase 6
/// Hiển thị và quản lý Exception Escalations trong AI Workforce.
/// 3 tier: FOUNDER_GATE (🔴 đỏ), LEAD_NOTIFY (🟡 vàng), AUTO_RETRY (🔵 xanh)
class ExceptionEscalationInbox extends StatelessWidget {
  final RxList<Map<String, dynamic>> escalations;
  final Map<String, dynamic>? summary;
  final RxBool isLoading;
  final void Function(int id, String action, String? comment) onResolve;

  const ExceptionEscalationInbox({
    super.key,
    required this.escalations,
    required this.summary,
    required this.isLoading,
    required this.onResolve,
  });

  static void show(
    BuildContext context, {
    required RxList<Map<String, dynamic>> escalations,
    required Map<String, dynamic>? summary,
    required RxBool isLoading,
    required void Function(int id, String action, String? comment) onResolve,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ExceptionEscalationInbox(
        escalations: escalations,
        summary: summary,
        isLoading: isLoading,
        onResolve: onResolve,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: BoxDecoration(
        color: const Color(0xFF0F1117),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
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
                    Obx(() {
                      final hasCritical = escalations.any(
                        (e) => e['tier'] == 'FOUNDER_GATE',
                      );
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: hasCritical
                              ? const Color(0xFFEF4444).withValues(alpha: 0.2)
                              : Colors.white10,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: hasCritical
                                ? const Color(0xFFEF4444).withValues(alpha: 0.5)
                                : Colors.white12,
                          ),
                        ),
                        child: Text(
                          hasCritical ? '🚨 CRITICAL' : '⚠ CẢNH BÁO',
                          style: TextStyle(
                            color: hasCritical ? const Color(0xFFEF4444) : Colors.white60,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                          ),
                        ),
                      );
                    }),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Obx(() => Text(
                        'Exception Escalations (${escalations.length} đang chờ)',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 15,
                        ),
                        overflow: TextOverflow.ellipsis,
                      )),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                // Summary chips
                Obx(() {
                  final s = summary;
                  if (s == null) return const SizedBox.shrink();
                  return Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      _tierChip(
                        '🔴 ${s['founder_gate_count'] ?? 0} Founder Gate',
                        const Color(0xFFEF4444),
                      ),
                      _tierChip(
                        '🟡 ${s['lead_notify_count'] ?? 0} Lead Notify',
                        const Color(0xFFEAB308),
                      ),
                    ],
                  );
                }),
                const SizedBox(height: 12),
                Divider(color: Colors.white.withValues(alpha: 0.08)),
              ],
            ),
          ),

          // ── Escalation List
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
              if (escalations.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.check_circle_outline, color: Color(0xFF22C55E), size: 56),
                      const SizedBox(height: 16),
                      Text(
                        'Không có exception nào đang chờ xử lý.',
                        style: TextStyle(color: Colors.white54, fontSize: 15),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Workforce đang hoạt động bình thường ✓',
                        style: TextStyle(color: Colors.white38, fontSize: 12),
                      ),
                    ],
                  ),
                );
              }

              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                itemCount: escalations.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final esc = escalations[i];
                  return _EscalationCard(
                    escalation: esc,
                    onResolve: (action, comment) {
                      final id = esc['id'] as int?;
                      if (id != null) onResolve(id, action, comment);
                    },
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _tierChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}

/// Card đại diện một exception escalation
class _EscalationCard extends StatelessWidget {
  final Map<String, dynamic> escalation;
  final void Function(String action, String? comment) onResolve;

  const _EscalationCard({required this.escalation, required this.onResolve});

  @override
  Widget build(BuildContext context) {
    final tier = escalation['tier'] as String? ?? 'LEAD_NOTIFY';
    final exceptionType = escalation['exception_type'] as String? ?? '';
    final agentKey = escalation['agent_key'] as String? ?? '';
    final stageCode = escalation['stage_code'] as String?;
    final details = escalation['details'] as Map<String, dynamic>? ?? {};
    final createdAt = escalation['created_at'] as String?;

    // Color mapping per tier
    final Color tierColor;
    final String tierLabel;
    final String tierIcon;

    switch (tier) {
      case 'FOUNDER_GATE':
        tierColor = const Color(0xFFEF4444);
        tierLabel = 'FOUNDER GATE';
        tierIcon = '🔴';
      case 'LEAD_NOTIFY':
        tierColor = const Color(0xFFEAB308);
        tierLabel = 'LEAD NOTIFY';
        tierIcon = '🟡';
      default: // AUTO_RETRY
        tierColor = const Color(0xFF3B82F6);
        tierLabel = 'AUTO RETRY';
        tierIcon = '🔵';
    }

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF111318),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tierColor.withValues(alpha: 0.25), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Row 1: Tier badge + Exception type
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: tierColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: tierColor.withValues(alpha: 0.4)),
                  ),
                  child: Text(
                    '$tierIcon $tierLabel',
                    style: TextStyle(
                      color: tierColor,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                      letterSpacing: 0.4,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                _ExceptionTypeChip(exceptionType),
                if (stageCode != null) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6C63FF).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(5),
                    ),
                    child: Text(
                      stageCode,
                      style: TextStyle(
                        color: const Color(0xFF9C8FFF),
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ],
            ),

            const SizedBox(height: 10),

            // Row 2: Agent info
            Row(
              children: [
                const Icon(Icons.smart_toy_outlined, color: Colors.white38, size: 14),
                const SizedBox(width: 6),
                Text(
                  agentKey,
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (createdAt != null) ...[
                  const Spacer(),
                  Text(
                    _formatRelativeTime(createdAt),
                    style: TextStyle(color: Colors.white30, fontSize: 11),
                  ),
                ],
              ],
            ),

            const SizedBox(height: 8),

            // Row 3: Details preview
            _buildDetailsRow(exceptionType, details),

            const SizedBox(height: 12),

            // Row 4: Action buttons (contextual per exception type)
            _buildActionRow(context, tier, exceptionType),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailsRow(String exceptionType, Map<String, dynamic> details) {
    String text = '';
    switch (exceptionType) {
      case 'BUDGET_OVERFLOW':
        final spent = (details['spent_usd'] as num?)?.toStringAsFixed(2) ?? '?';
        final limit = (details['limit_usd'] as num?)?.toStringAsFixed(2) ?? '?';
        text = 'Đã chi: \$$spent / hạn mức: \$$limit';
      case 'AGENT_STALL':
        final elapsed = details['elapsed_minutes'] ?? '?';
        text = 'Không phản hồi: $elapsed phút';
      case 'CONSECUTIVE_ERROR':
        final count = details['error_count'] ?? '?';
        final msg = details['error_message'] ?? '';
        text = '$count lỗi liên tiếp${msg.isNotEmpty ? ' — $msg' : ''}';
      case 'STAGE_MISMATCH':
        final note = details['note'] ?? details['agent_name'] ?? '';
        text = note.toString();
      default:
        text = details.toString();
    }

    if (text.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: TextStyle(color: Colors.white54, fontSize: 12),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  Widget _buildActionRow(BuildContext context, String tier, String exceptionType) {
    final List<_ActionButton> actions;

    switch (exceptionType) {
      case 'BUDGET_OVERFLOW':
        actions = [
          _ActionButton('🔄 Tăng hạn mức', 'increase_budget', const Color(0xFF22C55E)),
          _ActionButton('⏸ Tạm dừng', 'dismiss', Colors.white38),
        ];
      case 'AGENT_STALL':
        actions = [
          _ActionButton('🔄 Retry', 'retry', const Color(0xFF3B82F6)),
          _ActionButton('↗ Giao lại', 'reassign', const Color(0xFFEAB308)),
          _ActionButton('✗ Huỷ', 'dismiss', Colors.white38),
        ];
      case 'STAGE_MISMATCH':
        actions = [
          _ActionButton('▶ Cho phép lần này', 'force_approve', const Color(0xFFEAB308)),
          _ActionButton('🔒 Khoá vĩnh viễn', 'block_permanently', const Color(0xFFEF4444)),
        ];
      case 'CONSECUTIVE_ERROR':
        actions = [
          _ActionButton('🔄 Retry', 'retry', const Color(0xFF3B82F6)),
          _ActionButton('↗ Giao lại', 'reassign', const Color(0xFFEAB308)),
          _ActionButton('✓ Bỏ qua', 'dismiss', Colors.white38),
        ];
      default:
        actions = [
          _ActionButton('✓ Bỏ qua', 'dismiss', Colors.white38),
        ];
    }

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: actions.map((a) {
        return GestureDetector(
          onTap: () {
            if (a.action == 'force_approve' || a.action == 'increase_budget') {
              // Hiện dialog comment trước
              _showCommentDialog(context, a);
            } else {
              onResolve(a.action, null);
            }
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: a.color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: a.color.withValues(alpha: 0.3)),
            ),
            child: Text(
              a.label,
              style: TextStyle(
                color: a.color,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  void _showCommentDialog(BuildContext context, _ActionButton action) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1D24),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          action.label,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
        ),
        content: TextField(
          controller: controller,
          style: TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: 'Ghi chú quyết định (tùy chọn)...',
            hintStyle: TextStyle(color: Colors.white38),
            filled: true,
            fillColor: Colors.white.withValues(alpha: 0.06),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide.none,
            ),
          ),
          maxLines: 3,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Huỷ', style: TextStyle(color: Colors.white38)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: action.color.withValues(alpha: 0.2),
              foregroundColor: action.color,
              elevation: 0,
            ),
            onPressed: () {
              Navigator.pop(ctx);
              onResolve(action.action, controller.text.isEmpty ? null : controller.text);
            },
            child: Text('Xác nhận', style: TextStyle(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  String _formatRelativeTime(String isoString) {
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'vừa xong';
      if (diff.inMinutes < 60) return '${diff.inMinutes} phút trước';
      if (diff.inHours < 24) return '${diff.inHours} giờ trước';
      return '${diff.inDays} ngày trước';
    } catch (_) {
      return '';
    }
  }
}

class _ActionButton {
  final String label;
  final String action;
  final Color color;
  const _ActionButton(this.label, this.action, this.color);
}

/// Chip hiển thị loại exception với icon và màu sắc
class _ExceptionTypeChip extends StatelessWidget {
  final String exceptionType;
  const _ExceptionTypeChip(this.exceptionType);

  @override
  Widget build(BuildContext context) {
    final String label;
    final String icon;
    final Color color;

    switch (exceptionType) {
      case 'BUDGET_OVERFLOW':
        label = 'Budget Overflow';
        icon = '💰';
        color = const Color(0xFFF97316);
      case 'AGENT_STALL':
        label = 'Agent Stall';
        icon = '⏳';
        color = const Color(0xFF8B5CF6);
      case 'CONSECUTIVE_ERROR':
        label = 'Consecutive Error';
        icon = '❌';
        color = const Color(0xFFEF4444);
      case 'STAGE_MISMATCH':
        label = 'Stage Mismatch';
        icon = '⚡';
        color = const Color(0xFFEAB308);
      default:
        label = exceptionType;
        icon = '⚠';
        color = Colors.white38;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '$icon $label',
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w500),
      ),
    );
  }
}
