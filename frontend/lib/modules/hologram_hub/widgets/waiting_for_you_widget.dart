import 'package:flutter/material.dart';
import '../../../data/models/founder_decision_model.dart';
import 'decision_modal_sheet.dart';

class WaitingForYouWidget extends StatelessWidget {
  final List<FounderDecisionModel> decisions;
  final List<Map<String, dynamic>> approvals;
  final Function(int decisionId, String optionKey, String? notes) onResolveDecision;
  final Function(dynamic approvalId) onApproveTask;
  final Function(dynamic approvalId, String reason) onRejectTask;

  const WaitingForYouWidget({
    super.key,
    required this.decisions,
    required this.approvals,
    required this.onResolveDecision,
    required this.onApproveTask,
    required this.onRejectTask,
  });

  @override
  Widget build(BuildContext context) {
    if (decisions.isEmpty && approvals.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B).withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF334155)),
        ),
        child: Row(
          children: [
            const Icon(Icons.check_circle, color: Color(0xFF10B981), size: 22),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Hàng đợi trống: Không có quyết định hay phê duyệt nào đang chờ bạn.',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 13),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.inbox_outlined, color: Color(0xFF6366F1), size: 20),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'WAITING FOR YOU (Hàng đợi cần Founder xử lý)',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 0.5,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '${decisions.length + approvals.length} mục',
                style: const TextStyle(fontSize: 11, color: Color(0xFFF87171), fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // 1. Decisions Section
        if (decisions.isNotEmpty) ...[
          ...decisions.map((d) => _buildDecisionItem(context, d)),
        ],

        // 2. Approvals Section
        if (approvals.isNotEmpty) ...[
          ...approvals.map((a) => _buildApprovalItem(context, a)),
        ],
      ],
    );
  }

  Widget _buildDecisionItem(BuildContext context, FounderDecisionModel d) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.5), width: 1.2),
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'STRATEGIC DECISION',
                  style: TextStyle(fontSize: 10, color: Color(0xFFFBBF24), fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  d.domain,
                  style: TextStyle(fontSize: 11, color: Colors.white.withValues(alpha: 0.5)),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () {
                  showModalBottomSheet(
                    context: context,
                    isScrollControlled: true,
                    backgroundColor: Colors.transparent,
                    builder: (_) => DecisionModalSheet(
                      decision: d,
                      onResolve: (optKey, notes) => onResolveDecision(d.id, optKey, notes),
                    ),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFF59E0B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  minimumSize: Size.zero,
                ),
                child: const Text('Ra quyết định', style: TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            d.question,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
          ),
          if (d.contextSummary != null) ...[
            const SizedBox(height: 4),
            Text(
              d.contextSummary!,
              style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.65)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildApprovalItem(BuildContext context, Map<String, dynamic> a) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF3B82F6).withValues(alpha: 0.3), width: 1.0),
      ),
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.shield_outlined, color: Color(0xFF60A5FA), size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF3B82F6).withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text(
                        'APPROVAL',
                        style: TextStyle(fontSize: 9, color: Color(0xFF60A5FA), fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        a['agent_name'] ?? 'Domain Agent',
                        style: TextStyle(fontSize: 10, color: Colors.white.withValues(alpha: 0.5)),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  a['title'] ?? 'Yêu cầu phê duyệt tác vụ',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          OutlinedButton(
            onPressed: () => _promptRejectReason(context, a['id']),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFFF87171),
              side: const BorderSide(color: Color(0xFFF87171)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              minimumSize: Size.zero,
            ),
            child: const Text('Từ chối', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(width: 6),
          ElevatedButton(
            onPressed: () => onApproveTask(a['id']),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF3B82F6),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              minimumSize: Size.zero,
            ),
            child: const Text('Phê duyệt', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _promptRejectReason(BuildContext context, dynamic approvalId) {
    final reasonController = TextEditingController();
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Từ chối tác vụ', style: TextStyle(color: Colors.white)),
        content: TextField(
          controller: reasonController,
          autofocus: true,
          maxLines: 3,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: 'Lý do từ chối (bắt buộc)',
            hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4)),
            enabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: Color(0xFF334155))),
            focusedBorder: const OutlineInputBorder(borderSide: BorderSide(color: Color(0xFFF87171))),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text('Hủy', style: TextStyle(color: Colors.white.withValues(alpha: 0.6))),
          ),
          ElevatedButton(
            onPressed: () {
              final reason = reasonController.text.trim();
              if (reason.isEmpty) return;
              Navigator.of(dialogContext).pop();
              onRejectTask(approvalId, reason);
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFEF4444)),
            child: const Text('Từ chối', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }
}
