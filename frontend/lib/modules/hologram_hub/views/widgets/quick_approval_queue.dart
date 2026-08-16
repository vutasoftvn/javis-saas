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
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.how_to_reg_rounded,
                  color: Color(0xFFFBBF24),
                  size: 18,
                ),
              ),
              const SizedBox(width: 10),
              const Text(
                'ĐANG CHỜ BẠN DUYỆT',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
              const Spacer(),
              if (approvals.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFFEF4444).withValues(alpha: 0.4),
                    ),
                  ),
                  child: Text(
                    '${approvals.length} chờ duyệt',
                    style: const TextStyle(
                      color: Color(0xFFF87171),
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          if (approvals.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 24),
              alignment: Alignment.center,
              child: const Column(
                children: [
                  Icon(
                    Icons.task_alt_rounded,
                    color: Color(0xFF10B981),
                    size: 28,
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Tuyệt vời! Không có mục nào chờ bạn duyệt.',
                    style: TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: approvals.length > 3 ? 3 : approvals.length,
              separatorBuilder: (context, index) => const SizedBox(height: 12),
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
    final agent = item['agent']?.toString() ?? 'Agent';
    final type = item['type']?.toString() ?? 'action';
    final payloadPreview = item['payload_preview'] as Map<String, dynamic>? ?? {};

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: const Color(0xFF334155),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  type.toUpperCase(),
                  style: const TextStyle(
                    color: Color(0xFF38BDF8),
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(width: 8),
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
            ],
          ),
          const SizedBox(height: 8),
          // Payload preview block
          if (payloadPreview.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFF090D16),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: payloadPreview.entries.take(2).map((e) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text(
                      '• ${e.key}: ${e.value}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 11,
                        fontFamily: 'monospace',
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          const SizedBox(height: 10),
          Row(
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.smart_toy_outlined,
                    size: 12,
                    color: Color(0xFF64748B),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    agent,
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              // Nút Hỏi AI
              InkWell(
                onTap: () => onAskAI?.call(approvalId),
                borderRadius: BorderRadius.circular(100),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.chat_bubble_outline_rounded, size: 12, color: Color(0xFF94A3B8)),
                      SizedBox(width: 4),
                      Text(
                        'Hỏi AI',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 6),
              // Nút Từ chối
              InkWell(
                onTap: () => onApprove?.call(approvalId, 'reject', null),
                borderRadius: BorderRadius.circular(100),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: const Text(
                    'Từ chối',
                    style: TextStyle(color: Color(0xFFF87171), fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              // Nút Duyệt
              InkWell(
                onTap: () => onApprove?.call(approvalId, 'approve', null),
                borderRadius: BorderRadius.circular(100),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF059669), Color(0xFF10B981)],
                    ),
                    borderRadius: BorderRadius.circular(100),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF10B981).withValues(alpha: 0.3),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.check_rounded, size: 13, color: Colors.white),
                      SizedBox(width: 4),
                      Text(
                        'Duyệt ngay',
                        style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
