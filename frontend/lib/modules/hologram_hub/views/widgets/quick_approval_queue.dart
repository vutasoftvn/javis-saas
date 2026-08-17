import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';

class QuickApprovalQueue extends StatelessWidget {
  final List<dynamic> approvals;
  final Function(String approvalId, String decision, String? reason)? onApprove;
  final Function(String approvalId)? onAskAI;
  final VoidCallback? onViewAll;

  const QuickApprovalQueue({
    super.key,
    required this.approvals,
    this.onApprove,
    this.onAskAI,
    this.onViewAll,
  });

  @override
  Widget build(BuildContext context) {
    if (approvals.isEmpty) {
      return const SizedBox.shrink();
    }

    return GlassCard(
      padding: const EdgeInsets.all(14),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header Row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFFF59E0B).withValues(alpha: 0.3),
                    width: 1,
                  ),
                ),
                child: const Icon(
                  Icons.how_to_reg_rounded,
                  color: Color(0xFFFBBF24),
                  size: 16,
                ),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'ĐANG CHỜ BẠN DUYỆT',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.6,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFFEF4444).withValues(alpha: 0.25),
                      const Color(0xFFF59E0B).withValues(alpha: 0.25),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.45),
                    width: 0.8,
                  ),
                ),
                child: Text(
                  '${approvals.length} chờ duyệt',
                  style: const TextStyle(
                    color: Color(0xFFFCA5A5),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // List of Approval Cards
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: approvals.length > 3 ? 3 : approvals.length,
            separatorBuilder: (context, index) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = approvals[index] as Map<String, dynamic>;
              return _buildApprovalCard(context, item);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildApprovalCard(BuildContext context, Map<String, dynamic> item) {
    final approvalId = item['approval_id']?.toString() ?? '';
    final title = item['title']?.toString() ?? 'Yêu cầu phê duyệt';
    final rawType = item['type']?.toString() ?? 'ai_proposal';
    final payloadPreview = item['payload_preview'] as Map<String, dynamic>? ?? {};

    // Determine type label and color
    final typeLabel = _formatTypeLabel(rawType);
    final priority = (payloadPreview['priority'] as String?) ??
        (item['urgency'] == 'urgent' ? 'P0' : (item['urgency'] == 'high' ? 'P1' : 'P2'));
    final isP0 = priority == 'P0';

    // Extract detail fields cleanly
    final actionText = payloadPreview['action']?.toString() ??
        payloadPreview['requested_action']?.toString() ??
        '';
    final reasonText = payloadPreview['reason']?.toString() ?? '';
    final subjectText = payloadPreview['subject']?.toString() ?? '';
    final recipientText = payloadPreview['recipient']?.toString() ?? '';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0B1220),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isP0
              ? const Color(0xFFEF4444).withValues(alpha: 0.4)
              : const Color(0xFF1E293B),
          width: isP0 ? 1.2 : 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: isP0
                ? const Color(0xFFEF4444).withValues(alpha: 0.08)
                : Colors.black.withValues(alpha: 0.25),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Tag & Priority Header Row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: const Color(0xFF38BDF8).withValues(alpha: 0.35),
                    width: 0.8,
                  ),
                ),
                child: Text(
                  typeLabel,
                  style: const TextStyle(
                    color: Color(0xFF38BDF8),
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFFF59E0B))
                      .withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: (isP0 ? const Color(0xFFEF4444) : const Color(0xFFF59E0B))
                        .withValues(alpha: 0.35),
                    width: 0.8,
                  ),
                ),
                child: Text(
                  priority,
                  style: TextStyle(
                    color: isP0 ? const Color(0xFFF87171) : const Color(0xFFFBBF24),
                    fontSize: 9.5,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // 2. Title
          Text(
            title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w600,
              height: 1.35,
            ),
          ),

          // 3. Structured Payload Details
          if (actionText.isNotEmpty || reasonText.isNotEmpty || subjectText.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFF040711),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.8),
                  width: 0.8,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (actionText.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '• ',
                            style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                          Expanded(
                            child: Text(
                              'Hành động: $actionText',
                              style: const TextStyle(
                                color: Color(0xFFCBD5E1),
                                fontSize: 11.5,
                                height: 1.35,
                              ),
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (reasonText.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '• ',
                            style: TextStyle(color: Color(0xFFF59E0B), fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                          Expanded(
                            child: Text(
                              'Lý do: $reasonText',
                              style: const TextStyle(
                                color: Color(0xFF94A3B8),
                                fontSize: 11,
                                height: 1.35,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (subjectText.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Text(
                        'Tiêu đề: $subjectText',
                        style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  if (recipientText.isNotEmpty)
                    Text(
                      'Gửi đến: $recipientText',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 12),

          // 4. Action Buttons (Only 2 buttons: Từ chối & Duyệt ngay, no overflow)
          Row(
            children: [
              // Nút 1: Từ chối
              Expanded(
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () => onApprove?.call(approvalId, 'reject', null),
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      height: 34,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: const Color(0xFFEF4444).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(0xFFEF4444).withValues(alpha: 0.35),
                          width: 1,
                        ),
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.close_rounded,
                            size: 14,
                            color: Color(0xFFF87171),
                          ),
                          SizedBox(width: 4),
                          Text(
                            'Từ chối',
                            style: TextStyle(
                              color: Color(0xFFF87171),
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),

              // Nút 2: Duyệt ngay
              Expanded(
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () => onApprove?.call(approvalId, 'approve', null),
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      height: 34,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF059669), Color(0xFF10B981)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(8),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF10B981).withValues(alpha: 0.35),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.check_rounded,
                            size: 15,
                            color: Colors.white,
                          ),
                          SizedBox(width: 4),
                          Text(
                            'Duyệt ngay',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 11.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatTypeLabel(String rawType) {
    switch (rawType.toLowerCase()) {
      case 'ai_proposal':
      case 'founder_action':
        return 'AI PROPOSAL';
      case 'outreach_email':
      case 'email_approval':
        return 'EMAIL';
      case 'workflow_step':
      case 'workflow_approval':
        return 'WORKFLOW';
      case 'marketing_action':
        return 'MARKETING';
      default:
        return rawType.replaceAll('_', ' ').toUpperCase();
    }
  }
}
