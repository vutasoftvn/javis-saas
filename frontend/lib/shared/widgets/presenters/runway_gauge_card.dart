import 'package:flutter/material.dart';

class RunwayGaugeCardWidget extends StatelessWidget {
  final Map<String, dynamic> payload;

  const RunwayGaugeCardWidget({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Chỉ số Cash Runway';
    final months = payload['runway_months'] ?? 0;
    final status = payload['status'] ?? 'NORMAL';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0x20FFB800),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x40FFB800)),
      ),
      child: Row(
        children: [
          const Icon(Icons.speed, color: Color(0xFFFFB800), size: 24),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
              Text("Số tháng sống còn: $months tháng ($status)", style: const TextStyle(color: Color(0xFFFFB800), fontSize: 12)),
            ],
          ),
        ],
      ),
    );
  }
}
