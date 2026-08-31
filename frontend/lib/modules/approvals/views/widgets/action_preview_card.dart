import 'package:flutter/material.dart';
import '../../../../data/models/approval_model.dart';

class ActionPreviewCard extends StatelessWidget {
  final ApprovalItemModel item;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;

  const ActionPreviewCard({
    super.key,
    required this.item,
    this.onApprove,
    this.onReject,
  });

  Color _getActionClassColor(String actionClass) {
    switch (actionClass.toUpperCase()) {
      case 'M':
        return Colors.red.shade700;
      case 'D':
        return Colors.deepPurple;
      case 'X':
        return Colors.orange.shade800;
      case 'B':
        return Colors.blue.shade700;
      case 'A':
        return Colors.teal;
      case 'R':
      default:
        return Colors.grey.shade700;
    }
  }

  String _getActionClassTitle(String actionClass) {
    switch (actionClass.toUpperCase()) {
      case 'M':
        return 'M (Money / Human-owned)';
      case 'D':
        return 'D (Deploy / Sandbox-gated)';
      case 'X':
        return 'X (External / Connector-bound)';
      case 'B':
        return 'B (Bounded internal write)';
      case 'A':
        return 'A (Artifact output)';
      case 'R':
      default:
        return 'R (Read-only)';
    }
  }

  @override
  Widget build(BuildContext context) {
    final actionColor = _getActionClassColor(item.actionClass);
    final hasInvalidHash = item.skillHash == null || item.skillHash!.isEmpty;
    final isHumanOwned = item.isHumanOwnedOnly;
    final isExpired = item.isExpired;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: actionColor.withValues(alpha: 0.4), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Action Class & Title
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: actionColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: actionColor),
                  ),
                  child: Text(
                    _getActionClassTitle(item.actionClass),
                    style: TextStyle(
                      color: actionColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
                Text(
                  'Risk: ${item.riskLevel.label}',
                  style: TextStyle(
                    color: item.riskLevel.color,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Title & Description
            Text(
              item.title,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
            ),
            if (item.description != null && item.description!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                item.description!,
                style: TextStyle(fontSize: 13, color: Colors.grey.shade800),
              ),
            ],
            const Divider(height: 24),

            // Target Preview
            if (item.targetPreview != null &&
                item.targetPreview!.isNotEmpty) ...[
              const Text(
                'Target Preview (Xem trước đối tượng tác động):',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
              ),
              const SizedBox(height: 6),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: item.targetPreview!.entries.map((entry) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Text(
                        '• ${entry.key}: ${entry.value}',
                        style: const TextStyle(
                          fontSize: 12,
                          fontFamily: 'monospace',
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 12),
            ],

            // Skill and Hash Info
            Row(
              children: [
                const Icon(Icons.code, size: 16, color: Colors.blueGrey),
                const SizedBox(width: 6),
                Text(
                  'Skill: ${item.skillId ?? "N/A"}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Hash: ${item.skillHash ?? "UNKNOWN"}',
                    style: TextStyle(
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: hasInvalidHash ? Colors.red : Colors.grey.shade700,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Idempotency Key & Rollback Plan
            if (item.idempotencyKey != null) ...[
              Row(
                children: [
                  const Icon(Icons.fingerprint, size: 16, color: Colors.teal),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Idempotency: ${item.idempotencyKey}',
                      style: const TextStyle(
                        fontSize: 11,
                        fontFamily: 'monospace',
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],
            if (item.rollbackPlan != null) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.restore, size: 16, color: Colors.indigo),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Rollback Plan: ${item.rollbackPlan}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Colors.indigo,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],

            // Evidence Refs
            if (item.evidenceRefs.isNotEmpty) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: item.evidenceRefs.map((ref) {
                  return Chip(
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    visualDensity: VisualDensity.compact,
                    avatar: const Icon(
                      Icons.verified,
                      size: 14,
                      color: Colors.green,
                    ),
                    label: Text(ref, style: const TextStyle(fontSize: 11)),
                    backgroundColor: Colors.green.shade50,
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
            ],

            // Warning Banners
            if (isHumanOwned)
              Container(
                margin: const EdgeInsets.only(top: 8, bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.red.shade300),
                ),
                child: Row(
                  children: const [
                    Icon(Icons.shield, color: Colors.red, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Hành động tài chính (M): Yêu cầu con người thực hiện thủ công ngoài đời thực, hệ thống không tự động kích hoạt.',
                        style: TextStyle(
                          color: Colors.red,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            if (isExpired)
              Container(
                margin: const EdgeInsets.only(top: 8, bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.orange.shade300),
                ),
                child: Row(
                  children: const [
                    Icon(Icons.timer_off, color: Colors.orange, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Yêu cầu đã hết hạn phê duyệt. Không thể thực thi.',
                        style: TextStyle(
                          color: Colors.orange,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            if (hasInvalidHash)
              Container(
                margin: const EdgeInsets.only(top: 8, bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.red.shade300),
                ),
                child: Row(
                  children: const [
                    Icon(Icons.block, color: Colors.red, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Skill hash không xác định - Chặn thực thi để bảo vệ an toàn hệ thống.',
                        style: TextStyle(
                          color: Colors.red,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            // Action Buttons
            if (item.status == ApprovalStatus.pending) ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (onReject != null)
                    OutlinedButton.icon(
                      onPressed: onReject,
                      icon: const Icon(
                        Icons.close,
                        color: Colors.red,
                        size: 18,
                      ),
                      label: const Text(
                        'Từ chối',
                        style: TextStyle(color: Colors.red),
                      ),
                    ),
                  const SizedBox(width: 12),
                  if (onApprove != null)
                    ElevatedButton.icon(
                      onPressed: (isHumanOwned || isExpired || hasInvalidHash)
                          ? null
                          : onApprove,
                      icon: const Icon(Icons.check, size: 18),
                      label: const Text('Phê duyệt thực thi'),
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
