import 'package:flutter/material.dart';

class WebSearchCardWidget extends StatelessWidget {
  final Map<String, dynamic> payload;

  const WebSearchCardWidget({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Kết quả tìm kiếm Web';
    final items = (payload['items'] as List?) ?? [];

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0x2000F0FF),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x4000F0FF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.travel_explore, color: Color(0xFF00F0FF), size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...items.map((it) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    it['title'] ?? '',
                    style: const TextStyle(color: Color(0xFF00F0FF), fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    it['snippet'] ?? '',
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
