import 'package:flutter/material.dart';

class CrmLeadCardWidget extends StatelessWidget {
  final Map<String, dynamic> payload;

  const CrmLeadCardWidget({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Thông tin Khách hàng Tiềm năng';
    final metrics = (payload['metrics'] as List?) ?? [];
    final items = (payload['items'] as List?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0x208A2BE2),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x408A2BE2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.person_search_outlined, color: Color(0xFF8A2BE2), size: 18),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ],
          ),
          if (metrics.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              children: metrics.map((m) {
                return Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0x30FFFFFF),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    "${m['label']}: ${m['value']}",
                    style: const TextStyle(color: Colors.white, fontSize: 12),
                  ),
                );
              }).toList(),
            ),
          ],
          if (items.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...items.map((it) {
              return Text(
                "• ${it['name']} - ${it['company']} (Score: ${it['score']})",
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              );
            }),
          ]
        ],
      ),
    );
  }
}
