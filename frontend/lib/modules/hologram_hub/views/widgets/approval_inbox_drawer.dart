import 'package:flutter/material.dart';
import '../../presentation/widgets/glass_card.dart';

class ApprovalInboxDrawer extends StatelessWidget {
  final List<Map<String, dynamic>> approvals;
  final Function(int approvalId, String? comment) onApprove;
  final Function(int approvalId, String? comment) onReject;
  final VoidCallback onClose;

  const ApprovalInboxDrawer({
    super.key,
    required this.approvals,
    required this.onApprove,
    required this.onReject,
    required this.onClose,
  });

  static void show(BuildContext context, {
    required List<Map<String, dynamic>> approvals,
    required Function(int approvalId, String? comment) onApprove,
    required Function(int approvalId, String? comment) onReject,
  }) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (ctx) => Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480, maxHeight: double.infinity),
          child: ApprovalInboxDrawer(
            approvals: approvals,
            onApprove: (id, comment) {
              onApprove(id, comment);
              Navigator.of(ctx).pop();
            },
            onReject: (id, comment) {
              onReject(id, comment);
              Navigator.of(ctx).pop();
            },
            onClose: () => Navigator.of(ctx).pop(),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pendingList = approvals.where((a) => a['status'] == 'PENDING').toList();

    return Material(
      color: Colors.transparent,
      child: GlassCard(
        borderRadius: 0,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Drawer Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: const Color(0xFFEF4444).withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Icon(
                    Icons.security_outlined,
                    color: Color(0xFFEF4444),
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Hộp Thư Phê Duyệt (Human Approval Inbox)',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        '${pendingList.length} yêu cầu đang chờ Founder quyết định',
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: onClose,
                  icon: const Icon(Icons.close, color: Color(0xFF94A3B8)),
                  tooltip: 'Đóng',
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(color: Color(0xFF1E293B), height: 1),
            const SizedBox(height: 16),

            // Main List
            Expanded(
              child: pendingList.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.check_circle_outline,
                            size: 54,
                            color: const Color(0xFF10B981).withValues(alpha: 0.6),
                          ),
                          const SizedBox(height: 14),
                          const Text(
                            'Tất cả đã được giải quyết!',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Không có hành động rủi ro nào đang chờ phê duyệt.',
                            style: TextStyle(
                              color: Color(0xFF64748B),
                              fontSize: 12,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    )
                  : ListView.separated(
                      itemCount: pendingList.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 14),
                      itemBuilder: (context, idx) {
                        return _buildApprovalCard(context, pendingList[idx]);
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildApprovalCard(BuildContext context, Map<String, dynamic> item) {
    final id = (item['id'] as num?)?.toInt() ?? 0;
    final title = (item['action_type'] as String?) ?? 'Yêu cầu hành động';
    final description = (item['action_payload']?['description'] as String?) ??
        (item['action_payload']?['reason'] as String?) ??
        'Agent cần thực hiện thao tác vượt quyền hạn tự động.';
    final riskLevel = (item['risk_tier'] as String?) ?? 'HIGH';
    final agentKey = (item['agent_key'] as String?) ?? (item['requester_id']?.toString() ?? 'Agent');

    final isCritical = riskLevel.toUpperCase() == 'CRITICAL';
    final riskColor = isCritical ? const Color(0xFFEF4444) : const Color(0xFFF59E0B);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: riskColor.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Risk Badge & Agent
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: riskColor.withValues(alpha: 0.4)),
                ),
                child: Text(
                  'RỦI RO $riskLevel',
                  style: TextStyle(
                    color: riskColor,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              Text(
                'Từ: $agentKey',
                style: const TextStyle(
                  color: Color(0xFF38BDF8),
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Title
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),

          // Description
          Text(
            description,
            style: const TextStyle(
              color: Color(0xFF94A3B8),
              fontSize: 12,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),

          // Action Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton(
                onPressed: () => onReject(id, 'Từ chối bởi Founder'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFEF4444),
                  side: const BorderSide(color: Color(0xFFEF4444)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('Từ chối', style: TextStyle(fontSize: 12)),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () => onApprove(id, 'Phê duyệt bởi Founder'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('Phê duyệt', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
