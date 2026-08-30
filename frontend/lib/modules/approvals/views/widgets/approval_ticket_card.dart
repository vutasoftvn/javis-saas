import 'dart:convert';
import 'package:flutter/material.dart';
import '../../../../data/models/approval_model.dart';
import '../../controllers/approvals_controller.dart';
import 'approval_action_dialogs.dart';

class ApprovalTicketCard extends StatelessWidget {
  final ApprovalItemModel item;
  final ApprovalsController controller;

  const ApprovalTicketCard({
    super.key,
    required this.item,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    final riskColor = item.riskLevel.color;
    final isCritical = item.riskLevel == ApprovalRiskLevel.critical;
    final requester = item.requesterName ?? item.agentName ?? 'AI Agent';
    final actionType = item.actionType ?? 'SYSTEM_ACTION';
    final reason = item.description ?? 'Hành động rủi ro cần Founder phê duyệt';

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: riskColor.withValues(alpha: 0.5), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: riskColor.withValues(alpha: 0.1),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Card Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: riskColor.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    Icon(
                      isCritical ? Icons.gavel_rounded : Icons.warning_amber_rounded,
                      size: 14,
                      color: riskColor,
                    ),
                    const SizedBox(width: 5),
                    Text(
                      '${item.riskLevel.label} RISK',
                      style: TextStyle(
                        color: riskColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Lệnh gọi: $actionType',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                'Người yêu cầu: $requester',
                style: TextStyle(
                  color: Colors.blueAccent.shade100,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Reason Context
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Lý do phê duyệt:',
                  style: TextStyle(
                    color: Colors.grey,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  reason,
                  style: const TextStyle(
                    color: Color(0xFFE2E8F0),
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          // Payload Preview Accordion
          if (item.payload.isNotEmpty)
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text(
                'Xem chi tiết Payload dữ liệu',
                style: TextStyle(
                  color: Colors.blueAccent,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF020617),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: SelectableText(
                    const JsonEncoder.withIndent('  ').convert(item.payload),
                    style: const TextStyle(
                      color: Color(0xFF94A3B8),
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),

          const Divider(color: Color(0xFF334155), height: 20),

          // 3-Action Buttons (Approve, Reject, Request Revision)
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              // Request Revision Button
              OutlinedButton.icon(
                onPressed: () => ApprovalActionDialogs.showRevision(context, controller, item.id),
                icon: const Icon(Icons.edit_note_rounded, size: 16, color: Color(0xFF818CF8)),
                label: const Text('Yêu cầu sửa lại', style: TextStyle(color: Color(0xFF818CF8), fontSize: 12.5)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFF4F46E5)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 10),

              // Reject Button
              OutlinedButton.icon(
                onPressed: () => ApprovalActionDialogs.showReject(context, controller, item.id),
                icon: const Icon(Icons.close_rounded, size: 16, color: Color(0xFFF87171)),
                label: const Text('Từ chối', style: TextStyle(color: Color(0xFFF87171), fontSize: 12.5)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFFDC2626)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 10),

              // Approve Button
              ElevatedButton.icon(
                onPressed: (item.isHumanOwnedOnly || item.isExpired || (item.skillHash != null && item.skillHash!.isEmpty))
                    ? null
                    : () => ApprovalActionDialogs.showApprove(context, controller, item.id),
                icon: const Icon(Icons.check_rounded, size: 16, color: Colors.white),
                label: const Text(
                  'Chấp thuận (Approve)',
                  style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  disabledBackgroundColor: Colors.grey.shade800,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
