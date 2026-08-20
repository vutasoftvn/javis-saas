import 'package:flutter/material.dart';

class PnLStatementCardWidget extends StatelessWidget {
  final Map<String, dynamic> payload;

  const PnLStatementCardWidget({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Báo cáo P&L';
    final metrics = (payload['metrics'] as List?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0x2000FF66),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x4000FF66)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_balance_wallet_outlined, color: Color(0xFF00FF66), size: 18),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...metrics.map((m) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(m['label'] ?? '', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                  Text(m['value'] ?? '', style: const TextStyle(color: Color(0xFF00FF66), fontWeight: FontWeight.bold, fontSize: 12)),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
