import 'package:flutter/material.dart';
import '../../../../data/models/approval_model.dart';

class ApprovalHistoryItem extends StatelessWidget {
  final ApprovalItemModel item;

  const ApprovalHistoryItem({super.key, required this.item});

  @override
  Widget build(BuildContext context) {
    final isApproved = item.status == ApprovalStatus.approved;
    final statusColor = isApproved ? const Color(0xFF10B981) : const Color(0xFFEF4444);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        children: [
          Icon(
            isApproved ? Icons.check_circle_outline : Icons.cancel_outlined,
            color: statusColor,
            size: 22,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Lệnh: ${item.actionType ?? item.title}',
                  style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w700),
                ),
                Text(
                  'Ghi chú: ${item.comment ?? item.rejectionReason ?? 'N/A'}',
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
                ),
              ],
            ),
          ),
          Text(
            item.status.label,
            style: TextStyle(color: statusColor, fontSize: 12, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}
