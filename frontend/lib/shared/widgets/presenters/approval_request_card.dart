import 'package:flutter/material.dart';

class ApprovalRequestCardWidget extends StatelessWidget {
  final Map<String, dynamic> payload;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;

  const ApprovalRequestCardWidget({
    super.key,
    required this.payload,
    this.onApprove,
    this.onReject,
  });

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Yêu cầu Phê Duyệt Quyền';
    final toolId = payload['tool_id'] ?? 'Hành động nguy hiểm';
    final riskLevel = payload['risk_level'] ?? 'HIGH';
    final inputParams = payload['input_params'] ?? {};

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0x20FF3366),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFF3366)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.shield_outlined, color: Color(0xFFFF3366), size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF3366),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  riskLevel,
                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text("Công cụ: $toolId", style: const TextStyle(color: Colors.white70, fontSize: 12)),
          if (inputParams.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text("Tham số: $inputParams", style: const TextStyle(color: Colors.white54, fontSize: 11)),
          ],
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton(
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Colors.white54),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                ),
                onPressed: onReject,
                child: const Text("Từ chối", style: TextStyle(color: Colors.white70, fontSize: 12)),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFF3366),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                ),
                onPressed: onApprove,
                child: const Text("Phê duyệt", style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
